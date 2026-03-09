import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../utils/api';

const LifecycleTracking = () => {
  const { caseId } = useParams();
  const navigate = useNavigate();

  const [lifecycle, setLifecycle] = useState(null);
  const [summary, setSummary] = useState(null);
  const [policies, setPolicies] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [inputCaseId, setInputCaseId] = useState(caseId || '');

  const fetchLifecycleData = useCallback(async (id) => {
    if (!id) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    try {
      const response = await api.getLifecycleStatus(id);
      if (response.success) {
        setLifecycle(response.lifecycle || null);
        setSummary(response.summary || null);
      } else {
        setError(response.message || 'Failed to fetch lifecycle data');
      }
    } catch (err) {
      if (err.message?.includes('404') || err.message?.includes('not found')) {
        setError(`Lifecycle not found for case ${id}. Initialize lifecycle first.`);
      } else {
        setError(err.message || 'Failed to fetch lifecycle data');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchPolicies = useCallback(async () => {
    try {
      const res = await api.getLifecyclePolicies();
      if (res.success) setPolicies(res.policies);
    } catch { /* policies are optional */ }
  }, []);

  useEffect(() => {
    fetchPolicies();
    if (caseId) { fetchLifecycleData(caseId); } else { setLoading(false); }
  }, [caseId, fetchLifecycleData, fetchPolicies]);

  const handleSearch = (e) => {
    e.preventDefault();
    if (inputCaseId.trim()) navigate(`/lifecycle/${inputCaseId.trim()}`);
  };

  const handleRefresh = () => { if (caseId) fetchLifecycleData(caseId); };

  return (
    <div className="min-h-screen bg-[#F7F9FC]">
      <div className="max-w-[1320px] mx-auto px-5 py-5 space-y-4">

        {/* ── HEADER + SEARCH ─────────────────────────── */}
        <div className="bg-white rounded-lg border border-[#E5E7EB] shadow-sm px-6 py-4">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <h1 className="text-lg font-semibold text-gray-900">Lifecycle Tracking</h1>
              <p className="text-[11px] text-gray-400 mt-0.5">Follow-up lifecycle monitoring and safety governance</p>
            </div>
            <form onSubmit={handleSearch} className="flex gap-2">
              <input
                type="text"
                value={inputCaseId}
                onChange={e => setInputCaseId(e.target.value)}
                placeholder="Enter Case ID..."
                className="px-3 py-1.5 border border-gray-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-[#2563EB] bg-gray-50 w-52"
              />
              <button type="submit" className="px-3 py-1.5 bg-[#2563EB] text-white rounded text-xs font-medium hover:bg-blue-700">
                Load
              </button>
              {caseId && (
                <button type="button" onClick={handleRefresh} className="px-3 py-1.5 border border-gray-200 text-gray-600 rounded text-xs hover:bg-gray-50">
                  Refresh
                </button>
              )}
            </form>
          </div>
        </div>

        {/* ── EMPTY / LOADING / ERROR ─────────────────── */}
        {!caseId && !loading && (
          <EmptyState title="Enter a Case ID to View Lifecycle" sub="Use the search box above to load lifecycle tracking data for a specific case." />
        )}

        {loading && (
          <div className="bg-white rounded-lg border border-[#E5E7EB] p-12 text-center">
            <div className="animate-spin rounded-full h-10 w-10 border-2 border-gray-300 border-t-[#2563EB] mx-auto" />
            <p className="mt-3 text-sm text-gray-500">Loading lifecycle data...</p>
          </div>
        )}

        {error && !loading && (
          <div className="bg-white rounded-lg border border-red-200 p-5">
            <div className="flex items-start gap-3">
              <span className="w-2 h-2 rounded-full bg-red-500 mt-1.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-red-800">Error Loading Lifecycle</p>
                <p className="text-xs text-red-600 mt-0.5">{error}</p>
                <button onClick={handleRefresh} className="mt-2 px-3 py-1 border border-red-200 text-red-700 rounded text-xs hover:bg-red-50">Retry</button>
              </div>
            </div>
          </div>
        )}

        {!lifecycle && !loading && !error && caseId && (
          <EmptyState title="No Lifecycle Data" sub="Lifecycle tracking has not been initialized for this case." />
        )}

        {/* ── DASHBOARD (when lifecycle loaded) ────────── */}
        {lifecycle && !loading && (
          <>
            {/* STATUS STRIP */}
            <StatusStrip lifecycle={lifecycle} summary={summary} />

            {/* LIFECYCLE TIMELINE */}
            <LifecycleTimeline lifecycle={lifecycle} />

            {/* 2-COLUMN: Activity Log + Policy/Compliance */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
              <div className="lg:col-span-7">
                <ActivityLog lifecycle={lifecycle} />
              </div>
              <div className="lg:col-span-5 space-y-4">
                <PolicyCards policies={policies} reporterType={lifecycle.reporter_type} reporterSubtype={lifecycle.reporter_subtype} />
              </div>
            </div>

            {/* FOLLOW-UP PROGRESS */}
            <FollowUpProgress lifecycle={lifecycle} />
          </>
        )}
      </div>
    </div>
  );
};

export default LifecycleTracking;


/* ═══════════════════════════════════════════════════════════
   SUB-COMPONENTS
   ═══════════════════════════════════════════════════════════ */

function EmptyState({ title, sub }) {
  return (
    <div className="bg-white rounded-lg border border-[#E5E7EB] p-12 text-center">
      <p className="text-sm font-medium text-gray-700 mb-1">{title}</p>
      <p className="text-xs text-gray-400">{sub}</p>
    </div>
  );
}


/* ── STATUS STRIP ─────────────────────────────────────── */
function StatusStrip({ lifecycle, summary }) {
  const d = summary || lifecycle || {};
  const caseId = d.case_id || lifecycle?.case_id || '—';
  const stage = d.lifecycle_status || lifecycle?.lifecycle_status || 'active';
  const response = d.response_status || lifecycle?.response_status || 'pending';
  const escalation = d.escalation_status || lifecycle?.escalation_status || 'none';
  const reporter = d.reporter_type || lifecycle?.reporter_type || '—';
  const reporterSub = d.reporter_subtype || lifecycle?.reporter_subtype || '';
  const deadCase = d.dead_case_flag ?? lifecycle?.dead_case_flag ?? false;
  const daysRemaining = d.days_remaining ?? lifecycle?.days_remaining ?? null;

  const stageColor = stage === 'closed' || stage === 'completed' ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
    : stage === 'dead_case' || deadCase ? 'text-red-700 bg-red-50 border-red-200'
    : 'text-[#2563EB] bg-blue-50 border-blue-200';

  const escColor = escalation === 'none' ? 'text-gray-500 bg-gray-50 border-gray-200'
    : escalation === 'flagged' ? 'text-amber-700 bg-amber-50 border-amber-200'
    : 'text-red-700 bg-red-50 border-red-200';

  const respColor = response === 'complete' ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
    : response === 'partial' ? 'text-amber-700 bg-amber-50 border-amber-200'
    : 'text-gray-500 bg-gray-50 border-gray-200';

  return (
    <div className="bg-white rounded-lg border border-[#E5E7EB] shadow-sm px-6 py-3.5">
      <div className="flex items-center justify-between flex-wrap gap-y-2 gap-x-5">
        <StatusChip label="Case ID" value={caseId.length > 16 ? `${caseId.substring(0, 16)}...` : caseId} mono />
        <Sep />
        <StatusChip label="Reporter" value={reporterSub ? `${reporter} (${reporterSub})` : reporter} />
        <Sep />
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-400 uppercase tracking-wider">Stage</span>
          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${stageColor}`}>
            {stage.replace(/_/g, ' ').toUpperCase()}
          </span>
        </div>
        <Sep />
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-400 uppercase tracking-wider">Follow-up</span>
          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${respColor}`}>
            {response.toUpperCase()}
          </span>
        </div>
        <Sep />
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-400 uppercase tracking-wider">Escalation</span>
          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${escColor}`}>
            {escalation.replace(/_/g, ' ').toUpperCase()}
          </span>
        </div>
        {daysRemaining !== null && (
          <>
            <Sep />
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-gray-400 uppercase tracking-wider">Days Left</span>
              <span className={`text-xs font-bold ${daysRemaining <= 2 ? 'text-red-600' : daysRemaining <= 5 ? 'text-amber-600' : 'text-emerald-600'}`}>
                {daysRemaining}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function StatusChip({ label, value, mono }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-gray-400 uppercase tracking-wider">{label}</span>
      <span className={`text-xs font-medium text-gray-800 ${mono ? 'font-mono' : ''}`}>{value}</span>
    </div>
  );
}
function Sep() { return <span className="hidden sm:block w-px h-5 bg-gray-200" />; }


/* ── LIFECYCLE TIMELINE ───────────────────────────────── */
function LifecycleTimeline({ lifecycle }) {
  const attemptCount = lifecycle.attempt_count ?? 0;
  const escalation = lifecycle.escalation_status || 'none';
  const deadCase = lifecycle.dead_case_flag ?? false;
  const response = lifecycle.response_status || 'pending';
  const status = lifecycle.lifecycle_status || 'active';

  const isClosed = deadCase || response === 'complete' || status === 'closed' || status === 'completed' || status === 'dead_case';
  const isEscalated = escalation !== 'none';

  const steps = [
    { id: 'intake', label: 'Intake', completed: true, active: attemptCount === 0 && !isClosed },
    { id: 'validation', label: 'Validation', completed: attemptCount >= 1, active: attemptCount >= 1 && response === 'pending' && !isEscalated && !isClosed },
    { id: 'followup', label: 'Follow-Up', completed: response === 'partial' || response === 'complete', active: (response === 'partial' || (attemptCount >= 1 && response !== 'pending')) && !isEscalated && !isClosed },
    { id: 'review', label: 'Medical Review', completed: isEscalated, active: isEscalated && !isClosed, escalated: isEscalated },
    { id: 'closure', label: 'Closure', completed: isClosed, active: isClosed, dead: deadCase, success: response === 'complete' && !deadCase },
  ];

  const activeIdx = steps.reduce((acc, s, i) => s.active ? i : acc, 0);

  return (
    <div className="bg-white rounded-lg border border-[#E5E7EB] shadow-sm p-6">
      <div className="px-1 pb-2">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Lifecycle Timeline</h2>
      </div>

      <div className="relative mt-4">
        {/* Track */}
        <div className="absolute top-4 left-0 right-0 h-[2px] bg-gray-200" />
        <div className="absolute top-4 left-0 h-[2px] bg-[#2563EB] transition-all" style={{ width: `${Math.max(0, (activeIdx / (steps.length - 1)) * 100)}%` }} />

        <div className="relative flex justify-between">
          {steps.map((step, i) => {
            let dotClass = 'bg-white border-gray-300 text-gray-400';
            if (step.completed) dotClass = 'bg-[#2563EB] border-[#2563EB] text-white';
            if (step.escalated && !step.completed) dotClass = 'bg-white border-red-500 text-red-500';
            if (step.dead) dotClass = 'bg-red-500 border-red-500 text-white';
            if (step.success) dotClass = 'bg-emerald-500 border-emerald-500 text-white';

            let labelClass = 'text-gray-400';
            if (step.active) labelClass = 'text-[#2563EB] font-semibold';
            else if (step.completed) labelClass = 'text-gray-700';

            return (
              <div key={step.id} className="flex flex-col items-center" style={{ width: `${100 / steps.length}%` }}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium border-2 transition-all ${dotClass}`}>
                  {step.completed ? (
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                  ) : i + 1}
                </div>
                <span className={`mt-1.5 text-[10px] text-center ${labelClass}`}>{step.label}</span>
                {step.active && !step.completed && <span className="text-[9px] text-[#2563EB] mt-0.5">Current</span>}
                {step.dead && <span className="text-[9px] text-red-500 mt-0.5">Dead Case</span>}
                {step.success && <span className="text-[9px] text-emerald-500 mt-0.5">Complete</span>}
              </div>
            );
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="mt-6 pt-3 border-t border-gray-100 flex items-center justify-center gap-5 text-[10px] text-gray-400">
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#2563EB]" />Completed</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full border-2 border-[#2563EB] bg-white" />Active</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full border-2 border-gray-300 bg-white" />Pending</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-red-500" />Escalated</span>
      </div>
    </div>
  );
}


/* ── ACTIVITY LOG ─────────────────────────────────────── */
function ActivityLog({ lifecycle }) {
  const auditLog = lifecycle.audit_log || [];
  const attempts = lifecycle.attempts || [];

  // Merge audit log and attempt entries into unified activity feed
  const activities = [];

  auditLog.forEach(entry => {
    activities.push({
      type: 'audit',
      timestamp: entry.timestamp,
      action: entry.action_description || entry.action_type || 'Action',
      actor: entry.actor || 'System',
      detail: entry.reason || null,
    });
  });

  attempts.forEach((a, i) => {
    activities.push({
      type: 'attempt',
      timestamp: a.sent_at || a.created_at,
      action: `Follow-up #${a.attempt_number || i + 1} sent via ${a.channel || 'N/A'}`,
      actor: 'System',
      detail: a.response_received ? `Response received (${a.questions_answered ?? 0} answered)` : 'Awaiting response',
    });
  });

  activities.sort((a, b) => {
    const da = a.timestamp ? new Date(a.timestamp) : new Date(0);
    const db = b.timestamp ? new Date(b.timestamp) : new Date(0);
    return db - da; // newest first
  });

  const fmt = (ts) => {
    if (!ts) return '—';
    try { return new Date(ts).toLocaleString(); } catch { return ts; }
  };

  return (
    <div className="bg-white rounded-lg border border-[#E5E7EB] shadow-sm">
      <div className="px-5 pt-5 pb-3 border-b border-gray-100 flex items-center justify-between">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Activity Log</h2>
        <span className="text-[10px] text-gray-400">{activities.length} entries</span>
      </div>
      <div className="overflow-y-auto divide-y divide-gray-50" style={{ maxHeight: 420 }}>
        {activities.length === 0 ? (
          <p className="text-xs text-gray-400 text-center py-10">No activity recorded yet.</p>
        ) : (
          activities.map((a, i) => (
            <div key={i} className="px-5 py-3 hover:bg-gray-50/50 transition-colors">
              <div className="flex items-start gap-3">
                <span className={`w-6 h-6 rounded-md flex items-center justify-center text-[9px] font-bold flex-shrink-0 mt-0.5 ${
                  a.type === 'attempt' ? 'bg-blue-50 text-[#2563EB] border border-blue-200' : 'bg-gray-50 text-gray-500 border border-gray-200'
                }`}>
                  {a.type === 'attempt' ? 'FU' : 'SY'}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-800">{a.action}</p>
                  {a.detail && <p className="text-[10px] text-gray-400 mt-0.5">{a.detail}</p>}
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-[10px] text-gray-400">{fmt(a.timestamp)}</p>
                  <p className="text-[9px] text-gray-300 mt-0.5">{a.actor}</p>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}


/* ── POLICY CARDS ─────────────────────────────────────── */
function PolicyCards({ policies, reporterType, reporterSubtype }) {
  const hcp = policies?.HCP_POLICY || null;
  const nonHcp = policies?.NON_HCP_POLICY || null;
  const isHcp = reporterType === 'HCP';
  const subtypeLabels = {
    'MD': 'Physician', 'HP': 'Health Professional', 'PH': 'Pharmacist',
    'RPH': 'Pharmacist', 'RN': 'Nurse', 'CN': 'Consumer', 'PT': 'Patient',
    'LW': 'Lawyer', 'OT': 'Other',
  };
  const subtypeLabel = subtypeLabels[reporterSubtype] || reporterSubtype || '';

  return (
    <div className="space-y-4">
      {/* Compliance badge */}
      <div className="bg-white rounded-lg border border-[#E5E7EB] shadow-sm px-5 py-3">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" />
          <span className="text-xs font-medium text-emerald-700">Policy Compliant</span>
          <span className="ml-auto text-[10px] text-gray-400">Active: {isHcp ? 'HCP' : 'NON_HCP'}{subtypeLabel ? ` (${subtypeLabel})` : ''}</span>
        </div>
      </div>

      {/* HCP Policy */}
      <PolicyCard
        title="Healthcare Professional"
        tag="HCP"
        active={isHcp}
        data={hcp || { max_attempts: 4, escalation_after_attempts: 3, questions_per_round: 5, escalate_to: 'medical_team', allow_auto_dead_case: false }}
      />

      {/* NON_HCP Policy */}
      <PolicyCard
        title="Consumer / Patient"
        tag="NON_HCP"
        active={!isHcp}
        data={nonHcp || { max_attempts: 3, escalation_after_attempts: 2, questions_per_round: 2, escalate_to: 'supervisor', allow_auto_dead_case: true }}
      />
    </div>
  );
}

function PolicyCard({ title, tag, active, data }) {
  const rows = [
    { label: 'Max Attempts', value: data.max_attempts ?? '—' },
    { label: 'Escalation Rule', value: data.escalation_after_attempts ? `After ${data.escalation_after_attempts} attempts` : '—' },
    { label: 'Escalate To', value: data.escalate_to ? data.escalate_to.replace(/_/g, ' ') : '—' },
    { label: 'Questions / Round', value: data.questions_per_round ?? '—' },
    { label: 'Auto Close Allowed', value: data.allow_auto_dead_case ? 'Yes' : 'No' },
  ];

  return (
    <div className={`bg-white rounded-lg border shadow-sm ${active ? 'border-[#2563EB]' : 'border-[#E5E7EB]'}`}>
      <div className={`px-4 py-2.5 border-b flex items-center justify-between ${active ? 'border-blue-100 bg-blue-50/30' : 'border-gray-100'}`}>
        <div className="flex items-center gap-2">
          <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${active ? 'bg-[#2563EB] text-white' : 'bg-gray-100 text-gray-500'}`}>{tag}</span>
          <span className="text-xs font-medium text-gray-800">{title}</span>
        </div>
        {active && <span className="text-[9px] text-[#2563EB] font-semibold">ACTIVE</span>}
      </div>
      <div className="divide-y divide-gray-50">
        {rows.map((r, i) => (
          <div key={r.label} className={`flex items-center justify-between px-4 py-2 text-[11px] ${i % 2 === 0 ? 'bg-gray-50/40' : ''}`}>
            <span className="text-gray-500">{r.label}</span>
            <span className="text-gray-800 font-medium">{r.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}


/* ── FOLLOW-UP PROGRESS ───────────────────────────────── */
function FollowUpProgress({ lifecycle }) {
  const attemptCount = lifecycle.attempt_count ?? 0;
  const maxAttempts = lifecycle.max_attempts ?? 3;
  const remaining = Math.max(0, maxAttempts - attemptCount);
  const qSent = lifecycle.total_questions_sent ?? 0;
  const qAnswered = lifecycle.total_questions_answered ?? 0;
  const completeness = lifecycle.completeness_score ?? 0;
  const safety = lifecycle.safety_confidence_score ?? 0;
  const target = lifecycle.target_completeness ?? 0.85;
  const mandatory = lifecycle.mandatory_fields_complete ?? false;
  const completePct = Math.round(completeness * 100);
  const safetyPct = Math.round(safety * 100);
  const targetPct = Math.round(target * 100);

  const progressColor = completeness >= target ? 'bg-emerald-500' : completeness >= 0.5 ? 'bg-amber-500' : 'bg-red-500';
  const safetyColor = safety >= 0.8 ? 'bg-emerald-500' : safety >= 0.5 ? 'bg-amber-500' : 'bg-red-500';

  return (
    <div className="bg-white rounded-lg border border-[#E5E7EB] shadow-sm">
      <div className="px-6 pt-5 pb-3 border-b border-gray-100">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Follow-Up Progress</h2>
      </div>
      <div className="p-5">
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Attempts Used */}
          <div className="bg-gray-50 rounded-lg p-3.5 border border-gray-100">
            <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">Attempts Used</p>
            <p className="text-xl font-bold text-gray-900 mt-1">{attemptCount} <span className="text-sm font-normal text-gray-400">/ {maxAttempts}</span></p>
            <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
              <div className="h-1.5 rounded-full bg-[#2563EB] transition-all" style={{ width: `${Math.min((attemptCount / maxAttempts) * 100, 100)}%` }} />
            </div>
          </div>

          {/* Attempts Remaining */}
          <div className="bg-gray-50 rounded-lg p-3.5 border border-gray-100">
            <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">Remaining</p>
            <p className={`text-xl font-bold mt-1 ${remaining === 0 ? 'text-red-600' : remaining <= 1 ? 'text-amber-600' : 'text-gray-900'}`}>{remaining}</p>
            <p className="text-[10px] text-gray-400 mt-1">attempts left</p>
          </div>

          {/* Questions */}
          <div className="bg-gray-50 rounded-lg p-3.5 border border-gray-100">
            <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">Questions</p>
            <p className="text-xl font-bold text-gray-900 mt-1">{qAnswered} <span className="text-sm font-normal text-gray-400">/ {qSent}</span></p>
            <p className="text-[10px] text-gray-400 mt-1">answered / sent</p>
          </div>

          {/* Completion */}
          <div className="bg-gray-50 rounded-lg p-3.5 border border-gray-100">
            <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">Completion</p>
            <div className="flex items-baseline gap-1.5 mt-1">
              <span className="text-xl font-bold text-gray-900">{completePct}%</span>
              <span className="text-[10px] text-gray-400">/ {targetPct}%</span>
            </div>
            <div className="relative w-full bg-gray-200 rounded-full h-1.5 mt-2">
              <div className={`h-1.5 rounded-full transition-all ${progressColor}`} style={{ width: `${completePct}%` }} />
              <div className="absolute top-0 w-[2px] h-1.5 bg-gray-600" style={{ left: `${targetPct}%` }} />
            </div>
          </div>

          {/* Safety */}
          <div className="bg-gray-50 rounded-lg p-3.5 border border-gray-100">
            <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">Safety Confidence</p>
            <p className="text-xl font-bold text-gray-900 mt-1">{safetyPct}%</p>
            <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
              <div className={`h-1.5 rounded-full transition-all ${safetyColor}`} style={{ width: `${safetyPct}%` }} />
            </div>
          </div>
        </div>

        {/* Mandatory fields + closure */}
        <div className="mt-4 flex items-center gap-4 text-[10px]">
          <div className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${mandatory ? 'bg-emerald-500' : 'bg-red-500'}`} />
            <span className="text-gray-500">Mandatory Fields: <strong className={mandatory ? 'text-emerald-700' : 'text-red-700'}>{mandatory ? 'Complete' : 'Incomplete'}</strong></span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${completeness >= target && mandatory ? 'bg-emerald-500' : 'bg-gray-300'}`} />
            <span className="text-gray-500">Closure Eligible: <strong className={completeness >= target && mandatory ? 'text-emerald-700' : 'text-gray-500'}>{completeness >= target && mandatory ? 'Yes' : 'No'}</strong></span>
          </div>
        </div>
      </div>
    </div>
  );
}
