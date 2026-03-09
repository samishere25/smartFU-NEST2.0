import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const API = '';
const token = () => localStorage.getItem('access_token');

/* ── Colour helpers ─────────────────────────────────────────── */
const RISK = { CRITICAL: 'bg-red-50 text-red-700 ring-1 ring-red-600/20', HIGH: 'bg-orange-50 text-orange-700 ring-1 ring-orange-600/20', MEDIUM: 'bg-amber-50 text-amber-700 ring-1 ring-amber-600/20', LOW: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20' };
const STATUS_CLR = { PENDING: 'bg-yellow-100 text-yellow-800', SENT: 'bg-blue-100 text-blue-800', AWAITING_RESPONSE: 'bg-purple-100 text-purple-800', RESPONDED: 'bg-green-100 text-green-800', PARTIAL_RESPONSE: 'bg-teal-100 text-teal-800', EXPIRED: 'bg-gray-200 text-gray-600', FAILED: 'bg-red-100 text-red-800' };
const DECISION_CLR = { APPROVE: 'bg-emerald-600 hover:bg-emerald-700', REQUEST_MORE_INFO: 'bg-amber-500 hover:bg-amber-600', ESCALATE: 'bg-red-600 hover:bg-red-700', CLOSE: 'bg-gray-500 hover:bg-gray-600' };

const pct = (v) => Math.round((v || 0) * 100);

/* ── Ring gauge (reused pattern) ────────────────────────────── */
const Ring = ({ value, size = 56, stroke = 5, color = '#3b82f6', label }) => {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const o = c * (1 - (value || 0));
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#f3f4f6" strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke}
          strokeDasharray={c} strokeDashoffset={o} strokeLinecap="round" />
      </svg>
      {label && <span className="text-[10px] text-gray-500">{label}</span>}
    </div>
  );
};

/* ── Section card wrapper ───────────────────────────────────── */
const Card = ({ title, icon, children, className = '', badge }) => (
  <div className={`bg-white rounded-xl border shadow-sm ${className}`}>
    <div className="px-5 py-3 border-b flex items-center gap-2">
      {icon}
      <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
      {badge && <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium">{badge}</span>}
    </div>
    <div className="px-5 py-4">{children}</div>
  </div>
);

/* ── Key-value row ──────────────────────────────────────────── */
const KV = ({ k, v }) => (
  <div className="flex justify-between py-1.5 border-b border-dashed border-gray-100 last:border-0">
    <span className="text-xs text-gray-500">{k}</span>
    <span className="text-xs font-medium text-gray-800 text-right max-w-[55%] truncate">{v ?? '—'}</span>
  </div>
);

/* ═══════════════════════════════════════════════════════════════
   NOVARTIS REVIEW DASHBOARD PAGE
   ═══════════════════════════════════════════════════════════════ */
const ReviewerDashboard = () => {
  const navigate = useNavigate();

  /* ── Queue state ──────────────────────────────────────────── */
  const [queue, setQueue] = useState([]);
  const [queueLoading, setQueueLoading] = useState(true);
  const [queueError, setQueueError] = useState(null);
  const [queueTotal, setQueueTotal] = useState(0);
  const [queuePage, setQueuePage] = useState(1);
  const [queueTotalPages, setQueueTotalPages] = useState(1);
  const PAGE_SIZE = 50;

  /* ── Search/filter state ──────────────────────────────────── */
  const [searchDrug, setSearchDrug] = useState('');
  const [filterRisk, setFilterRisk] = useState('');

  /* ── Detail state ─────────────────────────────────────────── */
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [selectedCaseId, setSelectedCaseId] = useState(null);

  /* ── Decision state ───────────────────────────────────────── */
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(null);
  const [decisionResult, setDecisionResult] = useState(null);

  /* ── Follow-up state ──────────────────────────────────────── */
  const [sendingFollowup, setSendingFollowup] = useState(false);
  const [followupResult, setFollowupResult] = useState(null);
  const [reviewerQuestions, setReviewerQuestions] = useState('');
  const [overrideSaved, setOverrideSaved] = useState(false);
  const [savingOverride, setSavingOverride] = useState(false);
  const [buildingPackage, setBuildingPackage] = useState(false);
  const [builtPackage, setBuiltPackage] = useState(null); // from build-combined response

  /* ── Fetch review queue (paginated) ────────────────────────── */
  const fetchQueue = useCallback(async (page = 1, drug = '', risk = '') => {
    setQueueLoading(true);
    setQueueError(null);
    try {
      const skip = (page - 1) * PAGE_SIZE;
      const params = new URLSearchParams({ skip, limit: PAGE_SIZE });
      if (drug.trim()) params.append('drug', drug.trim());
      if (risk) params.append('risk_level', risk);
      const res = await fetch(`${API}/api/review/cases?${params}`, {
        headers: { Authorization: `Bearer ${token()}`, 'Content-Type': 'application/json' },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to load queue (${res.status})`);
      }
      const d = await res.json();
      setQueue(d.cases || []);
      setQueueTotal(d.total || 0);
      setQueuePage(d.page || 1);
      setQueueTotalPages(d.total_pages || 1);
    } catch (e) {
      setQueueError(e.message);
    } finally {
      setQueueLoading(false);
    }
  }, []);

  useEffect(() => { fetchQueue(1, '', ''); }, [fetchQueue]);

  const handleSearch = () => { setQueuePage(1); fetchQueue(1, searchDrug, filterRisk); };
  const goPage = (p) => { setQueuePage(p); fetchQueue(p, searchDrug, filterRisk); };

  /* ── Fetch case review ────────────────────────────────────── */
  const fetchReview = useCallback(async (id) => {
    const caseId = id;
    if (!caseId) return;
    setLoading(true);
    setError(null);
    setData(null);
    setDecisionResult(null);
    setFollowupResult(null);
    setReviewerQuestions('');
    setOverrideSaved(false);
    setBuiltPackage(null);
    setSelectedCaseId(caseId);
    try {
      const res = await fetch(`${API}/api/review/${caseId}`, {
        headers: { Authorization: `Bearer ${token()}`, 'Content-Type': 'application/json' },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Case not found (${res.status})`);
      }
      setData(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  /* ── Submit decision ──────────────────────────────────────── */
  const submitDecision = async (decision) => {
    if (!data) return;
    const caseId = data.case_summary?.case_id || selectedCaseId;
    setSubmitting(decision);
    setDecisionResult(null);
    try {
      const res = await fetch(`${API}/api/review/${caseId}/decision`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, reviewer_comment: comment || null }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Decision failed (${res.status})`);
      }
      const result = await res.json();
      setDecisionResult(result);
      fetchReview(caseId);
      fetchQueue(queuePage, searchDrug, filterRisk);
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(null);
    }
  };

  /* ── Step 1: Save override questions (no send) ─────────────── */
  const saveOverride = async () => {
    if (!data) return;
    const caseId = data.case_summary?.case_id || selectedCaseId;
    const questions = reviewerQuestions.split('\n').filter(q => q.trim());
    if (questions.length === 0) { setOverrideSaved(true); return; }
    setSavingOverride(true);
    try {
      const res = await fetch(`${API}/api/review/${caseId}/save-override`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ reviewer_questions: questions }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Save failed (${res.status})`);
      }
      setOverrideSaved(true);
      setBuiltPackage(null); // reset built package since override changed
    } catch (e) {
      setFollowupResult({ success: false, message: e.message });
    } finally {
      setSavingOverride(false);
    }
  };

  /* ── Step 2: Build combined follow-up package (no send) ──── */
  const buildCombined = async () => {
    if (!data) return;
    const caseId = data.case_summary?.case_id || selectedCaseId;
    setBuildingPackage(true);
    setFollowupResult(null);
    try {
      const bodyData = {};
      const pendingQuestions = reviewerQuestions.trim() ? reviewerQuestions.split('\n').filter(q => q.trim()) : [];
      if (pendingQuestions.length > 0) {
        bodyData.reviewer_questions = pendingQuestions;
        // Auto-save pending questions to DB before building
        try {
          await fetch(`${API}/api/review/${caseId}/save-override`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${token()}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ reviewer_questions: pendingQuestions }),
          });
          setOverrideSaved(true);
        } catch (_) { /* non-blocking */ }
      }
      const res = await fetch(`${API}/api/review/${caseId}/build-combined`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(bodyData),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Build failed (${res.status})`);
      }
      const result = await res.json();
      setBuiltPackage(result);
    } catch (e) {
      setFollowupResult({ success: false, message: e.message });
    } finally {
      setBuildingPackage(false);
    }
  };

  /* ── Step 3: Send combined follow-up (only after build) ──── */
  const sendFollowUp = async () => {
    if (!data || !builtPackage) return;
    const caseId = data.case_summary?.case_id || selectedCaseId;
    setSendingFollowup(true);
    setFollowupResult(null);
    try {
      const res = await fetch(`${API}/api/review/${caseId}/send-followup`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Follow-up failed (${res.status})`);
      }
      const result = await res.json();
      setFollowupResult(result);
      setBuiltPackage(null); // consumed
      setTimeout(() => fetchReview(caseId), 1000);
    } catch (e) {
      setFollowupResult({ success: false, message: e.message });
    } finally {
      setSendingFollowup(false);
    }
  };

  const cs = data?.case_summary;
  const ft = data?.followup_timeline;
  const ml = data?.ml_risk;
  const reg = data?.regulatory_seriousness;
  const lc = data?.lifecycle;
  const rv = data?.review_status;
  const cp = data?.combined_package;
  const attachments = data?.attachments || [];
  const reporterResponses = data?.reporter_responses || [];
  const fieldHistory = data?.field_history || [];
  const noResponse = data?.no_response;

  return (
    <div className="max-w-[1440px] mx-auto px-5 py-6">

      {/* ── Header ──────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Novartis Review Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">Medical case review, follow-up management, and decisions</p>
        </div>
        <button onClick={() => navigate('/case-analysis')} className="text-xs text-blue-600 hover:text-blue-800 font-medium">
          Back to Case Repository
        </button>
      </div>

      {/* ── Case Queue ───────────────────────────────────────── */}
      {!data && (
        <div className="bg-white rounded-xl border shadow-sm mb-6">
          <div className="px-5 py-3 border-b flex items-center justify-between">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>
              <h3 className="text-sm font-semibold text-gray-900">Review Queue</h3>
              <span className="text-[10px] text-gray-400 ml-1">{queueTotal.toLocaleString()} total &middot; page {queuePage}/{queueTotalPages}</span>
            </div>
            <button onClick={() => fetchQueue(queuePage, searchDrug, filterRisk)} disabled={queueLoading} className="text-xs text-blue-600 hover:text-blue-800 font-medium disabled:opacity-50">
              {queueLoading ? 'Loading...' : 'Refresh'}
            </button>
          </div>

          {/* Search & Filter Bar */}
          <div className="px-5 py-2.5 border-b bg-gray-50/50 flex items-center gap-3 flex-wrap">
            <input
              type="text"
              value={searchDrug}
              onChange={(e) => setSearchDrug(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search drug name..."
              className="border rounded-lg px-3 py-1.5 text-xs w-48 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
            <select
              value={filterRisk}
              onChange={(e) => { setFilterRisk(e.target.value); fetchQueue(1, searchDrug, e.target.value); }}
              className="border rounded-lg px-2 py-1.5 text-xs focus:ring-2 focus:ring-blue-500 outline-none bg-white"
            >
              <option value="">All Risk Levels</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
            <button onClick={handleSearch} className="px-3 py-1.5 rounded-lg text-xs font-medium text-white bg-blue-600 hover:bg-blue-700">
              Search
            </button>
            {(searchDrug || filterRisk) && (
              <button onClick={() => { setSearchDrug(''); setFilterRisk(''); fetchQueue(1, '', ''); }} className="text-xs text-gray-500 hover:text-gray-700">
                Clear filters
              </button>
            )}
          </div>

          {queueError && (
            <div className="px-5 py-3 bg-red-50 border-b border-red-200">
              <p className="text-sm text-red-700">{queueError}</p>
            </div>
          )}

          {queueLoading && !queue.length ? (
            <div className="p-8 text-center">
              <div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-2" />
              <p className="text-xs text-gray-400">Loading review queue...</p>
            </div>
          ) : queue.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-sm text-gray-400">No cases pending review.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-gray-50 text-left text-[10px] uppercase tracking-wider text-gray-500">
                    <th className="px-4 py-2.5 font-semibold">ID</th>
                    <th className="px-4 py-2.5 font-semibold">Drug</th>
                    <th className="px-4 py-2.5 font-semibold">Reaction</th>
                    <th className="px-4 py-2.5 font-semibold text-center">Serious</th>
                    <th className="px-4 py-2.5 font-semibold text-center">Risk</th>
                    <th className="px-4 py-2.5 font-semibold text-center">ML Score</th>
                    <th className="px-4 py-2.5 font-semibold">Reporter</th>
                    <th className="px-4 py-2.5 font-semibold text-center">Source</th>
                    <th className="px-4 py-2.5 font-semibold">Status</th>
                    <th className="px-4 py-2.5 font-semibold">Received</th>
                    <th className="px-4 py-2.5 font-semibold text-center">Days Left</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {queue.map((c) => (
                    <tr
                      key={c.case_id}
                      onClick={() => fetchReview(c.primaryid || c.case_id)}
                      className="hover:bg-blue-50/60 cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-2.5 font-mono font-medium text-blue-700">{c.primaryid || c.case_id?.slice(0, 8)}</td>
                      <td className="px-4 py-2.5 text-gray-800 max-w-[160px] truncate">{c.suspect_drug || '—'}</td>
                      <td className="px-4 py-2.5 text-gray-800 max-w-[180px] truncate">{c.reaction || '—'}</td>
                      <td className="px-4 py-2.5 text-center">
                        {c.is_serious
                          ? <span className="inline-block w-2 h-2 rounded-full bg-red-500" title="Serious" />
                          : <span className="inline-block w-2 h-2 rounded-full bg-gray-300" title="Non-serious" />
                        }
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${RISK[c.risk_level?.toUpperCase()] || 'bg-gray-100 text-gray-600'}`}>
                          {c.risk_level || '—'}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-center tabular-nums">{c.ml_risk_score != null ? (c.ml_risk_score * 100).toFixed(0) + '%' : '—'}</td>
                      <td className="px-4 py-2.5 text-gray-600">{c.reporter_type || '—'}</td>
                      <td className="px-4 py-2.5 text-center">
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                          c.intake_source === 'PDF' ? 'bg-indigo-50 text-indigo-700 ring-1 ring-indigo-600/20' : 'bg-gray-100 text-gray-600'
                        }`}>
                          {c.intake_source || 'CSV'}
                        </span>
                      </td>
                      <td className="px-4 py-2.5">
                        <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-gray-100 text-gray-700">
                          {c.case_status?.replace(/_/g, ' ') || '—'}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-gray-500">{c.date_received ? new Date(c.date_received).toLocaleDateString() : '—'}</td>
                      <td className="px-4 py-2.5 text-center tabular-nums">{c.days_remaining ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination Controls */}
              <div className="px-5 py-3 border-t bg-gray-50/50 flex items-center justify-between">
                <span className="text-xs text-gray-500">
                  Showing {(queuePage - 1) * PAGE_SIZE + 1}–{Math.min(queuePage * PAGE_SIZE, queueTotal)} of {queueTotal.toLocaleString()}
                </span>
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => goPage(1)}
                    disabled={queuePage <= 1 || queueLoading}
                    className="px-2 py-1 rounded text-xs border disabled:opacity-30 hover:bg-gray-100"
                  >«</button>
                  <button
                    onClick={() => goPage(queuePage - 1)}
                    disabled={queuePage <= 1 || queueLoading}
                    className="px-2.5 py-1 rounded text-xs border disabled:opacity-30 hover:bg-gray-100"
                  >Prev</button>
                  <span className="px-3 py-1 text-xs font-medium text-blue-700 bg-blue-50 rounded">{queuePage}</span>
                  <button
                    onClick={() => goPage(queuePage + 1)}
                    disabled={queuePage >= queueTotalPages || queueLoading}
                    className="px-2.5 py-1 rounded text-xs border disabled:opacity-30 hover:bg-gray-100"
                  >Next</button>
                  <button
                    onClick={() => goPage(queueTotalPages)}
                    disabled={queuePage >= queueTotalPages || queueLoading}
                    className="px-2 py-1 rounded text-xs border disabled:opacity-30 hover:bg-gray-100"
                  >»</button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Back to queue button (when viewing a case) ───────── */}
      {data && (
        <div className="mb-4">
          <button onClick={() => { setData(null); setError(null); setSelectedCaseId(null); setDecisionResult(null); setFollowupResult(null); setComment(''); setReviewerQuestions(''); setOverrideSaved(false); setBuiltPackage(null); }} className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
            Back to Review Queue
          </button>
        </div>
      )}

      {/* ── Error ───────────────────────────────────────────── */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 mb-6">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* ── Loading case detail ──────────────────────────────── */}
      {loading && (
        <div className="bg-white rounded-xl border shadow-sm p-12 text-center">
          <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-3" />
          <p className="text-sm text-gray-500">Loading case review data...</p>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════
         CASE DATA LOADED
         ═══════════════════════════════════════════════════════ */}
      {data && !loading && (
        <div className="space-y-5">

          {/* ── Top status bar ──────────────────────────────── */}
          <div className="bg-white rounded-xl border shadow-sm px-5 py-3 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div>
                <span className="text-[10px] uppercase tracking-wider text-gray-400">Case</span>
                <p className="text-sm font-semibold text-gray-900">{cs?.primaryid || cs?.case_id?.slice(0, 8)}</p>
              </div>
              <div className="w-px h-8 bg-gray-200" />
              <div>
                <span className="text-[10px] uppercase tracking-wider text-gray-400">Status</span>
                <p className="text-sm font-medium text-gray-800">{cs?.status?.case_status || '—'}</p>
              </div>
              <div className="w-px h-8 bg-gray-200" />
              <div>
                <span className="text-[10px] uppercase tracking-wider text-gray-400">Follow-Up</span>
                <p className="text-sm font-medium">
                  {ft?.total_attempts > 0
                    ? <span className="text-blue-600">{ft.total_attempts} attempt{ft.total_attempts !== 1 ? 's' : ''} ({ft.responded} responded)</span>
                    : <span className="text-gray-400">No follow-ups sent</span>
                  }
                </p>
              </div>
              <div className="w-px h-8 bg-gray-200" />
              <div>
                <span className="text-[10px] uppercase tracking-wider text-gray-400">Reviewed</span>
                <p className="text-sm font-medium">
                  {rv?.human_reviewed
                    ? <span className="text-emerald-600">Yes — {rv.reviewed_by}</span>
                    : <span className="text-amber-600">Not yet</span>
                  }
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {cs?.assessment?.is_serious && (
                <span className="inline-flex px-2.5 py-1 rounded-full text-[10px] font-bold uppercase bg-red-50 text-red-700 ring-1 ring-red-600/20">
                  Serious
                </span>
              )}
              <span className={`inline-flex px-2.5 py-1 rounded-full text-[10px] font-bold uppercase ${RISK[cs?.assessment?.risk_level?.toUpperCase()] || 'bg-gray-100 text-gray-600'}`}>
                {cs?.assessment?.risk_level || 'Unknown'} Risk
              </span>
            </div>
          </div>

          {/* ── Three-column layout ─────────────────────────── */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

            {/* LEFT: Case details (2 cols) */}
            <div className="lg:col-span-2 space-y-5">

              {/* Patient + Drug + Event */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card title="Patient" icon={<svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>}>
                  <KV k="Age" v={cs?.patient?.age} />
                  <KV k="Sex" v={cs?.patient?.sex} />
                  <KV k="Initials" v={cs?.patient?.initials} />
                  <KV k="Medical History" v={cs?.patient?.medical_history} />
                </Card>

                <Card title="Drug" icon={<svg className="w-4 h-4 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" /></svg>}>
                  <KV k="Suspect Drug" v={cs?.drug?.suspect_drug} />
                  <KV k="Dose" v={cs?.drug?.dose} />
                  <KV k="Route" v={cs?.drug?.route} />
                  <KV k="Indication" v={cs?.drug?.indication} />
                  <KV k="Concomitant" v={cs?.drug?.concomitant_drugs} />
                </Card>

                <Card title="Event" icon={<svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" /></svg>}>
                  <KV k="Adverse Event" v={cs?.event?.adverse_event} />
                  <KV k="Event Date" v={cs?.event?.event_date} />
                  <KV k="Outcome" v={cs?.event?.event_outcome} />
                  <KV k="Reporter" v={cs?.reporter?.reporter_type} />
                  <KV k="Country" v={cs?.reporter?.country} />
                </Card>
              </div>

              {/* Clinical Narrative */}
              <Card title="Clinical Narrative" icon={<svg className="w-4 h-4 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>}>
                <p className="text-sm text-gray-700 leading-relaxed italic">
                  {data.clinical_narrative || 'No narrative generated.'}
                </p>
              </Card>

              {/* ── FOLLOW-UP TIMELINE (full detail) ───────── */}
              <Card
                title={`Follow-Up Timeline (${ft?.total_attempts || 0} attempts)`}
                badge={ft?.still_missing_fields?.length > 0 ? `${ft.still_missing_fields.length} still missing` : null}
                icon={<svg className="w-4 h-4 text-teal-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
              >
                {ft?.total_attempts === 0 ? (
                  <p className="text-sm text-gray-400 text-center py-2">No follow-up attempts yet. Use "Send Follow-Up" to trigger.</p>
                ) : (
                  <>
                    <div className="flex flex-wrap gap-2 mb-4">
                      <span className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-800">Sent: {ft?.total_attempts || 0}</span>
                      <span className="text-xs px-2 py-1 rounded-full bg-yellow-100 text-yellow-800">Pending: {ft?.pending || 0}</span>
                      <span className="text-xs px-2 py-1 rounded-full bg-green-100 text-green-800">Responded: {ft?.responded || 0}</span>
                      <span className="text-xs px-2 py-1 rounded-full bg-gray-200 text-gray-600">Expired: {ft?.expired || 0}</span>
                      {ft?.failed > 0 && <span className="text-xs px-2 py-1 rounded-full bg-red-100 text-red-800">Failed: {ft.failed}</span>}
                      <span className="text-xs px-2 py-1 rounded-full bg-emerald-100 text-emerald-800">Answered: {ft?.total_questions_answered || 0}/{ft?.total_questions_sent || 0}</span>
                    </div>
                    {ft?.still_missing_fields?.length > 0 && (
                      <div className="mb-4 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                        <p className="text-[10px] uppercase tracking-wider text-amber-700 font-semibold mb-1">Still Missing</p>
                        <div className="flex flex-wrap gap-1">
                          {ft.still_missing_fields.map(f => (
                            <span key={f} className="text-[10px] px-2 py-0.5 rounded-full bg-amber-200 text-amber-800 font-medium">{f}</span>
                          ))}
                        </div>
                      </div>
                    )}
                    <div className="space-y-3">
                      {ft?.timeline?.map((t, i) => (
                        <div key={t.attempt_id || i} className="border rounded-lg overflow-hidden">
                          <div className="flex items-center justify-between px-3 py-2 bg-gray-50">
                            <div className="flex items-center gap-3">
                              <span className="text-xs font-mono text-gray-400">#{t.iteration_number || i + 1}</span>
                              <span className="text-xs font-medium text-gray-700">{t.channel}</span>
                              <span className="text-[10px] text-gray-400">{t.questions_count} questions</span>
                              {t.sent_to && <span className="text-[10px] text-gray-400">→ {t.sent_to}</span>}
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${STATUS_CLR[t.status] || 'bg-gray-100 text-gray-600'}`}>
                                {t.status}
                              </span>
                              <span className="text-[10px] text-gray-400">
                                {t.sent_at ? new Date(t.sent_at).toLocaleString() : ''}
                              </span>
                            </div>
                          </div>
                          {t.questions?.length > 0 && (
                            <div className="px-3 py-2 border-t">
                              <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">Questions Sent</p>
                              {t.questions.map((q, qi) => (
                                <div key={qi} className="text-xs text-gray-700 py-0.5 flex items-start gap-1">
                                  <span className="text-gray-400 shrink-0">{qi + 1}.</span>
                                  <span>{q.question_text || q.question || `[${q.field || q.field_name}]`}</span>
                                </div>
                              ))}
                            </div>
                          )}
                          {t.responses?.length > 0 && (
                            <div className="px-3 py-2 border-t bg-green-50/30">
                              <p className="text-[10px] uppercase tracking-wider text-emerald-600 font-semibold mb-1">Responses Received ({t.responses.length})</p>
                              {t.responses.map((r, ri) => (
                                <div key={ri} className="text-xs py-1 border-b border-emerald-100 last:border-0">
                                  <div className="flex items-center gap-2 mb-0.5">
                                    <span className="text-emerald-500 font-medium shrink-0">{r.field_name}</span>
                                    {r.channel && (
                                      <span className={`text-[9px] px-1 py-0.5 rounded font-medium ${
                                        r.channel === 'EMAIL' ? 'bg-blue-100 text-blue-600' :
                                        r.channel === 'PHONE' ? 'bg-purple-100 text-purple-600' :
                                        r.channel === 'WHATSAPP' ? 'bg-green-100 text-green-600' :
                                        'bg-gray-100 text-gray-500'
                                      }`}>{r.channel}</span>
                                    )}
                                    {r.processed === false && <span className="text-[9px] px-1 py-0.5 rounded bg-amber-100 text-amber-600 font-medium">Skipped</span>}
                                    <span className="text-[10px] text-gray-400 ml-auto">{r.responded_at ? new Date(r.responded_at).toLocaleString() : ''}</span>
                                  </div>
                                  {r.question_text && <div className="text-[10px] text-gray-400 mb-0.5">Q: {r.question_text}</div>}
                                  <div className="flex items-center gap-1">
                                    <span className="text-gray-800 font-medium">{r.response_text || r.field_value || '—'}</span>
                                    {r.previous_value && r.previous_value !== r.field_value && (
                                      <span className="text-[10px] text-gray-400 ml-1">(was: <span className="line-through">{r.previous_value}</span>)</span>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </Card>

              {/* ── REPORTER RESPONSES PANEL ────────────────── */}
              {reporterResponses.length > 0 && (
                <Card
                  title={`Reporter Responses (${reporterResponses.length})`}
                  badge={`${reporterResponses.filter(r => r.processed).length} applied`}
                  icon={<svg className="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" /></svg>}
                >
                  <div className="space-y-2">
                    {reporterResponses.map((r, i) => (
                      <div key={r.response_id || i} className={`border rounded-lg overflow-hidden ${r.processed ? 'border-emerald-200' : 'border-amber-200'}`}>
                        <div className="flex items-center justify-between px-3 py-1.5 bg-gray-50 border-b">
                          <div className="flex items-center gap-2">
                            <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                              r.channel === 'EMAIL' ? 'bg-blue-100 text-blue-700' :
                              r.channel === 'PHONE' ? 'bg-purple-100 text-purple-700' :
                              r.channel === 'WHATSAPP' ? 'bg-green-100 text-green-700' :
                              'bg-gray-100 text-gray-600'
                            }`}>{r.channel || 'N/A'}</span>
                            <span className="text-[10px] text-gray-500 font-medium">{r.field_name}</span>
                            {r.attempt_number && <span className="text-[10px] text-gray-400">Round #{r.attempt_number}</span>}
                          </div>
                          <div className="flex items-center gap-1.5">
                            {r.processed ? (
                              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-medium">Applied</span>
                            ) : (
                              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 font-medium">Skipped</span>
                            )}
                            <span className="text-[10px] text-gray-400">{r.responded_at ? new Date(r.responded_at).toLocaleString() : ''}</span>
                          </div>
                        </div>
                        <div className="px-3 py-2 space-y-1">
                          {r.question_text && (
                            <div className="text-xs">
                              <span className="text-gray-400 font-medium">Q: </span>
                              <span className="text-gray-600">{r.question_text}</span>
                            </div>
                          )}
                          <div className="text-xs">
                            <span className="text-emerald-600 font-medium">A: </span>
                            <span className="text-gray-800 font-medium">{r.response_text || r.field_value || '—'}</span>
                          </div>
                          {r.previous_value && r.previous_value !== r.field_value && (
                            <div className="text-[10px] text-gray-400 flex items-center gap-1">
                              <span>Previous:</span>
                              <span className="line-through">{r.previous_value}</span>
                              <span>→</span>
                              <span className="text-emerald-600 font-medium">{r.field_value}</span>
                            </div>
                          )}
                          {r.needs_clarification && (
                            <div className="text-[10px] text-amber-600 font-medium">⚠ Needs clarification</div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {/* ── UPDATED CASE FIELDS (version history) ───── */}
              {fieldHistory.length > 0 && (
                <Card
                  title={`Updated Case Fields (${fieldHistory.length})`}
                  icon={<svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>}
                >
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-left text-[10px] uppercase tracking-wider text-gray-500 border-b">
                          <th className="pb-2 pr-2">Field</th>
                          <th className="pb-2 pr-2">Old Value</th>
                          <th className="pb-2 pr-2">New Value</th>
                          <th className="pb-2 pr-2">Source</th>
                          <th className="pb-2">Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        {fieldHistory.map((h, i) => (
                          <tr key={i} className="border-b border-gray-50 last:border-0">
                            <td className="py-1.5 pr-2 font-medium text-gray-700">{h.field_name}</td>
                            <td className="py-1.5 pr-2 text-gray-400">{h.old_value || <span className="italic">empty</span>}</td>
                            <td className="py-1.5 pr-2 text-emerald-700 font-medium">{h.new_value || '—'}</td>
                            <td className="py-1.5 pr-2">
                              <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                                h.source === 'EMAIL' ? 'bg-blue-50 text-blue-600' :
                                h.source === 'PHONE' ? 'bg-purple-50 text-purple-600' :
                                h.source === 'WHATSAPP' ? 'bg-green-50 text-green-600' :
                                'bg-gray-50 text-gray-500'
                              }`}>{h.source || 'N/A'}</span>
                            </td>
                            <td className="py-1.5 text-gray-400 text-[10px]">{h.changed_at ? new Date(h.changed_at).toLocaleString() : ''}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}

              {/* ── NO RESPONSE TRACKING ────────────────────── */}
              {noResponse && noResponse.pending_count > 0 && (
                <Card
                  title="No Response Tracking"
                  badge={`${noResponse.days_since_last_attempt ?? '?'} days`}
                  icon={<svg className="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
                >
                  <div className="space-y-3">
                    <div className="flex items-center gap-4">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-amber-600">{noResponse.pending_count}</div>
                        <div className="text-[10px] text-gray-500">Pending</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-gray-400">{noResponse.days_since_last_attempt ?? '—'}</div>
                        <div className="text-[10px] text-gray-500">Days Since</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-red-500">{noResponse.still_missing_fields?.length || 0}</div>
                        <div className="text-[10px] text-gray-500">Missing Fields</div>
                      </div>
                    </div>
                    {noResponse.last_attempt_date && (
                      <p className="text-[10px] text-gray-400">
                        Last attempt: {new Date(noResponse.last_attempt_date).toLocaleString()}
                      </p>
                    )}
                    {noResponse.still_missing_fields?.length > 0 && (
                      <div>
                        <p className="text-[10px] uppercase tracking-wider text-amber-700 font-semibold mb-1">Awaiting Response</p>
                        <div className="flex flex-wrap gap-1">
                          {noResponse.still_missing_fields.map(f => (
                            <span key={f} className="text-[10px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 font-medium">{f}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </Card>
              )}

              {/* Uploaded Documents */}
              {attachments.length > 0 && (
                <Card title={`Uploaded Documents (${attachments.length})`} icon={<svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>}>
                  <div className="space-y-1.5">
                    {attachments.map((a, i) => (
                      <div key={i} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2">
                        <div className="flex items-center gap-2">
                          <svg className="w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                          <span className="text-xs text-gray-700">{a.file_name}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700">{a.document_type}</span>
                          <span className="text-[10px] text-gray-400">{a.uploaded_by}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {/* Review Notes History */}
              {rv?.review_notes && (
                <Card title="Review Notes History" icon={<svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" /></svg>}>
                  <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono bg-gray-50 rounded-lg p-3">
                    {rv.review_notes}
                  </pre>
                </Card>
              )}
            </div>

            {/* RIGHT: Assessment + Actions (1 col) */}
            <div className="space-y-5">

              {/* Risk Gauges */}
              <Card title="Risk Assessment" icon={<svg className="w-4 h-4 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>}>
                <div className="flex items-center justify-around mb-3">
                  <Ring value={ml?.seriousness_score} color={ml?.seriousness_score >= 0.7 ? '#dc2626' : ml?.seriousness_score >= 0.4 ? '#d97706' : '#059669'} label={`${pct(ml?.seriousness_score)}% ML`} />
                  <Ring value={cs?.assessment?.data_completeness_score} color="#3b82f6" label={`${pct(cs?.assessment?.data_completeness_score)}% Complete`} />
                </div>
                <KV k="ML Risk Level" v={ml?.risk_level} />
                <KV k="Priority Score" v={ml?.priority_score?.toFixed?.(2)} />
                <p className="text-[10px] text-gray-400 mt-2 italic">{ml?.note}</p>
              </Card>

              {/* Regulatory Seriousness */}
              <Card title="Regulatory Seriousness" icon={<svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>}>
                {reg ? (
                  <>
                    <div className="flex items-center gap-2 mb-3">
                      <span className={`inline-flex px-2.5 py-1 rounded-full text-[10px] font-bold uppercase ${reg.is_serious ? 'bg-red-50 text-red-700 ring-1 ring-red-600/20' : 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20'}`}>
                        {reg.is_serious ? 'SERIOUS' : 'NON-SERIOUS'}
                      </span>
                      <span className="text-[10px] text-gray-400">{reg.seriousness_source}</span>
                    </div>
                    {reg.seriousness_criteria?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mb-2">
                        {reg.seriousness_criteria.map((c, i) => (
                          <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-red-50 text-red-600 font-medium">
                            {c.replace(/_/g, ' ')}
                          </span>
                        ))}
                      </div>
                    )}
                    <p className="text-xs text-gray-600">{reg.detail}</p>
                  </>
                ) : (
                  <p className="text-xs text-gray-400">Not evaluated</p>
                )}
              </Card>

              {/* Lifecycle */}
              {lc && (
                <Card title="Lifecycle" icon={<svg className="w-4 h-4 text-cyan-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>}>
                  <KV k="State" v={lc.state || lc.lifecycle_status} />
                  <KV k="Attempts Used" v={`${lc.followups_sent || lc.attempt_count || 0} / ${lc.max_attempts || '—'}`} />
                  <KV k="Deadline" v={lc.deadline} />
                  <KV k="Days Remaining" v={lc.days_remaining} />
                  <KV k="Completeness" v={lc.completeness_score != null ? `${pct(lc.completeness_score)}%` : '—'} />
                </Card>
              )}

              {/* Intake Info */}
              <Card title="Intake" icon={<svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>}>
                <KV k="Source" v={cs?.intake?.intake_source} />
                <KV k="File" v={cs?.intake?.source_filename} />
                <KV k="Created" v={cs?.intake?.created_at ? new Date(cs.intake.created_at).toLocaleString() : '—'} />
              </Card>



            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReviewerDashboard;
