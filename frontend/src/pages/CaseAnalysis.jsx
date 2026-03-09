import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../utils/api';
import { useCaseEvents, useCaseEventListener } from '../context/CaseEventContext';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import AgenticDecisionTab from '../components/tabs/AgenticDecisionTab';
import QuestionScoringTab from '../components/tabs/QuestionScoringTab';
import CiomsDetailsSection from '../components/CiomsDetailsSection';

/* ═══════════════════════════════════════════════════════════════
   HELPERS
   ═══════════════════════════════════════════════════════════════ */
const pct = (v) => Math.round((v || 0) * 100);

const decisionMeta = {
  PROCEED:  { cls: 'bg-blue-50 text-blue-700 ring-1 ring-blue-600/20',   label: 'Proceed' },
  ESCALATE: { cls: 'bg-red-50 text-red-700 ring-1 ring-red-600/20',      label: 'Escalate' },
  DEFER:    { cls: 'bg-amber-50 text-amber-700 ring-1 ring-amber-600/20', label: 'Defer' },
  ASK:      { cls: 'bg-purple-50 text-purple-700 ring-1 ring-purple-600/20', label: 'Ask' },
  SKIP:     { cls: 'bg-gray-100 text-gray-600',                          label: 'Skip' },
};

const riskColor = (s) => {
  if (s >= 0.7) return 'text-red-600';
  if (s >= 0.4) return 'text-amber-600';
  return 'text-emerald-600';
};

const riskBg = (s) => {
  if (s >= 0.7) return 'bg-red-50 text-red-700 ring-1 ring-red-600/20';
  if (s >= 0.4) return 'bg-amber-50 text-amber-700 ring-1 ring-amber-600/20';
  return 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20';
};

/* ── lifecycle step derivation ─────────────────────────────── */
const LIFECYCLE_STEPS = ['Intake', 'Validation', 'Analysis', 'Follow-Up', 'Closure'];

const deriveStep = (a) => {
  if (!a) return 0;
  if (a.stop_followup || a.decision === 'SKIP') return 4; // closure
  if (a.decision === 'ASK' || a.decision === 'DEFER') return 3; // follow-up
  if (a.decision) return 2; // analysis done
  if (a.completeness_score != null) return 1; // validated
  return 0;
};

/* ── tiny ring gauge ───────────────────────────────────────── */
const RingGauge = ({ value, size = 64, stroke = 6, color = '#3b82f6', label }) => {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - (value || 0));
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#f3f4f6" strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke}
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round" />
      </svg>
      <span className="text-xs text-gray-500">{label}</span>
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════
   PAGE COMPONENT
   ═══════════════════════════════════════════════════════════════ */
const CaseAnalysis = () => {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const { emitCaseUpdate } = useCaseEvents();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [analyzing, setAnalyzing] = useState(false);

  const [analyzeSending, setAnalyzeSending] = useState(false);
  const [partialSources, setPartialSources] = useState(null); // question sources when no full analysis

  /* ── lifecycle state (fetched in parallel) ──────── */
  const [lifecycle, setLifecycle] = useState(null);

  const fetchData = async (emitEvent = false) => {
    try {
      setLoading(true);
      setError(null);

      let analysis = null;

      // Try loading cached/stored analysis first
      try {
        const stored = await api.getCaseAnalysis(caseId);
        if (stored.has_analysis) {
          analysis = stored;
          setPartialSources(null);
        } else {
          setPartialSources(stored);
        }
      } catch (_) { /* no stored analysis yet */ }

      // If no analysis exists, auto-trigger analysis using primaryid route
      if (!analysis) {
        try {
          await api.analyzeCase(caseId);
          // Re-fetch after analysis completes
          try {
            const stored2 = await api.getCaseAnalysis(caseId);
            if (stored2.has_analysis) {
              analysis = stored2;
              setPartialSources(null);
            }
          } catch (_) {}
        } catch (err) {
          console.error('Auto-analysis failed:', err);
        }
      }

      setAnalysisData(analysis);

      if (analysis && emitEvent) {
        emitCaseUpdate({ type: 'CASE_ANALYZED', caseId, metadata: { analysis } });
      }

      /* fetch lifecycle in background (non-blocking) */
      try { const lc = await api.getLifecycleStatus(caseId); setLifecycle(lc); } catch (_) {}

      setLoading(false);
    } catch (err) {
      setError(err.message || 'Failed to load case analysis');
      setLoading(false);
    }
  };

  /* ── Analyze button: merge 4 sources + send follow-up ──── */
  const handleAnalyzeAndSend = async () => {
    setAnalyzeSending(true);
    try {
      const res = await api.analyzeAndSend(analysisData?.case_id || caseId);
      if (res.status === 'sent') {
        alert(`✅ Follow-up sent!\n\nMerged ${res.merged_questions} questions\nReviewer: ${res.sources?.reviewer || 0}\nTFU: ${res.sources?.tfu || 0}\nRepo: ${res.sources?.repo || 0}\nAI: ${res.sources?.ai || 0}`);
      } else {
        alert('No questions to send.');
      }
      // Refresh data
      fetchData(true);
    } catch (err) {
      console.error('Analyze-and-send failed:', err);
      alert('Analyze failed: ' + err.message);
    } finally {
      setAnalyzeSending(false);
    }
  };

  useEffect(() => {
    if (caseId) fetchData(true);
  }, [caseId]);

  useCaseEventListener((event) => {
    if (event.caseId === caseId && event.type !== 'CASE_ANALYZED') {
      console.log('📋 CaseAnalysis: Refreshing due to:', event.type);
      fetchData(false);
    }
  });

  /* ── derived data (MUST come before any early returns so hook order is stable) */
  const { analysis: _analysis } = analysisData || {};
  const a = _analysis || {};
  const cd = a.case_data || {};
  const dm = decisionMeta[a.decision] || decisionMeta.SKIP;
  const currentStep = deriveStep(a);

  const fieldCounts = useMemo(() => {
    const mf = a.missing_fields || [];
    return {
      critical: mf.filter(f => f.criticality === 'CRITICAL').length,
      high:     mf.filter(f => f.criticality === 'HIGH').length,
      medium:   mf.filter(f => f.criticality === 'MEDIUM').length,
      low:      mf.filter(f => f.criticality === 'LOW').length,
      total:    mf.length,
    };
  }, [a.missing_fields]);

  /* ── guards ─────────────────────────────────────────────── */
  if (loading) return <LoadingState message="Loading case data..." />;
  if (error)   return <ErrorState message={error} onRetry={fetchData} />;
  if (!analysisData) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-xl border shadow-sm p-8 max-w-lg w-full space-y-6 text-center">
        <svg className="w-12 h-12 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg>
        <h2 className="text-lg font-semibold text-gray-800 mb-2">No Analysis Yet</h2>
        <p className="text-sm text-gray-500 mb-3">Analysis is pending. Click <strong>Analyze & Send</strong> to run analysis and send follow-up.</p>

        <button onClick={handleAnalyzeAndSend} disabled={analyzeSending}
          className={`px-5 py-2.5 rounded-lg text-sm font-medium ${analyzeSending ? 'bg-emerald-300 text-white cursor-not-allowed' : 'bg-emerald-600 text-white hover:bg-emerald-700'}`}>
          {analyzeSending ? 'Analyzing…' : 'Analyze & Send'}
        </button>
        <button onClick={() => navigate('/case-analysis')} className="block mx-auto mt-3 text-xs text-gray-400 hover:text-gray-600">← Back to Cases</button>
      </div>
    </div>
  );

  const tabs = [
    { id: 'overview',  label: 'Overview' },
    { id: 'decision',  label: 'Decision' },
    { id: 'followup',  label: 'Follow-Up Strategy' },
    { id: 'questions', label: 'Question Scoring' },
  ];

  /* ═══════════════════════════════════════════════════════════
     RENDER
     ═══════════════════════════════════════════════════════════ */
  return (
    <div className="min-h-screen bg-gray-50">

      {/* ═══ CASE HEADER ═══ */}
      <div className="bg-white border-b">
        <div className="max-w-[1400px] mx-auto px-6 py-5">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            {/* Left — case identity */}
            <div className="flex items-start gap-3 min-w-0">
              <button onClick={() => navigate('/case-analysis')} className="mt-1 text-gray-400 hover:text-gray-700 flex-shrink-0">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
              </button>
              <div className="min-w-0">
                <div className="flex items-center gap-3 flex-wrap">
                  <h1 className="text-xl font-bold text-gray-900 tracking-tight">Case #{analysisData.primaryid || caseId}</h1>
                  <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold ${dm.cls}`}>{a.decision || 'PENDING'}</span>
                  {(a.risk_level === 'HIGH' || a.risk_level === 'CRITICAL') && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-50 text-red-700 ring-1 ring-red-600/20">
                      Multi-Channel Eligible
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-4 mt-1.5 text-sm text-gray-500 flex-wrap">
                  <span><span className="text-gray-400">Drug:</span> <span className="text-gray-700 font-medium">{cd.suspect_drug || 'N/A'}</span></span>
                  <span className="text-gray-300">|</span>
                  <span><span className="text-gray-400">Event:</span> <span className="text-gray-700 font-medium">{cd.adverse_event || 'N/A'}</span></span>
                  <span className="text-gray-300">|</span>
                  <span><span className="text-gray-400">Reporter:</span> <span className="text-gray-700 font-medium">{cd.reporter_type || 'N/A'}</span></span>
                  <span className="text-gray-300">|</span>
                  <span><span className="text-gray-400">Seriousness:</span> <span className={`font-semibold ${riskColor(a.risk_score || 0)}`}>{pct(a.risk_score)}%</span></span>
                </div>
              </div>
            </div>

            {/* Right — actions */}
            <div className="flex items-center gap-2 flex-shrink-0 flex-wrap">
              <button onClick={() => navigate(`/explainability/${analysisData.case_id || caseId}`)}
                className="px-3.5 py-2 bg-white border text-gray-700 rounded-lg hover:bg-gray-50 text-xs font-medium flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                Explain
              </button>
              <button onClick={handleAnalyzeAndSend} disabled={analyzeSending}
                className={`px-3.5 py-2 rounded-lg text-xs font-medium flex items-center gap-1.5 ${analyzeSending ? 'bg-emerald-300 text-white cursor-not-allowed' : 'bg-emerald-600 text-white hover:bg-emerald-700'}`}>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                {analyzeSending ? 'Sending…' : 'Analyze'}
              </button>
              {['ASK', 'PROCEED', 'DEFER', 'ESCALATE'].includes(a.decision) && (
                <button onClick={() => navigate(`/follow-up/${analysisData.primaryid || caseId}`)}
                  className="px-3.5 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-xs font-medium flex items-center gap-1.5">
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg>
                  Start Follow-Up
                </button>
              )}
              {a.escalation_needed && (
                <button onClick={() => navigate(`/follow-up/${analysisData.primaryid || caseId}`)}
                  className="px-3.5 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-xs font-medium flex items-center gap-1.5">
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>
                  Escalate
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ═══ LIFECYCLE PROGRESS BAR ═══ */}
      <div className="bg-white border-b">
        <div className="max-w-[1400px] mx-auto px-6 py-4">
          <div className="flex items-center gap-1">
            {LIFECYCLE_STEPS.map((step, i) => {
              const done = i <= currentStep;
              const active = i === currentStep;
              return (
                <React.Fragment key={step}>
                  {i > 0 && <div className={`flex-1 h-0.5 ${i <= currentStep ? 'bg-blue-500' : 'bg-gray-200'}`} />}
                  <div className="flex flex-col items-center gap-1 min-w-0">
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                      active ? 'bg-blue-600 text-white ring-4 ring-blue-100'
                      : done ? 'bg-blue-500 text-white'
                      : 'bg-gray-200 text-gray-500'
                    }`}>
                      {done && !active ? (
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={3} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/></svg>
                      ) : (i + 1)}
                    </div>
                    <span className={`text-[10px] font-medium whitespace-nowrap ${active ? 'text-blue-700' : done ? 'text-gray-700' : 'text-gray-400'}`}>{step}</span>
                  </div>
                </React.Fragment>
              );
            })}
          </div>
        </div>
      </div>

      {/* ═══ TAB NAVIGATION ═══ */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-[1400px] mx-auto px-6">
          <nav className="flex gap-0 overflow-x-auto">
            {tabs.map(t => (
              <button key={t.id} onClick={() => setActiveTab(t.id)}
                className={`px-4 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                  activeTab === t.id ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}>
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* ═══ MAIN CONTENT — two-column (workspace + insights panel) ═══ */}
      <div className="max-w-[1400px] mx-auto px-6 py-6">
        <div className="flex gap-6">

          {/* LEFT — tab workspace */}
          <div className="flex-1 min-w-0 space-y-6">

            {/* ── OVERVIEW TAB ─────────────────────────────── */}
            {activeTab === 'overview' && (
              <>
                {/* KPI strip */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <KpiMini label="Risk Score" value={`${pct(a.risk_score)}%`} sub={a.risk_level || '—'} color={riskColor(a.risk_score || 0)} />
                  <KpiMini label="Confidence" value={`${pct(a.confidence)}%`} sub={a.priority || '—'} color="text-blue-600" />
                  <KpiMini label="Completeness" value={`${pct(a.completeness_score)}%`} sub={`${a.missing_fields_count ?? fieldCounts.total} missing`} color="text-gray-900" />
                  <KpiMini label="Response Prob." value={`${pct(a.response_probability)}%`} sub={a.engagement_risk || '—'} color="text-purple-600" />
                </div>

                {/* Case Summary + Completeness Breakdown */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Case Summary */}
                  <div className="bg-white rounded-xl border shadow-sm p-5">
                    <h3 className="text-sm font-semibold text-gray-900 mb-4">Case Summary</h3>
                    <div className="space-y-3">
                      <InfoRow label="Case ID" value={analysisData.primaryid || caseId} />
                      <InfoRow label="Suspect Drug" value={cd.suspect_drug} />
                      <InfoRow label="Adverse Event" value={cd.adverse_event} />
                      <InfoRow label="Reporter Type" value={cd.reporter_type} />
                      <InfoRow label="Decision" value={a.decision || 'PENDING'} badge={dm.cls} />
                      <InfoRow label="Risk Level" value={a.risk_level || 'N/A'} badge={riskBg(a.risk_score || 0)} />
                      <InfoRow label="Priority" value={a.priority || 'N/A'} />
                      <InfoRow label="Urgency" value={a.urgency || 'Standard'} />
                      <InfoRow label="Days to Deadline" value={a.days_to_deadline ?? 'N/A'} />
                      {a.is_resumed && <InfoRow label="Status" value="Resumed Follow-Up" badge="bg-amber-50 text-amber-700 ring-1 ring-amber-600/20" />}
                    </div>
                  </div>

                  {/* Completeness Breakdown */}
                  <div className="bg-white rounded-xl border shadow-sm p-5">
                    <h3 className="text-sm font-semibold text-gray-900 mb-4">Completeness Breakdown</h3>
                    {/* progress bar */}
                    <div className="mb-5">
                      <div className="flex justify-between text-xs mb-1.5">
                        <span className="text-gray-500">Data Completeness</span>
                        <span className="font-semibold text-gray-900">{pct(a.completeness_score)}%</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2.5">
                        <div className={`h-full rounded-full ${pct(a.completeness_score) >= 80 ? 'bg-emerald-500' : pct(a.completeness_score) >= 60 ? 'bg-blue-500' : 'bg-red-400'}`}
                          style={{ width: `${pct(a.completeness_score)}%` }} />
                      </div>
                    </div>
                    {/* field severity grid */}
                    <div className="grid grid-cols-2 gap-3 mb-5">
                      <SeverityCount label="Critical Missing" count={fieldCounts.critical} cls="bg-red-50 text-red-700" />
                      <SeverityCount label="High Missing" count={fieldCounts.high} cls="bg-amber-50 text-amber-700" />
                      <SeverityCount label="Medium Missing" count={fieldCounts.medium} cls="bg-blue-50 text-blue-700" />
                      <SeverityCount label="Low Missing" count={fieldCounts.low} cls="bg-gray-50 text-gray-600" />
                    </div>
                    {/* answered vs total */}
                    <div className="flex items-center justify-between text-xs text-gray-500 border-t pt-3">
                      <span>Answered Fields: <span className="font-semibold text-gray-900">{a.answered_fields?.length ?? 0}</span></span>
                      <span>Total Missing: <span className="font-semibold text-gray-900">{fieldCounts.total}</span></span>
                    </div>
                    {a.stop_followup && (
                      <div className="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800">
                        <span className="font-semibold">Follow-up stopped:</span> {a.stop_reason || 'Threshold reached'}
                      </div>
                    )}
                  </div>
                </div>

                {/* ═══ FOLLOW-UP SENT BANNER ═══ */}
                {analysisData.followup_sent && (
                  <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center flex-shrink-0">
                      <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-emerald-800">Follow-Up Sent</p>
                      <p className="text-xs text-emerald-700 mt-0.5">{analysisData.followup_sent_count || 0} frozen questions sent to reporter.</p>
                    </div>
                  </div>
                )}

                {/* ═══ ATTACHED REPO DOCUMENTS ═══ */}
                {(analysisData.attached_repo_docs || []).length > 0 && (
                  <div className="bg-white rounded-xl border shadow-sm p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" /></svg>
                      <h3 className="text-sm font-semibold text-gray-900">Attached Repository Documents</h3>
                      <span className="ml-auto text-[10px] text-gray-400">{(analysisData.attached_repo_docs).length} document(s)</span>
                    </div>
                    <div className="space-y-1.5">
                      {(analysisData.attached_repo_docs).map((doc, i) => (
                        <div key={doc.id || i} className="flex items-center gap-3 bg-indigo-50/60 rounded-lg p-2.5">
                          <svg className="w-4 h-4 text-indigo-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium text-gray-800 truncate">{doc.display_name || doc.file_name}</p>
                            <div className="flex items-center gap-2 mt-0.5">
                              <span className="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-indigo-100 text-indigo-700">{doc.form_type}</span>
                              <span className="text-[10px] text-gray-400">{doc.questions_count ?? 0} questions</span>
                            </div>
                          </div>
                          <span className="text-[9px] text-emerald-600 font-semibold bg-emerald-50 px-1.5 py-0.5 rounded">PDF ATTACHED</span>
                        </div>
                      ))}
                    </div>
                    <p className="text-[10px] text-gray-400 mt-2">These PDFs will be attached to the follow-up email when sent.</p>
                  </div>
                )}

                {/* ═══ QUESTION SOURCE PANELS ═══ */}

                {/* 1. TFU Mandatory Questions */}
                {(analysisData.tfu_questions || []).length > 0 && (
                  <div className="bg-white rounded-xl border shadow-sm p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="inline-flex px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-700">TFU MANDATORY</span>
                      <h3 className="text-sm font-semibold text-gray-900">TFU Mandatory Questions</h3>
                      <span className="ml-auto text-xs font-semibold text-amber-600">{(analysisData.tfu_questions || []).length}</span>
                    </div>
                    <div className="space-y-1.5">
                      {(analysisData.tfu_questions || []).map((q, i) => (
                        <div key={i} className="flex items-start gap-2 bg-amber-50 rounded-lg p-2.5 text-xs text-amber-900">
                          <span className="font-mono text-amber-400 mt-px">{i+1}.</span>
                          <div className="flex-1">
                            <span>{q.question_text || q.question}</span>
                            {q.criticality && <span className={`ml-2 inline-flex px-1.5 py-0.5 rounded text-[9px] font-semibold ${q.criticality === 'CRITICAL' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>{q.criticality}</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 3. Repository Questions */}
                {(analysisData.repo_questions || []).length > 0 && (
                  <div className="bg-white rounded-xl border shadow-sm p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="inline-flex px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-100 text-indigo-700">REPO FORM</span>
                      <h3 className="text-sm font-semibold text-gray-900">Repository Questions</h3>
                      <span className="ml-auto text-xs font-semibold text-indigo-600">{(analysisData.repo_questions || []).length}</span>
                    </div>
                    <div className="space-y-1.5">
                      {(analysisData.repo_questions || []).map((q, i) => (
                        <div key={i} className="flex items-start gap-2 bg-indigo-50 rounded-lg p-2.5 text-xs text-indigo-900">
                          <span className="font-mono text-indigo-400 mt-px">{i+1}.</span>
                          <div className="flex-1">
                            <span>{q.question_text || q.question}</span>
                            {q.source_document && <span className="ml-2 text-[9px] text-indigo-400">({q.source_document})</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 4. Follow Up Questions */}
                {(analysisData.ai_questions || []).length > 0 && (
                  <div className="bg-white rounded-xl border shadow-sm p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="inline-flex px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-700">FOLLOW UP</span>
                      <h3 className="text-sm font-semibold text-gray-900">Follow Up Questions</h3>
                      <span className="ml-auto text-xs font-semibold text-purple-600">{(analysisData.ai_questions || []).length}</span>
                    </div>
                    <div className="space-y-1.5">
                      {(analysisData.ai_questions || []).map((q, i) => (
                        <div key={i} className="flex items-start gap-2 bg-purple-50 rounded-lg p-2.5 text-xs text-purple-900">
                          <span className="font-mono text-purple-400 mt-px">{i+1}.</span>
                          <div className="flex-1">
                            <span>{q.question || q.question_text}</span>
                            {q.criticality && <span className={`ml-2 inline-flex px-1.5 py-0.5 rounded text-[9px] font-semibold ${q.criticality === 'CRITICAL' ? 'bg-red-100 text-red-700' : q.criticality === 'HIGH' ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600'}`}>{q.criticality}</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Reasoning */}
                {a.reasoning && (
                  <div className="bg-white rounded-xl border shadow-sm p-5">
                    <h3 className="text-sm font-semibold text-gray-900 mb-3">Reasoning</h3>
                    <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap">{a.reasoning}</p>
                  </div>
                )}

                {/* CIOMS Details (shown for PDF-ingested CIOMS cases) */}
                <CiomsDetailsSection caseData={cd} />

                {/* Decision Factors */}
                {a.decision_factors && Object.keys(a.decision_factors).length > 0 && (
                  <div className="bg-white rounded-xl border shadow-sm p-5">
                    <h3 className="text-sm font-semibold text-gray-900 mb-3">Decision Factors</h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                      {Object.entries(a.decision_factors).map(([k, v]) => (
                        <div key={k} className="bg-gray-50 rounded-lg p-3">
                          <p className="text-[10px] text-gray-400 uppercase tracking-wide mb-0.5">{k.replace(/_/g, ' ')}</p>
                          <p className="text-sm font-medium text-gray-900">{typeof v === 'boolean' ? (v ? 'Yes' : 'No') : String(v)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {/* ── DECISION TAB ──────────────────────────── */}
            {activeTab === 'decision' && <AgenticDecisionTab analysis={_analysis} />}

            {/* ── FOLLOW-UP STRATEGY TAB ───────────────────── */}
            {activeTab === 'followup' && (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <StrategyCard label="Recommended Timing" value={a.followup_priority || 'Standard'} sub={`${a.followup_frequency ?? '—'}h interval`} icon={
                    <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                  } />
                  <StrategyCard label="Recommended Channel" value={
                    (a.risk_level === 'HIGH' || a.risk_level === 'CRITICAL') ? 'Phone + WhatsApp + Email' : 'Email'
                  } sub="Based on risk level" icon={
                    <svg className="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
                  } />
                  <StrategyCard label="Engagement Risk" value={a.engagement_risk || 'N/A'} sub={`Response prob: ${pct(a.response_probability)}%`} icon={
                    <svg className="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>
                  } />
                  <StrategyCard label="Follow-Up Frequency" value={`Every ${a.followup_frequency ?? '—'}h`} sub={`${a.days_to_deadline ?? '—'} days to deadline`} icon={
                    <svg className="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                  } />
                </div>

                {/* Escalation alert */}
                {a.escalation_needed && (
                  <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
                    <svg className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>
                    <div>
                      <p className="text-sm font-semibold text-red-800">Escalation Required</p>
                      <p className="text-xs text-red-700 mt-0.5">{a.escalation_reason || 'Case requires immediate supervisor review'}</p>
                    </div>
                  </div>
                )}

                {/* Questions preview */}
                {(a.questions || a.missing_fields || []).length > 0 && (
                  <div className="bg-white rounded-xl border shadow-sm p-5">
                    <h3 className="text-sm font-semibold text-gray-900 mb-3">Top Follow-Up Questions <span className="text-gray-400 font-normal">({(a.questions || a.missing_fields || []).length})</span></h3>
                    <div className="space-y-2">
                      {(a.questions || a.missing_fields || []).slice(0, 8).map((q, i) => (
                        <div key={i} className="flex items-start gap-3 bg-gray-50 rounded-lg p-3">
                          <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">{i + 1}</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-gray-800">{q.question || q.field_display || q.field_name || q.field}</p>
                            <div className="flex items-center gap-3 mt-1">
                              <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                                q.criticality === 'CRITICAL' ? 'bg-red-100 text-red-700' :
                                q.criticality === 'HIGH' ? 'bg-amber-100 text-amber-700' :
                                'bg-gray-100 text-gray-600'
                              }`}>{q.criticality}</span>
                              {q.value_score != null && <span className="text-[10px] text-gray-400">Value: {(q.value_score * 100).toFixed(0)}%</span>}
                              {q.safety_impact && <span className="text-[10px] text-gray-400">{q.safety_impact}</span>}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Automated follow-up result */}
                {analysisData.automated_followup?.success && (
                  <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-start gap-3">
                    <svg className="w-5 h-5 text-emerald-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-emerald-800">Follow-Up Sent via {analysisData.automated_followup.channel}</p>
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-100 text-emerald-700 border border-emerald-300">
                          <span className="relative flex h-1.5 w-1.5">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-600"></span>
                          </span>
                          AUTO
                        </span>
                      </div>
                      <p className="text-xs text-emerald-700 mt-0.5">
                        {analysisData.automated_followup.questions_count} questions sent to{' '}
                        {analysisData.automated_followup.contact_info?.email || analysisData.automated_followup.contact_info?.phone || 'contact'}
                      </p>
                    </div>
                  </div>
                )}
              </>
            )}

            {/* ── QUESTION SCORING TAB ─────────────────────── */}
            {activeTab === 'questions' && <QuestionScoringTab analysis={_analysis} caseId={analysisData?.primaryid || analysisData?.case_id || caseId} />}

          </div>

          {/* RIGHT — insights panel */}
          <div className="hidden xl:block w-[300px] flex-shrink-0 space-y-5">

            {/* Mini Completeness */}
            <div className="bg-white rounded-xl border shadow-sm p-5">
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">Completeness</h4>
              <div className="flex justify-center mb-3">
                <RingGauge value={a.completeness_score || 0} size={80} stroke={8}
                  color={pct(a.completeness_score) >= 80 ? '#10b981' : pct(a.completeness_score) >= 60 ? '#3b82f6' : '#ef4444'}
                  label={`${pct(a.completeness_score)}%`} />
              </div>
              <div className="flex justify-between text-[10px] text-gray-400 mt-2">
                <span>Missing: {fieldCounts.total}</span>
                <span>Answered: {a.answered_fields?.length ?? 0}</span>
              </div>
            </div>

            {/* Risk Gauge */}
            <div className="bg-white rounded-xl border shadow-sm p-5">
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">Risk Assessment</h4>
              <div className="flex justify-center mb-3">
                <RingGauge value={a.risk_score || 0} size={80} stroke={8}
                  color={(a.risk_score || 0) >= 0.7 ? '#ef4444' : (a.risk_score || 0) >= 0.4 ? '#f59e0b' : '#10b981'}
                  label={`${pct(a.risk_score)}%`} />
              </div>
              <div className="text-center">
                <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-semibold ${riskBg(a.risk_score || 0)}`}>{a.risk_level || 'N/A'}</span>
              </div>
            </div>

            {/* Lifecycle Status */}
            <div className="bg-white rounded-xl border shadow-sm p-5">
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Lifecycle</h4>
              <div className="space-y-2.5">
                {LIFECYCLE_STEPS.map((step, i) => (
                  <div key={step} className="flex items-center gap-2.5">
                    <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${
                      i < currentStep ? 'bg-emerald-100 text-emerald-600' :
                      i === currentStep ? 'bg-blue-100 text-blue-600' :
                      'bg-gray-100 text-gray-400'
                    }`}>
                      {i < currentStep ? (
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth={3} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/></svg>
                      ) : (
                        <span className="text-[10px] font-bold">{i + 1}</span>
                      )}
                    </div>
                    <span className={`text-xs ${i === currentStep ? 'text-blue-700 font-semibold' : i < currentStep ? 'text-gray-700' : 'text-gray-400'}`}>{step}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick Stats */}
            <div className="bg-white rounded-xl border shadow-sm p-5">
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Quick Stats</h4>
              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between"><span className="text-gray-500">Decision</span><span className={`font-semibold ${dm.cls} px-1.5 py-0.5 rounded`}>{a.decision || 'PENDING'}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Confidence</span><span className="font-semibold text-gray-900">{pct(a.confidence)}%</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Response Prob.</span><span className="font-semibold text-gray-900">{pct(a.response_probability)}%</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Engagement</span><span className="font-medium text-gray-700">{a.engagement_risk || 'N/A'}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Priority</span><span className="font-medium text-gray-700">{a.followup_priority || a.priority || 'N/A'}</span></div>
                {a.previous_attempts?.length > 0 && (
                  <div className="flex justify-between"><span className="text-gray-500">Prev Attempts</span><span className="font-semibold text-gray-900">{a.previous_attempts.length}</span></div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════
   SUB-COMPONENTS
   ═══════════════════════════════════════════════════════════════ */
const KpiMini = ({ label, value, sub, color }) => (
  <div className="bg-white rounded-xl border shadow-sm p-4">
    <p className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold">{label}</p>
    <p className={`text-2xl font-bold mt-1 ${color || 'text-gray-900'}`}>{value}</p>
    <p className="text-xs text-gray-500 mt-0.5">{sub}</p>
  </div>
);

const InfoRow = ({ label, value, badge }) => (
  <div className="flex items-center justify-between">
    <span className="text-xs text-gray-500">{label}</span>
    {badge ? (
      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${badge}`}>{value || 'N/A'}</span>
    ) : (
      <span className="text-sm font-medium text-gray-900">{value ?? 'N/A'}</span>
    )}
  </div>
);

const SeverityCount = ({ label, count, cls }) => (
  <div className={`rounded-lg p-3 ${cls}`}>
    <p className="text-[10px] uppercase tracking-wide opacity-70">{label}</p>
    <p className="text-xl font-bold">{count}</p>
  </div>
);

const StrategyCard = ({ label, value, sub, icon }) => (
  <div className="bg-white rounded-xl border shadow-sm p-5">
    <div className="flex items-center gap-2 mb-2">{icon}<span className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold">{label}</span></div>
    <p className="text-sm font-bold text-gray-900">{value}</p>
    <p className="text-xs text-gray-500 mt-0.5">{sub}</p>
  </div>
);

const MetaItem = ({ label, value }) => (
  <div className="bg-gray-50 rounded-lg p-3">
    <p className="text-[10px] text-gray-400 uppercase tracking-wide">{label}</p>
    <p className="text-sm font-medium text-gray-900 mt-0.5">{value || 'N/A'}</p>
  </div>
);

export default CaseAnalysis;
