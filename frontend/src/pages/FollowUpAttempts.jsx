import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCaseEventListener } from '../context/CaseEventContext';

const PAGE_SIZE = 15;

/* ── helpers ───────────────────────────────────────────────── */
const pct = (v) => Math.round((v || 0) * 100);

const statusMeta = (s) => {
  if (s === 'COMPLETE' || s === 'RESPONDED') return { label: 'Complete',  cls: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20' };
  if (s === 'PENDING' || s === 'AWAITING_RESPONSE') return { label: 'Pending', cls: 'bg-amber-50 text-amber-700 ring-1 ring-amber-600/20' };
  if (s === 'FAILED')  return { label: 'Failed',   cls: 'bg-red-50 text-red-700 ring-1 ring-red-600/20' };
  return                       { label: s || 'Unknown', cls: 'bg-gray-100 text-gray-600' };
};

const channelMeta = (ch) => {
  if (ch === 'PHONE')    return { label: 'Phone',    cls: 'bg-blue-50 text-blue-700 ring-1 ring-blue-600/20' };
  if (ch === 'WHATSAPP') return { label: 'WhatsApp', cls: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20' };
  return                        { label: 'Email',    cls: 'bg-gray-100 text-gray-600' };
};

const riskCls = (v) => {
  if (v >= 70) return 'bg-red-50 text-red-700 ring-1 ring-red-600/20';
  if (v >= 40) return 'bg-amber-50 text-amber-700 ring-1 ring-amber-600/20';
  return 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20';
};

const compColor = (v) => {
  if (v >= 80) return 'bg-emerald-500';
  if (v >= 60) return 'bg-blue-500';
  if (v >= 40) return 'bg-amber-400';
  return 'bg-red-400';
};

const isPending  = (a) => a.status === 'PENDING' || a.status === 'AWAITING_RESPONSE';
const isComplete = (a) => a.status === 'COMPLETE' || a.response_status === 'RESPONDED';

const FollowUpAttempts = () => {
  const navigate = useNavigate();
  const [attempts, setAttempts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterStatus, setFilterStatus] = useState('ALL'); // ALL, PENDING, COMPLETE

  /* new client-side state */
  const [searchTerm, setSearchTerm] = useState('');
  const [channelFilter, setChannelFilter] = useState('ALL');
  const [riskFilter, setRiskFilter] = useState('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const [expandedRow, setExpandedRow] = useState(null);

  useEffect(() => {
    fetchAttempts();
  }, []);

  // Auto-refresh when cases are updated
  useCaseEventListener((event) => {
    console.log('📬 FollowUpAttempts: Refreshing due to case event:', event.type);
    fetchAttempts();
  });

  const fetchAttempts = async () => {
    try {
      setLoading(true);
      setError(null);

      const token = localStorage.getItem('access_token');
      const baseUrl = '';

      // Fetch real follow-up attempts from database
      const response = await fetch(`${baseUrl}/api/followups/attempts/all?limit=100`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch follow-up attempts');
      }

      const data = await response.json();
      setAttempts(data.attempts || []);
    } catch (err) {
      setError(err.message || 'Failed to load follow-up attempts');
    } finally {
      setLoading(false);
    }
  };

  /* ── derived data ───────────────────────────────────────── */
  const metrics = useMemo(() => {
    const pending   = attempts.filter(isPending).length;
    const completed = attempts.filter(isComplete).length;
    const escalated = attempts.filter(a => pct(a.seriousness_score) >= 70).length;
    const avgComp   = attempts.length
      ? Math.round(attempts.reduce((s, a) => s + pct(a.completeness_score), 0) / attempts.length)
      : 0;
    return { pending, completed, escalated, avgComp };
  }, [attempts]);

  const filteredAttempts = useMemo(() => {
    let list = [...attempts];

    // status
    if (filterStatus === 'PENDING')  list = list.filter(isPending);
    if (filterStatus === 'COMPLETE') list = list.filter(isComplete);

    // search
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      list = list.filter(a =>
        String(a.primaryid || a.case_id || '').toLowerCase().includes(q) ||
        (a.drug_name || '').toLowerCase().includes(q) ||
        (a.adverse_event || '').toLowerCase().includes(q)
      );
    }

    // channel
    if (channelFilter !== 'ALL') list = list.filter(a => a.channel === channelFilter);

    // risk
    if (riskFilter === 'HIGH')   list = list.filter(a => pct(a.seriousness_score) >= 70);
    if (riskFilter === 'MEDIUM') list = list.filter(a => pct(a.seriousness_score) >= 40 && pct(a.seriousness_score) < 70);
    if (riskFilter === 'LOW')    list = list.filter(a => pct(a.seriousness_score) < 40);

    return list;
  }, [attempts, filterStatus, searchTerm, channelFilter, riskFilter]);

  const totalPages = Math.max(1, Math.ceil(filteredAttempts.length / PAGE_SIZE));
  const paginatedAttempts = filteredAttempts.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);
  const rangeStart = filteredAttempts.length ? (currentPage - 1) * PAGE_SIZE + 1 : 0;
  const rangeEnd = Math.min(currentPage * PAGE_SIZE, filteredAttempts.length);

  // reset page on filter change
  useEffect(() => { setCurrentPage(1); }, [filterStatus, searchTerm, channelFilter, riskFilter]);

  /* ── loading ────────────────────────────────────────────── */
  if (loading) {
    return (
      <div className="min-h-screen bg-[#f7f9fc] flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="animate-spin rounded-full h-10 w-10 border-2 border-blue-600 border-t-transparent mx-auto" />
          <p className="text-sm text-gray-500">Loading follow-up attempts…</p>
        </div>
      </div>
    );
  }

  /* ── error ──────────────────────────────────────────────── */
  if (error) {
    return (
      <div className="min-h-screen bg-[#f7f9fc] flex items-center justify-center">
        <div className="max-w-sm w-full bg-white rounded-xl shadow-sm border p-8 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center mx-auto">
            <svg className="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          </div>
          <p className="text-sm font-medium text-gray-900">{error}</p>
          <button onClick={fetchAttempts} className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium">Retry</button>
        </div>
      </div>
    );
  }

  /* ── main render ────────────────────────────────────────── */
  return (
    <div className="min-h-screen bg-[#f8f9fb]">
      <div className="max-w-[1400px] mx-auto px-6 pt-6 pb-8 space-y-5">

        {/* ═══ PAGE HEADER ═══ */}
        <div className="flex items-center justify-between mt-0">
          <div>
            <h1 className="text-lg font-semibold text-[#111827]">Follow-Up Tracker</h1>
            <p className="text-[13px] text-[#6B7280] mt-0.5">{attempts.length} total attempts · {filteredAttempts.length} shown</p>
          </div>
          <button onClick={fetchAttempts} className="flex items-center gap-1.5 px-3.5 py-[7px] border border-[#E5E7EB] rounded-md text-[13px] font-medium text-[#374151] bg-white hover:bg-[#F9FAFB] transition-colors">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
            Refresh
          </button>
        </div>

        {/* ═══ METRICS CARDS ═══ */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard label="Pending Attempts" value={metrics.pending} icon={
            <svg className="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          } color="text-amber-600" />
          <MetricCard label="Completed" value={metrics.completed} icon={
            <svg className="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          } color="text-emerald-600" />
          <MetricCard label="Escalated Cases" value={metrics.escalated} icon={
            <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>
          } color="text-red-600" />
          <MetricCard label="Avg. Completeness" value={`${metrics.avgComp}%`} icon={
            <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
          } color="text-blue-600" />
        </div>

        {/* ═══ FILTERS BAR ═══ */}
        <div className="bg-white rounded-xl shadow-sm border border-[#e5e7eb] p-4">
          <div className="flex flex-wrap items-center gap-3">
            {/* Search */}
            <div className="relative flex-1 min-w-[220px]">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
              <input type="text" placeholder="Search by Case ID, drug, or event…"
                value={searchTerm} onChange={e => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500" />
            </div>

            <div className="h-8 w-px bg-gray-200 hidden sm:block" />

            {/* Status */}
            <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
              className="border rounded-lg px-3 py-2 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/30">
              <option value="ALL">All Statuses</option>
              <option value="PENDING">Pending</option>
              <option value="COMPLETE">Complete</option>
            </select>

            {/* Channel */}
            <select value={channelFilter} onChange={e => setChannelFilter(e.target.value)}
              className="border rounded-lg px-3 py-2 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/30">
              <option value="ALL">All Channels</option>
              <option value="EMAIL">Email</option>
              <option value="PHONE">Phone</option>
              <option value="WHATSAPP">WhatsApp</option>
            </select>

            {/* Risk */}
            <select value={riskFilter} onChange={e => setRiskFilter(e.target.value)}
              className="border rounded-lg px-3 py-2 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/30">
              <option value="ALL">All Risk Levels</option>
              <option value="HIGH">High Risk (≥70%)</option>
              <option value="MEDIUM">Medium (40–70%)</option>
              <option value="LOW">Low (&lt;40%)</option>
            </select>
          </div>
        </div>

        {/* ═══ TABLE ═══ */}
        <div className="bg-white rounded-xl shadow-sm border border-[#e5e7eb] overflow-hidden">
          {filteredAttempts.length === 0 ? (
            <div className="py-16 text-center">
              <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"/></svg>
              <p className="text-gray-500 font-medium">No follow-up attempts found</p>
              <p className="text-gray-400 text-sm mt-1">{filterStatus !== 'ALL' ? 'Try changing the filter' : 'Follow-ups will appear here when cases are analyzed'}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b text-left">
                    <th className="pl-5 pr-3 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wider w-8" />
                    <th className="px-3 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wider w-[100px]">Case ID</th>
                    <th className="px-3 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wider">Drug & Event</th>
                    <th className="px-3 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wider w-[90px]">Risk</th>
                    <th className="px-3 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wider w-[100px]">Channel</th>
                    <th className="px-3 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wider w-[100px]">Status</th>
                    <th className="px-3 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wider w-[160px]">Completeness</th>
                    <th className="px-3 pr-5 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wider text-right w-[200px]">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {paginatedAttempts.map((attempt) => {
                    const risk = pct(attempt.seriousness_score);
                    const comp = pct(attempt.completeness_score);
                    const st = statusMeta(attempt.status);
                    const ch = channelMeta(attempt.channel);
                    const isExpanded = expandedRow === attempt.attempt_id;
                    const hasTimeline = attempt.timeline && attempt.timeline.length > 0;

                    return (
                      <React.Fragment key={attempt.attempt_id}>
                        <tr className={`hover:bg-gray-50/70 transition-colors group ${isExpanded ? 'bg-blue-50/30' : ''}`}>
                          {/* Expand toggle */}
                          <td className="pl-5 pr-1 py-3.5">
                            {hasTimeline ? (
                              <button onClick={() => setExpandedRow(isExpanded ? null : attempt.attempt_id)}
                                className="w-6 h-6 rounded flex items-center justify-center text-gray-400 hover:text-gray-700 hover:bg-gray-100">
                                <svg className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7"/></svg>
                              </button>
                            ) : <span className="w-6" />}
                          </td>
                          {/* Case ID */}
                          <td className="px-3 py-3.5">
                            <span className="font-mono text-xs font-semibold text-gray-900">{attempt.primaryid || attempt.case_id}</span>
                          </td>
                          {/* Drug & Event */}
                          <td className="px-3 py-3.5 max-w-[240px]">
                            <p className="text-gray-900 font-medium truncate" title={attempt.drug_name}>{attempt.drug_name || 'N/A'}</p>
                            <p className="text-gray-500 text-xs truncate mt-0.5" title={attempt.adverse_event}>{attempt.adverse_event || 'N/A'}</p>
                          </td>
                          {/* Risk */}
                          <td className="px-3 py-3.5">
                            <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-semibold ${riskCls(risk)}`}>{risk}%</span>
                          </td>
                          {/* Channel */}
                          <td className="px-3 py-3.5">
                            <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-medium ${ch.cls}`}>{ch.label}</span>
                          </td>
                          {/* Status */}
                          <td className="px-3 py-3.5">
                            <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-medium ${st.cls}`}>{st.label}</span>
                          </td>
                          {/* Completeness */}
                          <td className="px-3 py-3.5">
                            <div className="flex items-center gap-2">
                              <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                                <div className={`h-full rounded-full ${compColor(comp)} transition-all`} style={{ width: `${comp}%` }} />
                              </div>
                              <span className="text-xs font-semibold text-gray-700 tabular-nums w-9 text-right">{comp}%</span>
                            </div>
                          </td>
                          {/* Actions */}
                          <td className="px-3 pr-5 py-3.5 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <button onClick={() => navigate(`/cases/${attempt.primaryid || attempt.case_id}`)}
                                className="h-8 px-3 rounded-md text-xs font-medium bg-[#EEF2FF] text-[#3730A3] hover:bg-indigo-100 transition-colors">
                                View Case
                              </button>
                              <button onClick={() => navigate(`/lifecycle/${attempt.primaryid || attempt.case_id}`)}
                                className="h-8 px-3 rounded-md text-xs font-medium bg-[#ECFDF5] text-[#065F46] hover:bg-emerald-100 transition-colors">
                                Lifecycle
                              </button>
                            </div>
                          </td>
                        </tr>

                        {/* Expanded timeline */}
                        {isExpanded && hasTimeline && (
                          <tr>
                            <td colSpan={8} className="bg-gray-50/60 px-5 py-4">
                              <div className="ml-10">
                                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Attempt Timeline</p>
                                <div className="space-y-2">
                                  {attempt.timeline.map((entry, idx) => (
                                    <div key={idx} className="flex items-center gap-3 bg-white rounded-lg border p-3">
                                      <div className="w-6 h-6 rounded-full bg-blue-50 text-blue-600 text-xs font-bold flex items-center justify-center flex-shrink-0">{entry.attempt_number || idx + 1}</div>
                                      <div className="flex-1 min-w-0">
                                        <p className="text-sm text-gray-800 font-medium">{entry.channel || attempt.channel} — <span className={`${entry.response_status === 'RESPONDED' ? 'text-emerald-600' : 'text-amber-600'}`}>{entry.response_status || 'Awaiting'}</span></p>
                                        {entry.timestamp && <p className="text-[10px] text-gray-400 mt-0.5">{new Date(entry.timestamp).toLocaleString()}</p>}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* ═══ PAGINATION ═══ */}
          {filteredAttempts.length > 0 && (
            <div className="border-t bg-gray-50/50 px-5 py-3 flex items-center justify-between text-sm">
              <p className="text-gray-500">
                Showing <span className="font-medium text-gray-900">{rangeStart}</span>–<span className="font-medium text-gray-900">{rangeEnd}</span> of{' '}
                <span className="font-medium text-gray-900">{filteredAttempts.length}</span> attempts
              </p>
              <div className="flex items-center gap-1">
                <button disabled={currentPage <= 1} onClick={() => setCurrentPage(p => p - 1)}
                  className="px-3 py-1.5 rounded-lg border text-gray-600 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed text-xs font-medium">
                  Prev
                </button>
                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter(p => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 2)
                  .reduce((acc, p, idx, arr) => {
                    if (idx > 0 && p - arr[idx - 1] > 1) acc.push('...' + p);
                    acc.push(p);
                    return acc;
                  }, [])
                  .map(p => typeof p === 'string'
                    ? <span key={p} className="px-1 text-gray-400">…</span>
                    : <button key={p} onClick={() => setCurrentPage(p)}
                        className={`w-8 h-8 rounded-lg text-xs font-medium ${p === currentPage ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-white border'}`}>
                        {p}
                      </button>
                  )}
                <button disabled={currentPage >= totalPages} onClick={() => setCurrentPage(p => p + 1)}
                  className="px-3 py-1.5 rounded-lg border text-gray-600 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed text-xs font-medium">
                  Next
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ═══ FOOTER ═══ */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center gap-3">
          <span className="text-blue-600 text-lg">ℹ️</span>
          <div>
            <p className="text-sm font-medium text-blue-900">Follow-Up Lifecycle Monitor</p>
            <p className="text-xs text-blue-700">Real-time tracking · All channels · Audit-ready · Last updated: {new Date().toLocaleString()}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ── sub-components ───────────────────────────────────────── */
const MetricCard = ({ label, value, icon, color }) => (
  <div className="bg-white rounded-xl border border-[#e5e7eb] shadow-sm p-5">
    <div className="flex items-center gap-2 mb-2">{icon}<span className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold">{label}</span></div>
    <p className={`text-2xl font-bold ${color || 'text-gray-900'}`}>{typeof value === 'number' ? value.toLocaleString() : value}</p>
  </div>
);

export default FollowUpAttempts;
