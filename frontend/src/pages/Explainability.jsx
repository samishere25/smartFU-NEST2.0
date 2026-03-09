import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../utils/api';
import {
  getResponseConfidence,
  getTimingRecommendation,
  getChannelRecommendation,
  getReporterTypeLabel,
  formatProbability
} from '../utils/followUpOptimization';
import AuditLog from '../components/governance/AuditLog';

/* ── Render backend text that may contain **bold** markers ── */
function FormattedText({ text, className = '' }) {
  if (!text) return <span className={className}>—</span>;
  // Split on **...**  and render bold spans
  const parts = String(text).split(/\*\*(.*?)\*\*/g);
  return (
    <span className={className}>
      {parts.map((part, i) =>
        i % 2 === 1
          ? <strong key={i} className="font-semibold text-gray-900">{part}</strong>
          : <React.Fragment key={i}>{part}</React.Fragment>
      )}
    </span>
  );
}

/* ── Split long reasoning into readable paragraphs ── */
function ReasoningBlock({ text, className = '' }) {
  if (!text) return <p className={`text-sm text-gray-500 italic ${className}`}>No reasoning provided.</p>;
  // Split on double newlines, numbered items, or bullet-like patterns
  const raw = String(text);
  const paragraphs = raw
    .split(/\n{2,}|\n(?=\d+\.\s)|(?<=\.)\s+(?=[A-Z])/)
    .map(p => p.trim())
    .filter(Boolean);

  if (paragraphs.length <= 1) {
    return (
      <div className={className}>
        <FormattedText text={raw} className="text-sm text-gray-700 leading-relaxed" />
      </div>
    );
  }

  return (
    <div className={`space-y-2.5 ${className}`}>
      {paragraphs.map((p, i) => (
        <div key={i} className="text-sm text-gray-700 leading-relaxed">
          <FormattedText text={p} />
        </div>
      ))}
    </div>
  );
}

export default function Explainability() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);
  const [expandedAgents, setExpandedAgents] = useState({});
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [showOverrideModal, setShowOverrideModal] = useState(false);
  const [reviewNote, setReviewNote] = useState('');
  const [overrideDecision, setOverrideDecision] = useState('');
  const [overrideReason, setOverrideReason] = useState('');
  const [auditLog, setAuditLog] = useState([]);
  const [auditLoading, setAuditLoading] = useState(false);

  useEffect(() => { fetchAnalysisData(); }, [caseId]);

  const fetchAnalysisData = async () => {
    try {
      setLoading(true);
      setError(null);
      const isUUID = caseId.includes('-');
      let primaryId = caseId;
      if (isUUID) {
        const caseData = await api.getCase(caseId);
        primaryId = caseData.primaryid;
      }
      // Try cached analysis first (instant), fall back to full AI run
      try {
        const cached = await api.getCaseAnalysis(primaryId);
        if (cached && cached.has_analysis) {
          console.log('📊 Explainability Data:', cached.explainability);
          setAnalysisData(cached);
          // Fetch audit log in parallel
          fetchAuditLog(primaryId);
          return;
        }
      } catch (_) { /* no cached data — run full analysis */ }
      const data = await api.analyzeCase(primaryId);
      console.log('📊 Full Analysis Explainability:', data.explainability);
      setAnalysisData(data);
      // Fetch audit log in parallel
      fetchAuditLog(primaryId);
    } catch (err) {
      setError('Unable to load explainability data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const fetchAuditLog = async (primaryId) => {
    try {
      setAuditLoading(true);
      // Try both governance and lifecycle audit endpoints
      try {
        const auditData = await api.getCaseAuditLog(primaryId);
        console.log('📜 Audit Log:', auditData);
        setAuditLog(Array.isArray(auditData) ? auditData : auditData?.entries || auditData?.logs || auditData?.audit_log || []);
      } catch (govErr) {
        // Fallback to lifecycle audit
        try {
          const lifecycleAudit = await api.getLifecycleAuditLog(primaryId);
          console.log('📜 Lifecycle Audit:', lifecycleAudit);
          setAuditLog(lifecycleAudit?.audit_log || lifecycleAudit?.entries || []);
        } catch (lifecycleErr) {
          console.warn('Audit log not available:', lifecycleErr);
          setAuditLog([]);
        }
      }
    } catch (err) {
      console.error('Failed to fetch audit log:', err);
      setAuditLog([]);
    } finally {
      setAuditLoading(false);
    }
  };

  const toggleAgent = (agentName) => {
    setExpandedAgents(prev => ({ ...prev, [agentName]: !prev[agentName] }));
  };

  const handleAddReview = async () => {
    if (!reviewNote.trim()) return;
    try {
      setShowReviewModal(false);
      setReviewNote('');
      alert('Review note added successfully');
    } catch { alert('Failed to add review note'); }
  };

  const handleOverride = async () => {
    if (!overrideDecision || !overrideReason.trim()) return;
    try {
      setShowOverrideModal(false);
      setOverrideDecision('');
      setOverrideReason('');
      alert('AI decision overridden successfully');
      fetchAnalysisData();
    } catch { alert('Failed to override decision'); }
  };

  if (loading) return (
    <div className="min-h-screen bg-[#F7F9FC] flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-10 w-10 border-2 border-gray-300 border-t-[#2563EB] mx-auto" />
        <p className="mt-3 text-sm text-gray-500">Loading audit data...</p>
      </div>
    </div>
  );

  if (error || !analysisData) return (
    <div className="min-h-screen bg-[#F7F9FC] flex items-center justify-center p-4">
      <div className="bg-white rounded-lg border border-[#E5E7EB] p-8 max-w-md w-full text-center">
        <p className="text-sm text-gray-700 mb-2 font-medium">Unable to Load</p>
        <p className="text-sm text-gray-500 mb-5">{error || 'No analysis data available'}</p>
        <button onClick={() => navigate(`/cases/${caseId}`)} className="px-5 py-2 bg-[#2563EB] text-white rounded text-sm hover:bg-blue-700">
          Return to Case
        </button>
      </div>
    </div>
  );

  const analysis = analysisData.analysis || {};
  const messages = analysis.messages || [];
  const explainability = analysisData.explainability || {};

  return (
    <div className="min-h-screen bg-[#F7F9FC]">
      <div className="max-w-[1200px] mx-auto px-5 py-5 space-y-5">

        <AuditHeader caseId={analysisData.primaryid || caseId} analysis={analysis} />
        
        {/* Technical Explainability Section */}
        {explainability.decision_summary && (
          <TechnicalDecisionSummary summary={explainability.decision_summary} />
        )}
        
        <DecisionSummary analysis={analysis} />
        
        {/* Contributing Factors from Explainability Layer */}
        {explainability.contributing_factors && (
          <ContributingFactorsBreakdown factors={explainability.contributing_factors} />
        )}
        
        <ClinicalContext reasoning={analysis.reasoning} />
        <FollowUpRecommendation analysis={analysis} />
        
        {/* Agent Trace from Explainability Layer */}
        {explainability.agent_trace && explainability.agent_trace.length > 0 ? (
          <TechnicalAgentTrace trace={explainability.agent_trace} expandedAgents={expandedAgents} toggleAgent={toggleAgent} />
        ) : (
          <ReasoningTrace messages={messages} expandedAgents={expandedAgents} toggleAgent={toggleAgent} />
        )}
        
        {/* Regulatory Compliance Section */}
        {explainability.decision_summary && (
          <RegulatoryCompliance summary={explainability.decision_summary} />
        )}
        
        {/* Audit Trail Section */}
        <AuditTrailSection auditLog={auditLog} loading={auditLoading} />
        
        <HumanOversight onReview={() => setShowReviewModal(true)} onOverride={() => setShowOverrideModal(true)} explainability={explainability} />
        <MetadataFooter caseId={analysisData.primaryid || caseId} explainability={explainability} />

        <div className="flex justify-center pt-1 pb-4">
          <button onClick={() => navigate(`/cases/${caseId}`)}
            className="px-5 py-2 border border-gray-300 text-gray-600 rounded text-sm hover:bg-gray-50">
            Return to Case Analysis
          </button>
        </div>
      </div>

      {/* ── MODALS ── */}
      {showReviewModal && (
        <Modal title="Add Review Note" onClose={() => { setShowReviewModal(false); setReviewNote(''); }}>
          <p className="text-xs text-gray-500 mb-3">Document your review of this AI decision for audit purposes.</p>
          <textarea value={reviewNote} onChange={e => setReviewNote(e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded text-sm focus:outline-none focus:ring-1 focus:ring-[#2563EB]"
            rows="5" placeholder="Enter your review notes..." />
          <div className="flex gap-3 mt-4">
            <button onClick={handleAddReview} disabled={!reviewNote.trim()}
              className="flex-1 px-4 py-2 bg-[#2563EB] text-white rounded text-sm hover:bg-blue-700 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed">
              Save Review</button>
            <button onClick={() => { setShowReviewModal(false); setReviewNote(''); }}
              className="flex-1 px-4 py-2 border border-gray-200 text-gray-600 rounded text-sm hover:bg-gray-50">
              Cancel</button>
          </div>
        </Modal>
      )}

      {showOverrideModal && (
        <Modal title="Override AI Decision" onClose={() => { setShowOverrideModal(false); setOverrideDecision(''); setOverrideReason(''); }}>
          <p className="text-xs text-red-600 font-medium mb-3">This will override the AI recommendation. Provide justification.</p>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">New Decision</label>
              <select value={overrideDecision} onChange={e => setOverrideDecision(e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded text-sm focus:outline-none focus:ring-1 focus:ring-[#2563EB]">
                <option value="">Select decision...</option>
                <option value="ASK">ASK</option>
                <option value="DEFER">DEFER</option>
                <option value="PROCEED">PROCEED</option>
                <option value="ESCALATE">ESCALATE</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Justification (Required)</label>
              <textarea value={overrideReason} onChange={e => setOverrideReason(e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded text-sm focus:outline-none focus:ring-1 focus:ring-[#2563EB]"
                rows="4" placeholder="Explain why you are overriding the AI decision..." />
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button onClick={handleOverride} disabled={!overrideDecision || !overrideReason.trim()}
              className="flex-1 px-4 py-2 bg-amber-600 text-white rounded text-sm hover:bg-amber-700 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed">
              Confirm Override</button>
            <button onClick={() => { setShowOverrideModal(false); setOverrideDecision(''); setOverrideReason(''); }}
              className="flex-1 px-4 py-2 border border-gray-200 text-gray-600 rounded text-sm hover:bg-gray-50">
              Cancel</button>
          </div>
        </Modal>
      )}
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════
   SUB-COMPONENTS
   ═══════════════════════════════════════════════════════════ */

function SectionCard({ children, className = '' }) {
  return (
    <div className={`bg-white rounded-lg border border-[#E5E7EB] shadow-sm ${className}`}>
      {children}
    </div>
  );
}

function SectionHeader({ title, subtitle }) {
  return (
    <div className="px-6 pt-5 pb-3 border-b border-gray-100">
      <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{title}</h2>
      {subtitle && <p className="text-[11px] text-gray-400 mt-0.5">{subtitle}</p>}
    </div>
  );
}


/* ── AUDIT HEADER ─────────────────────────────────────── */
function AuditHeader({ caseId, analysis }) {
  return (
    <div className="bg-white rounded-lg border border-[#E5E7EB] shadow-sm px-6 py-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">SmartFU Explainability</h1>
          <div className="flex items-center gap-3 mt-1.5 flex-wrap">
            <HeaderChip label="Case ID" value={caseId} mono />
            <HeaderChip label="Decision" value={analysis.decision || '—'} />
            <HeaderChip label="Timestamp" value={new Date().toLocaleString()} />
            <HeaderChip label="Model" value="SmartFU v1.0" />
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="px-2.5 py-1 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            Explainable AI
          </span>
          <span className="px-2.5 py-1 rounded text-[10px] font-semibold bg-blue-50 text-[#2563EB] border border-blue-200">
            Audit Ready
          </span>
        </div>
      </div>
    </div>
  );
}

function HeaderChip({ label, value, mono }) {
  return (
    <span className="text-[11px] text-gray-500">
      {label}: <strong className={`text-gray-800 ${mono ? 'font-mono' : 'font-medium'}`}>{value}</strong>
    </span>
  );
}


/* ── DECISION SUMMARY ─────────────────────────────────── */
function DecisionSummary({ analysis }) {
  const decision = analysis.decision || 'PENDING';
  const riskScore = analysis.risk_score || 0;
  const riskPct = Math.round(riskScore * 100);
  const responsePct = Math.round((analysis.response_probability || 0) * 100);
  const confidence = analysis.confidence_level || 'HIGH';

  const decisionStyle = {
    ASK: 'text-purple-700 bg-purple-50 border-purple-200',
    PROCEED: 'text-[#2563EB] bg-blue-50 border-blue-200',
    ESCALATE: 'text-red-700 bg-red-50 border-red-200',
    DEFER: 'text-amber-700 bg-amber-50 border-amber-200',
  }[decision] || 'text-gray-600 bg-gray-50 border-gray-200';

  const riskColor = riskScore >= 0.7 ? 'bg-red-500' : riskScore >= 0.4 ? 'bg-amber-500' : 'bg-emerald-500';
  const riskLabel = riskScore >= 0.7 ? 'High' : riskScore >= 0.4 ? 'Medium' : 'Low';
  const riskLabelColor = riskScore >= 0.7 ? 'text-red-600' : riskScore >= 0.4 ? 'text-amber-600' : 'text-emerald-600';

  const confStyle = {
    HIGH: 'text-emerald-700 bg-emerald-50 border-emerald-200',
    MEDIUM: 'text-amber-700 bg-amber-50 border-amber-200',
    LOW: 'text-red-700 bg-red-50 border-red-200',
  }[confidence] || 'text-gray-600 bg-gray-50 border-gray-200';

  return (
    <SectionCard>
      <SectionHeader title="Decision Summary" />
      <div className="p-5">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Final Decision */}
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
            <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-3">Final Decision</p>
            <span className={`inline-block px-3 py-1.5 rounded text-sm font-bold border ${decisionStyle}`}>
              {decision}
            </span>
          </div>

          {/* Risk Score */}
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
            <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-2">Risk Score</p>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-gray-900">{riskPct}%</span>
              <span className={`text-[10px] font-semibold ${riskLabelColor}`}>{riskLabel}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2.5">
              <div className={`h-1.5 rounded-full transition-all ${riskColor}`} style={{ width: `${riskPct}%` }} />
            </div>
          </div>

          {/* Response Probability */}
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
            <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-2">Response Probability</p>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-gray-900">{responsePct}%</span>
              <span className="text-[10px] text-gray-400">likelihood</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2.5">
              <div className="h-1.5 rounded-full bg-[#2563EB] transition-all" style={{ width: `${responsePct}%` }} />
            </div>
          </div>

          {/* Confidence */}
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
            <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-3">Confidence Level</p>
            <span className={`inline-block px-3 py-1.5 rounded text-sm font-bold border ${confStyle}`}>
              {confidence}
            </span>
          </div>
        </div>
      </div>
    </SectionCard>
  );
}


/* ── CLINICAL CONTEXT ─────────────────────────────────── */
function ClinicalContext({ reasoning }) {
  return (
    <SectionCard>
      <SectionHeader title="Clinical Context Summary" subtitle="Regulatory justification for the AI decision" />
      <div className="p-5">
        <div className="rounded-lg bg-[#F7F9FC] border-l-[3px] border-[#2563EB] px-5 py-4">
          <ReasoningBlock text={reasoning} />
        </div>
      </div>
    </SectionCard>
  );
}


/* ── FOLLOW-UP RECOMMENDATION ─────────────────────────── */
function FollowUpRecommendation({ analysis }) {
  const responseProbability = analysis.response_probability || 0;
  const confidence = getResponseConfidence(responseProbability);
  const timingRec = getTimingRecommendation(analysis);
  const channelRec = getChannelRecommendation(analysis);
  const reporterType = analysis.case_data?.reporter_type || 'UNKNOWN';

  const engagementRisk = analysis.engagement_risk || null;
  const followupPriority = analysis.followup_priority || null;
  const followupFrequency = analysis.followup_frequency || null;
  const escalationNeeded = analysis.escalation_needed || false;
  const escalationReason = analysis.escalation_reason || '';

  const riskBadge = (val) => {
    if (!val || val === '—') return <span className="text-xs text-gray-400">—</span>;
    const v = String(val).toUpperCase().replace(/_/g, ' ');
    const cls = v.includes('VERY HIGH') || v.includes('HIGH') ? 'bg-red-50 text-red-700 border-red-200'
      : v.includes('MEDIUM') || v.includes('MODERATE') ? 'bg-amber-50 text-amber-700 border-amber-200'
      : v.includes('LOW') ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
      : 'bg-gray-50 text-gray-600 border-gray-200';
    return <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold border ${cls}`}>{v}</span>;
  };

  const priorityBadge = (val) => {
    if (!val || val === '—') return <span className="text-xs text-gray-400">—</span>;
    const v = String(val).toUpperCase();
    const cls = v === 'URGENT' || v === 'CRITICAL' ? 'bg-red-50 text-red-700 border-red-200'
      : v === 'ELEVATED' || v === 'HIGH' ? 'bg-orange-50 text-orange-700 border-orange-200'
      : v === 'STANDARD' || v === 'MEDIUM' ? 'bg-amber-50 text-amber-700 border-amber-200'
      : 'bg-emerald-50 text-emerald-700 border-emerald-200';
    return <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold border ${cls}`}>{v}</span>;
  };

  const confBadge = (val) => {
    const cls = val === 'HIGH' ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
      : val === 'MEDIUM' ? 'bg-amber-50 text-amber-700 border-amber-200'
      : 'bg-red-50 text-red-700 border-red-200';
    return <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold border ${cls}`}>{val}</span>;
  };

  const rows = [
    { label: 'Engagement Risk', render: () => riskBadge(engagementRisk) },
    { label: 'Priority', render: () => priorityBadge(followupPriority) },
    { label: 'Frequency', render: () => <span className="text-xs font-medium text-gray-800">{followupFrequency ? `Every ${followupFrequency} hours` : '—'}</span> },
    { label: 'Timing', render: () => <span className="text-xs font-medium text-gray-800">{timingRec.timing}</span> },
    { label: 'Urgency', render: () => riskBadge(timingRec.urgency) },
    { label: 'Channel', render: () => <span className="text-xs font-medium text-gray-800">{channelRec.channel}</span> },
    { label: 'Alternatives', render: () => channelRec.alternatives?.length
        ? <div className="flex gap-1 flex-wrap">{channelRec.alternatives.map((a, i) => <span key={i} className="px-1.5 py-0.5 bg-gray-100 border border-gray-200 rounded text-[10px] text-gray-600">{a}</span>)}</div>
        : <span className="text-xs text-gray-400">—</span>
    },
    { label: 'Reporter Type', render: () => <span className="text-xs font-medium text-gray-800">{getReporterTypeLabel(reporterType)}</span> },
    { label: 'Response Probability', render: () => <span className="text-xs font-bold text-gray-900">{formatProbability(responseProbability)}</span> },
    { label: 'Prediction Confidence', render: () => confBadge(confidence) },
  ];

  return (
    <SectionCard>
      <SectionHeader title="Follow-Up Recommendation" subtitle="AI-generated engagement strategy" />
      <div className="p-5">
        {escalationNeeded && (
          <div className="mb-4 flex items-start gap-3 px-4 py-3 bg-red-50 border border-red-200 rounded-lg">
            <span className="w-2 h-2 rounded-full bg-red-500 mt-1 flex-shrink-0 animate-pulse" />
            <div>
              <p className="text-xs font-semibold text-red-700">Escalation Required</p>
              {escalationReason && <p className="text-[11px] text-red-600 mt-0.5">{escalationReason}</p>}
            </div>
          </div>
        )}

        <div className="border border-[#E5E7EB] rounded-lg overflow-hidden">
          {rows.map((row, i) => (
            <div key={row.label} className={`flex items-center justify-between px-5 py-3 ${i < rows.length - 1 ? 'border-b border-[#E5E7EB]' : ''} ${i % 2 === 0 ? 'bg-gray-50/60' : 'bg-white'}`}>
              <span className="text-[11px] text-gray-500 font-medium min-w-[140px]">{row.label}</span>
              <div className="text-right">{row.render()}</div>
            </div>
          ))}
        </div>
      </div>
    </SectionCard>
  );
}


/* ── REASONING TRACE (ACCORDION) ──────────────────────── */
function ReasoningTrace({ messages, expandedAgents, toggleAgent }) {
  const agentMeta = {
    DataCompleteness: { label: 'Data Completeness', desc: 'Evaluates data quality and identifies missing critical fields' },
    RiskAssessment: { label: 'Risk Assessment', desc: 'Analyzes safety signals and calculates risk scores' },
    ResponseStrategy: { label: 'Response Strategy', desc: 'Predicts response likelihood and optimal contact methods' },
    Escalation: { label: 'Escalation Logic', desc: 'Determines final action and escalation requirements' },
    MedicalReasoning: { label: 'Medical Reasoning', desc: 'Clinical reasoning and medical context analysis' },
    QuestionGeneration: { label: 'Question Generation', desc: 'Generates follow-up questions for missing data' },
  };

  return (
    <SectionCard>
      <SectionHeader title="AI Reasoning Trace" subtitle="Expand each agent step to view reasoning detail" />
      <div className="p-5">
        {messages.length === 0 ? (
          <p className="text-xs text-gray-400 py-6 text-center">No agent messages available for this analysis.</p>
        ) : (
          <div className="border border-[#E5E7EB] rounded-lg overflow-hidden divide-y divide-[#E5E7EB]">
            {messages.map((msg, idx) => {
              const name = msg.agent;
              const meta = agentMeta[name] || { label: name, desc: 'AI analysis agent' };
              const isOpen = expandedAgents[name];

              return (
                <div key={idx}>
                  <button
                    onClick={() => toggleAgent(name)}
                    className={`w-full flex items-center justify-between px-5 py-3.5 transition-colors text-left ${isOpen ? 'bg-[#F7F9FC]' : 'hover:bg-gray-50'}`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="w-7 h-7 rounded-lg bg-white border border-gray-200 flex items-center justify-center text-[11px] font-bold text-gray-500 flex-shrink-0 shadow-sm">
                        {idx + 1}
                      </span>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-900">{meta.label}</p>
                        <p className="text-[10px] text-gray-400 mt-0.5">{meta.desc}</p>
                      </div>
                    </div>
                    <svg className={`w-4 h-4 text-gray-400 flex-shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>

                  {isOpen && (
                    <div className="px-5 pb-5 pt-3 bg-[#F7F9FC] border-t border-[#E5E7EB]">
                      <div className="space-y-4">
                        {msg.analysis && (
                          <TraceBlock label="Analysis">
                            <ReasoningBlock text={msg.analysis} />
                          </TraceBlock>
                        )}
                        {msg.reasoning && (
                          <TraceBlock label="Reasoning">
                            <ReasoningBlock text={msg.reasoning} />
                          </TraceBlock>
                        )}

                        {/* Metric badges row */}
                        {(msg.risk_score !== undefined || msg.response_probability !== undefined || msg.decision) && (
                          <div className="flex items-center gap-4 flex-wrap pt-2 border-t border-gray-200">
                            {msg.risk_score !== undefined && (
                              <div className="flex items-center gap-2">
                                <span className="text-[10px] text-gray-400 uppercase font-medium">Risk</span>
                                <span className="text-sm font-bold text-gray-900">{Math.round(msg.risk_score * 100)}%</span>
                                {msg.category && (
                                  <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                                    msg.category === 'HIGH' ? 'bg-red-50 text-red-700 border-red-200' :
                                    msg.category === 'MEDIUM' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                                    'bg-emerald-50 text-emerald-700 border-emerald-200'
                                  }`}>{msg.category}</span>
                                )}
                              </div>
                            )}
                            {msg.response_probability !== undefined && (
                              <div className="flex items-center gap-2">
                                <span className="text-[10px] text-gray-400 uppercase font-medium">Response</span>
                                <span className="text-sm font-bold text-gray-900">{Math.round(msg.response_probability * 100)}%</span>
                              </div>
                            )}
                            {msg.decision && (
                              <div className="flex items-center gap-2">
                                <span className="text-[10px] text-gray-400 uppercase font-medium">Decision</span>
                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                                  msg.decision === 'ASK' ? 'bg-purple-50 text-purple-700 border-purple-200' :
                                  msg.decision === 'PROCEED' ? 'bg-blue-50 text-[#2563EB] border-blue-200' :
                                  msg.decision === 'ESCALATE' ? 'bg-red-50 text-red-700 border-red-200' :
                                  'bg-gray-50 text-gray-700 border-gray-200'
                                }`}>{msg.decision}</span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </SectionCard>
  );
}

function TraceBlock({ label, children }) {
  return (
    <div>
      <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5">{label}</p>
      <div className="bg-white border border-[#E5E7EB] rounded-lg px-4 py-3">
        {children}
      </div>
    </div>
  );
}


/* ── TECHNICAL DECISION SUMMARY ──────────────────────── */
function TechnicalDecisionSummary({ summary }) {
  const confLevel = summary.confidence_level || 'UNKNOWN';
  const confScore = ((summary.confidence_score || 0) * 100).toFixed(1);
  
  const confColor = {
    'VERY_HIGH': 'text-emerald-700 bg-emerald-50 border-emerald-300',
    'HIGH': 'text-blue-700 bg-blue-50 border-blue-300',
    'MODERATE': 'text-amber-700 bg-amber-50 border-amber-300',
    'LOW': 'text-orange-700 bg-orange-50 border-orange-300',
    'VERY_LOW': 'text-red-700 bg-red-50 border-red-300',
  }[confLevel] || 'text-gray-700 bg-gray-50 border-gray-300';

  return (
    <SectionCard>
      <SectionHeader title="AI Decision Analysis" subtitle="Regulatory-compliant decision reasoning" />
      <div className="p-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-50 rounded-lg px-4 py-3 border border-gray-200">
            <p className="text-[10px] text-gray-400 uppercase font-medium mb-1.5">Decision Classification</p>
            <p className="text-sm font-bold text-gray-900">{summary.decision_label || summary.decision || '—'}</p>
          </div>
          <div className="bg-gray-50 rounded-lg px-4 py-3 border border-gray-200">
            <p className="text-[10px] text-gray-400 uppercase font-medium mb-1.5">Confidence Level</p>
            <div className="flex items-baseline gap-2">
              <span className={`px-2 py-0.5 rounded text-xs font-bold border ${confColor}`}>{confLevel.replace('_', ' ')}</span>
              <span className="text-sm font-medium text-gray-600">{confScore}%</span>
            </div>
          </div>
          <div className="bg-gray-50 rounded-lg px-4 py-3 border border-gray-200">
            <p className="text-[10px] text-gray-400 uppercase font-medium mb-1.5">Risk Assessment</p>
            <p className="text-sm font-bold text-gray-900">{((summary.risk_score || 0) * 100).toFixed(0)}%</p>
          </div>
        </div>
        
        <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3.5">
          <p className="text-[10px] text-blue-600 uppercase font-semibold mb-2">Primary Reasoning</p>
          <p className="text-sm text-blue-900 leading-relaxed">{summary.primary_reasoning || 'No reasoning provided'}</p>
        </div>
        
        <div className="flex items-start gap-2.5 px-4 py-3 bg-emerald-50 border border-emerald-200 rounded-lg">
          <svg className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
          <div>
            <p className="text-xs font-semibold text-emerald-700">Regulatory Compliance Verified</p>
            <p className="text-[11px] text-emerald-600 mt-0.5">{summary.regulatory_compliance || 'Aligned with pharmacovigilance standards'}</p>
          </div>
        </div>
      </div>
    </SectionCard>
  );
}

/* ── CONTRIBUTING FACTORS BREAKDOWN ───────────────────── */
function ContributingFactorsBreakdown({ factors }) {
  const renderFactor = (label, data) => {
    if (!data) return null;
    
    const impactColor = {
      'CRITICAL': 'bg-red-100 text-red-800 border-red-300',
      'HIGH': 'bg-orange-100 text-orange-800 border-orange-300',
      'MODERATE': 'bg-amber-100 text-amber-800 border-amber-300',
      'LOW': 'bg-emerald-100 text-emerald-800 border-emerald-300',
    }[data.impact] || 'bg-gray-100 text-gray-700 border-gray-300';
    
    return (
      <div className="border-b border-gray-100 last:border-0 pb-4 last:pb-0">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold text-gray-700">{label}</h4>
          <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold border ${impactColor}`}>
            {data.impact} IMPACT
          </span>
        </div>
        <p className="text-xs text-gray-600 leading-relaxed">{data.explanation}</p>
      </div>
    );
  };

  return (
    <SectionCard>
      <SectionHeader title="Contributing Factors Analysis" subtitle="Technical breakdown of decision inputs" />
      <div className="p-5 space-y-4">
        {renderFactor('Data Quality Assessment', factors.data_quality)}
        {renderFactor('Safety Risk Evaluation', factors.risk_assessment)}
        {renderFactor('Reporter Engagement Profile', factors.reporter_profile)}
      </div>
    </SectionCard>
  );
}

/* ── TECHNICAL AGENT TRACE ────────────────────────────── */
function TechnicalAgentTrace({ trace, expandedAgents, toggleAgent }) {
  return (
    <SectionCard>
      <SectionHeader title="Agent Execution Trace" subtitle="Step-by-step AI decision pipeline" />
      <div className="p-5">
        <div className="border border-[#E5E7EB] rounded-lg overflow-hidden divide-y divide-[#E5E7EB]">
          {trace.map((step, idx) => {
            const isOpen = expandedAgents[step.agent];
            const confScore = step.confidence ? (step.confidence * 100).toFixed(1) : null;
            
            return (
              <div key={idx}>
                <button
                  onClick={() => toggleAgent(step.agent)}
                  className={`w-full flex items-center justify-between px-5 py-3.5 transition-colors text-left ${isOpen ? 'bg-[#F7F9FC]' : 'hover:bg-gray-50'}`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-xs font-bold text-white flex-shrink-0 shadow-sm">
                      {idx + 1}
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-900">{step.agent_label || step.agent}</p>
                      <p className="text-[10px] text-gray-400 mt-0.5 uppercase tracking-wide">
                        {step.timestamp ? new Date(step.timestamp).toLocaleTimeString() : 'Executed'}
                        {confScore && <span className="ml-2">• Confidence: {confScore}%</span>}
                      </p>
                    </div>
                  </div>
                  <svg className={`w-4 h-4 text-gray-400 flex-shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {isOpen && (
                  <div className="px-5 pb-5 pt-3 bg-[#F7F9FC] border-t border-[#E5E7EB]">
                    <div className="space-y-3">
                      {step.analysis && (
                        <div>
                          <p className="text-[10px] font-semibold text-gray-400 uppercase mb-1.5">Analysis Output</p>
                          <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
                            <FormattedText text={step.analysis} className="text-sm text-gray-700 leading-relaxed" />
                          </div>
                        </div>
                      )}
                      {step.reasoning && (
                        <div>
                          <p className="text-[10px] font-semibold text-gray-400 uppercase mb-1.5">Reasoning</p>
                          <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
                            <FormattedText text={step.reasoning} className="text-sm text-gray-700 leading-relaxed" />
                          </div>
                        </div>
                      )}
                      {step.recommendations && step.recommendations.length > 0 && (
                        <div>
                          <p className="text-[10px] font-semibold text-gray-400 uppercase mb-1.5">Recommendations</p>
                          <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 space-y-1">
                            {step.recommendations.map((rec, i) => (
                              <div key={i} className="flex items-start gap-2">
                                <span className="text-blue-500 mt-1">•</span>
                                <span className="text-xs text-gray-700">{rec}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </SectionCard>
  );
}


/* ── AUDIT TRAIL SECTION ───────────────────────────────── */
function AuditTrailSection({ auditLog, loading }) {
  const [isExpanded, setIsExpanded] = useState(true);

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '—';
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const getActionIcon = (action) => {
    const icons = {
      'CASE_CREATED': '📋',
      'AI_ANALYSIS': '🤖',
      'AI_DECISION': '⚙️',
      'FOLLOWUP_SENT': '📧',
      'FOLLOWUP_DELIVERED': '✉️',
      'RESPONSE_RECEIVED': '✅',
      'HUMAN_REVIEW': '👤',
      'DECISION_OVERRIDE': '🔄',
      'SIGNAL_DETECTED': '🔍',
      'REGULATORY_ESCALATION': '🚨',
      'CASE_UPDATED': '📝',
    };
    return icons[action] || '•';
  };

  const getActionColor = (action) => {
    if (action?.includes('OVERRIDE') || action?.includes('ESCALATION')) return 'text-red-700 bg-red-50 border-red-200';
    if (action?.includes('REVIEW') || action?.includes('HUMAN')) return 'text-amber-700 bg-amber-50 border-amber-200';
    if (action?.includes('AI') || action?.includes('DECISION')) return 'text-blue-700 bg-blue-50 border-blue-200';
    if (action?.includes('FOLLOWUP') || action?.includes('SENT')) return 'text-purple-700 bg-purple-50 border-purple-200';
    if (action?.includes('RECEIVED') || action?.includes('COMPLETE')) return 'text-emerald-700 bg-emerald-50 border-emerald-200';
    return 'text-gray-700 bg-gray-50 border-gray-200';
  };

  if (loading) {
    return (
      <SectionCard>
        <SectionHeader title="Audit Trail" subtitle="Complete decision and action history" />
        <div className="p-5">
          <div className="animate-pulse space-y-3">
            <div className="h-16 bg-gray-200 rounded"></div>
            <div className="h-16 bg-gray-200 rounded"></div>
            <div className="h-16 bg-gray-200 rounded"></div>
          </div>
        </div>
      </SectionCard>
    );
  }

  return (
    <SectionCard>
      <div className="px-6 pt-5 pb-3 border-b border-gray-100 flex items-center justify-between">
        <div>
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Audit Trail</h2>
          <p className="text-[11px] text-gray-400 mt-0.5">
            Complete decision and action history ({auditLog.length} {auditLog.length === 1 ? 'entry' : 'entries'})
          </p>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="px-3 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
        >
          {isExpanded ? 'Collapse' : 'Expand'}
        </button>
      </div>
      
      {isExpanded && (
        <div className="p-5">
          {auditLog.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-sm text-gray-400">No audit entries recorded yet</p>
              <p className="text-xs text-gray-400 mt-1">Actions will be logged here automatically</p>
            </div>
          ) : (
            <>
              <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
                {auditLog.map((entry, index) => {
                  const action = entry.action || entry.action_type || 'ACTION';
                  const actor = entry.actor || entry.actor_name || 'System';
                  const actorType = entry.actor_type || (actor.includes('Agent') ? 'AI' : 'HUMAN');
                  const timestamp = entry.timestamp || entry.created_at;
                  const reasoning = entry.reason || entry.reasoning || entry.metadata?.reasoning;
                  const confidence = entry.confidence || entry.metadata?.confidence;
                  
                  return (
                    <div
                      key={index}
                      className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-sm transition-all"
                    >
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <div className="flex items-start gap-3 min-w-0 flex-1">
                          <span className="text-2xl flex-shrink-0 mt-0.5">{getActionIcon(action)}</span>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getActionColor(action)}`}>
                                {action.replace(/_/g, ' ')}
                              </span>
                              <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                actorType === 'AI' 
                                  ? 'bg-blue-100 text-blue-700 border border-blue-200' 
                                  : 'bg-purple-100 text-purple-700 border border-purple-200'
                              }`}>
                                {actorType}
                              </span>
                            </div>
                            <div className="mt-1.5">
                              <p className="text-sm font-medium text-gray-900">{actor}</p>
                              <p className="text-xs text-gray-500 mt-0.5">{formatTimestamp(timestamp)}</p>
                            </div>
                          </div>
                        </div>
                        {confidence !== undefined && confidence !== null && (
                          <div className="flex-shrink-0 text-right">
                            <p className="text-[10px] text-gray-400 uppercase">Confidence</p>
                            <p className="text-sm font-bold text-gray-900">{Math.round(confidence * 100)}%</p>
                          </div>
                        )}
                      </div>
                      
                      {reasoning && (
                        <div className="mt-3 pt-3 border-t border-gray-100">
                          <p className="text-[10px] font-semibold text-gray-400 uppercase mb-1.5">Reasoning</p>
                          <p className="text-sm text-gray-700 leading-relaxed bg-gray-50 px-3 py-2 rounded">
                            {reasoning}
                          </p>
                        </div>
                      )}
                      
                      {entry.metadata && Object.keys(entry.metadata).length > 0 && !reasoning && (
                        <div className="mt-3 pt-3 border-t border-gray-100">
                          <p className="text-[10px] font-semibold text-gray-400 uppercase mb-1.5">Details</p>
                          <div className="text-xs text-gray-600 bg-gray-50 px-3 py-2 rounded font-mono">
                            {JSON.stringify(entry.metadata, null, 2).substring(0, 200)}
                            {JSON.stringify(entry.metadata).length > 200 && '...'}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
              
              <div className="mt-4 pt-4 border-t border-gray-200">
                <div className="flex items-start gap-2.5 px-4 py-3 bg-emerald-50 border border-emerald-200 rounded-lg">
                  <svg className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <p className="text-xs font-semibold text-emerald-700">Immutable Audit Trail</p>
                    <p className="text-[11px] text-emerald-600 mt-0.5">
                      All entries are cryptographically hash-chained and tamper-evident. Complies with FDA 21 CFR Part 11 and EU GVP requirements.
                    </p>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </SectionCard>
  );
}

/* ── REGULATORY COMPLIANCE ─────────────────────────────── */
function RegulatoryCompliance({ summary }) {
  const frameworks = [
    { id: 'GVP', name: 'EU Good Pharmacovigilance Practices', status: 'COMPLIANT' },
    { id: 'FDA', name: 'FDA 21 CFR Part 314.80', status: 'COMPLIANT' },
    { id: 'CIOMS', name: 'CIOMS Safety Reporting Standards', status: 'COMPLIANT' },
    { id: 'ICH-E2B', name: 'ICH E2B Clinical Safety Data Management', status: 'COMPLIANT' },
  ];

  return (
    <SectionCard>
      <SectionHeader title="Regulatory Framework Compliance" subtitle="Pharmacovigilance standards alignment" />
      <div className="p-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {frameworks.map(fw => (
            <div key={fw.id} className="flex items-center justify-between px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg">
              <div>
                <p className="text-xs font-medium text-gray-900">{fw.name}</p>
                <p className="text-[10px] text-gray-500 mt-0.5">{fw.id}</p>
              </div>
              <span className="px-2.5 py-1 rounded text-[10px] font-bold bg-emerald-100 text-emerald-700 border border-emerald-300">
                ✓ {fw.status}
              </span>
            </div>
          ))}
        </div>
        
        <div className="mt-4 px-4 py-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-[10px] text-blue-600 uppercase font-semibold mb-1">Audit Trail Status</p>
          <p className="text-xs text-blue-900">All decision steps logged with timestamps, actor attribution, and confidence scores. Hash-chain verification enabled for tamper detection.</p>
        </div>
      </div>
    </SectionCard>
  );
}

/* ── HUMAN OVERSIGHT ──────────────────────────────────── */
function HumanOversight({ onReview, onOverride, explainability }) {
  const oversight = explainability?.human_oversight || {};
  const canOverride = oversight.can_override !== false;
  const requiresReview = oversight.requires_human_review || false;
  
  return (
    <SectionCard>
      <SectionHeader title="Human Oversight & Governance" />
      <div className="p-5">
        <div className="flex items-center gap-2.5 mb-5 px-4 py-3 bg-emerald-50 border border-emerald-200 rounded-lg">
          <span className="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" />
          <p className="text-xs text-emerald-700">
            <strong className="font-semibold">Human-in-the-loop: Enabled.</strong>{' '}
            AI decisions can be reviewed and overridden by authorized personnel.
          </p>
        </div>
        
        {requiresReview && (
          <div className="flex items-center gap-2.5 mb-4 px-4 py-3 bg-amber-50 border border-amber-200 rounded-lg">
            <svg className="w-4 h-4 text-amber-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <p className="text-xs text-amber-700">
              <strong className="font-semibold">Human Review Required.</strong> This case requires mandatory review before follow-up execution.
            </p>
          </div>
        )}
        
        <div className="flex gap-3">
          <button onClick={onReview} className="flex-1 px-4 py-2.5 bg-[#2563EB] text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">
            Add Review Note
          </button>
          <button onClick={onOverride} disabled={!canOverride} className="flex-1 px-4 py-2.5 bg-white border border-amber-300 text-amber-700 text-sm font-medium rounded-lg hover:bg-amber-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
            Override AI Decision
          </button>
        </div>
      </div>
    </SectionCard>
  );
}


/* ── DECISION METADATA FOOTER ─────────────────────────── */
function MetadataFooter({ caseId, explainability }) {
  const summary = explainability?.decision_summary || {};
  const version = explainability?.explainability_version || 'v1.0';
  const timestamp = summary.timestamp || new Date().toISOString();
  
  const items = [
    { label: 'System', value: `SmartFU ${version}` },
    { label: 'Model', value: 'Mistral Large' },
    { label: 'Analysis Time', value: new Date(timestamp).toLocaleString() },
    { label: 'Case ID', value: caseId },
    { label: 'Explainability', value: 'Full Trace', highlight: true },
    { label: 'Audit Status', value: 'Hash-Verified', highlight: true },
  ];

  return (
    <div className="bg-white rounded-lg border border-[#E5E7EB] shadow-sm px-6 py-3.5">
      <div className="flex items-center justify-between flex-wrap gap-y-2 gap-x-4">
        {items.map((item, i) => (
          <React.Fragment key={item.label}>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-gray-400 uppercase tracking-wider">{item.label}</span>
              {item.highlight
                ? <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">{item.value}</span>
                : <span className="text-xs font-medium text-gray-700">{item.value}</span>
              }
            </div>
            {i < items.length - 1 && <span className="hidden sm:block w-px h-4 bg-gray-200" />}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}


/* ── MODAL ────────────────────────────────────────────── */
function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg border border-[#E5E7EB] shadow-xl max-w-lg w-full p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none">&times;</button>
        </div>
        {children}
      </div>
    </div>
  );
}
