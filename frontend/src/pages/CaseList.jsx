import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useCaseEventListener } from '../context/CaseEventContext';

const PAGE_SIZE = 15;

/* ── helpers ───────────────────────────────────────────────── */
const riskMeta = (s) => {
  if (s >= 0.7) return { label: 'Critical', bg: 'bg-red-50', text: 'text-red-700', ring: 'ring-red-600/20', border: 'border-l-red-500', dot: 'bg-red-500' };
  if (s >= 0.4) return { label: 'Medium',   bg: 'bg-amber-50', text: 'text-amber-700', ring: 'ring-amber-600/20', border: 'border-l-amber-400', dot: 'bg-amber-400' };
  return              { label: 'Low',      bg: 'bg-emerald-50', text: 'text-emerald-700', ring: 'ring-emerald-600/20', border: 'border-l-gray-300', dot: 'bg-emerald-500' };
};

const statusMeta = (s) => {
  if (s >= 0.7) return { label: 'Critical',     cls: 'bg-red-50 text-red-700 ring-1 ring-red-600/20' };
  if (s >= 0.4) return { label: 'Needs Review',  cls: 'bg-amber-50 text-amber-700 ring-1 ring-amber-600/20' };
  return              { label: 'Normal',         cls: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20' };
};

const pct = (v) => Math.round((v || 0) * 100);

const CaseList = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterRisk, setFilterRisk] = useState('ALL'); // ALL, HIGH — drives API

  /* ── new client-side state ──────────────────────────────── */
  const [searchTerm, setSearchTerm] = useState('');
  const [completenessFilter, setCompletenessFilter] = useState('ALL');
  const [sortBy, setSortBy] = useState('default');
  const [currentPage, setCurrentPage] = useState(1);

  // Signal filter params from URL
  const drugFilter = searchParams.get('drug');
  const eventFilter = searchParams.get('event');

  useEffect(() => {
    fetchCases();
  }, [filterRisk, drugFilter, eventFilter]);

  // Auto-refresh when ANY case is updated
  useCaseEventListener((event) => {
    console.log('📋 CaseList: Refreshing due to case event:', event.type);
    fetchCases();
  });

  const fetchCases = async () => {
    try {
      setLoading(true);
      setError(null);

      const token = localStorage.getItem('access_token');
      const baseUrl = '';

      // Build URL with filters
      let url = `${baseUrl}/api/cases/?limit=100`;
      if (filterRisk === 'HIGH') {
        url += '&risk_level=HIGH';
      }
      if (drugFilter) {
        url += `&drug=${encodeURIComponent(drugFilter)}`;
      }
      if (eventFilter) {
        url += `&event=${encodeURIComponent(eventFilter)}`;
      }

      console.log('🔍 Fetching cases with URL:', url);

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch cases');
      }

      const data = await response.json();
      console.log(`✅ Loaded ${data.cases?.length || 0} cases (filter: ${filterRisk})`);
      setCases(data.cases || []);
    } catch (err) {
      setError(err.message || 'Failed to load cases');
    } finally {
      setLoading(false);
    }
  };

  /* ── derived / filtered / sorted / paginated ────────────── */
  const resetPage = useCallback(() => setCurrentPage(1), []);

  const filteredCases = useMemo(() => {
    let list = [...cases];

    // search
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      list = list.filter(c =>
        String(c.primaryid).toLowerCase().includes(q) ||
        (c.suspect_drug || c.drug_name || '').toLowerCase().includes(q) ||
        (c.adverse_event || '').toLowerCase().includes(q)
      );
    }

    // completeness bucket
    if (completenessFilter !== 'ALL') {
      list = list.filter(c => {
        const v = (c.data_completeness_score || 0) * 100;
        if (completenessFilter === '<60') return v < 60;
        if (completenessFilter === '60-80') return v >= 60 && v < 80;
        if (completenessFilter === '>80') return v >= 80;
        return true;
      });
    }

    // sort
    if (sortBy === 'risk-desc')        list.sort((a, b) => (b.seriousness_score || 0) - (a.seriousness_score || 0));
    else if (sortBy === 'risk-asc')    list.sort((a, b) => (a.seriousness_score || 0) - (b.seriousness_score || 0));
    else if (sortBy === 'comp-desc')   list.sort((a, b) => (b.data_completeness_score || 0) - (a.data_completeness_score || 0));
    else if (sortBy === 'comp-asc')    list.sort((a, b) => (a.data_completeness_score || 0) - (b.data_completeness_score || 0));

    return list;
  }, [cases, searchTerm, completenessFilter, sortBy]);

  const totalPages = Math.max(1, Math.ceil(filteredCases.length / PAGE_SIZE));
  const paginatedCases = filteredCases.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);
  const rangeStart = filteredCases.length ? (currentPage - 1) * PAGE_SIZE + 1 : 0;
  const rangeEnd = Math.min(currentPage * PAGE_SIZE, filteredCases.length);

  // reset page when filters change
  useEffect(() => { resetPage(); }, [searchTerm, completenessFilter, sortBy, filterRisk, resetPage]);

  /* ── loading ────────────────────────────────────────────── */
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="animate-spin rounded-full h-10 w-10 border-2 border-blue-600 border-t-transparent mx-auto" />
          <p className="text-sm text-gray-500">Loading cases…</p>
        </div>
      </div>
    );
  }

  /* ── error ──────────────────────────────────────────────── */
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="max-w-sm w-full bg-white rounded-xl shadow-sm border p-8 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center mx-auto">
            <svg className="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          </div>
          <p className="text-sm font-medium text-gray-900">{error}</p>
          <button onClick={fetchCases} className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium">Retry</button>
        </div>
      </div>
    );
  }

  /* ── main render ────────────────────────────────────────── */
  return (
    <div className="min-h-screen bg-gray-50">

      {/* Signal Filter Banner */}
      {(drugFilter || eventFilter) && (
        <div className="bg-blue-50 border-b border-blue-200">
          <div className="max-w-[1400px] mx-auto px-6 py-2.5 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm">
              <span className="text-blue-600 font-medium">Filtered by Signal:</span>
              {drugFilter && <span className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded-md text-xs font-medium">Drug: {drugFilter}</span>}
              {eventFilter && <span className="bg-purple-100 text-purple-800 px-2 py-0.5 rounded-md text-xs font-medium">Event: {eventFilter}</span>}
            </div>
            <button onClick={() => navigate('/cases')} className="text-blue-600 hover:text-blue-800 text-xs font-medium">Clear Filter</button>
          </div>
        </div>
      )}

      <div className="max-w-[1400px] mx-auto px-6 py-8 space-y-6">

        {/* ═══ HEADER ═══ */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Case Repository</h1>
            <p className="text-sm text-gray-500 mt-0.5">{cases.length} total cases · {filteredCases.length} shown</p>
          </div>
          <button onClick={fetchCases} className="self-start sm:self-auto px-4 py-2 bg-white border rounded-lg text-sm text-gray-600 hover:bg-gray-50 shadow-sm flex items-center gap-1.5">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
            Refresh
          </button>
        </div>

        {/* ═══ FILTERS BAR ═══ */}
        <div className="bg-white rounded-xl shadow-sm border p-4">
          <div className="flex flex-wrap items-center gap-3">
            {/* Search */}
            <div className="relative flex-1 min-w-[220px]">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
              <input
                type="text"
                placeholder="Search by Case ID, drug, or event…"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500"
              />
            </div>

            <div className="h-8 w-px bg-gray-200 hidden sm:block" />

            {/* Risk Level (drives API) */}
            <select value={filterRisk} onChange={e => setFilterRisk(e.target.value)}
              className="border rounded-lg px-3 py-2 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/30">
              <option value="ALL">All Risk Levels</option>
              <option value="HIGH">High Risk Only</option>
            </select>

            {/* Completeness (client-side) */}
            <select value={completenessFilter} onChange={e => setCompletenessFilter(e.target.value)}
              className="border rounded-lg px-3 py-2 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/30">
              <option value="ALL">All Completeness</option>
              <option value="<60">Below 60%</option>
              <option value="60-80">60 – 80%</option>
              <option value=">80">Above 80%</option>
            </select>

            {/* Sort */}
            <select value={sortBy} onChange={e => setSortBy(e.target.value)}
              className="border rounded-lg px-3 py-2 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/30">
              <option value="default">Sort: Default</option>
              <option value="risk-desc">Risk ↓</option>
              <option value="risk-asc">Risk ↑</option>
              <option value="comp-desc">Completeness ↓</option>
              <option value="comp-asc">Completeness ↑</option>
            </select>
          </div>
        </div>

        {/* ═══ TABLE ═══ */}
        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          {filteredCases.length === 0 ? (
            <div className="py-16 text-center">
              <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"/></svg>
              <p className="text-gray-500 font-medium">No cases found</p>
              <p className="text-gray-400 text-sm mt-1">{searchTerm ? 'Try a different search term' : filterRisk === 'HIGH' ? 'Try viewing all cases' : 'Upload data to get started'}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b text-left">
                    <th className="pl-5 pr-3 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wider w-[100px]">Case ID</th>
                    <th className="px-3 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wider w-[60px]">Source</th>
                    <th className="px-3 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wider">Drug</th>
                    <th className="px-3 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wider">Adverse Event</th>
                    <th className="px-3 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wider w-[110px]">Risk Score</th>
                    <th className="px-3 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wider w-[160px]">Completeness</th>
                    <th className="px-3 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wider w-[100px]">Seriousness</th>
                    <th className="px-3 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wider w-[110px]">Status</th>
                    <th className="px-3 pr-5 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wider text-right w-[180px]">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {paginatedCases.map((c) => {
                    const score = c.seriousness_score || 0;
                    const risk = riskMeta(score);
                    const comp = pct(c.data_completeness_score);
                    const compColor = comp >= 80 ? 'bg-emerald-500' : comp >= 60 ? 'bg-blue-500' : comp >= 40 ? 'bg-amber-400' : 'bg-red-400';
                    const status = statusMeta(score);

                    return (
                      <tr key={c.primaryid}
                        className={`border-l-4 ${risk.border} hover:bg-gray-50/70 transition-colors group`}>
                        {/* Case ID */}
                        <td className="pl-5 pr-3 py-3.5">
                          <span className="font-mono text-xs font-semibold text-gray-900">{c.primaryid}</span>
                        </td>
                        {/* Source */}
                        <td className="px-3 py-3.5">
                          <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                            c.intake_source === 'PDF'
                              ? 'bg-purple-50 text-purple-700 ring-1 ring-purple-600/20'
                              : 'bg-gray-50 text-gray-600 ring-1 ring-gray-300/50'
                          }`}>
                            {c.intake_source === 'PDF' ? 'PDF' : 'CSV'}
                          </span>
                        </td>
                        {/* Drug */}
                        <td className="px-3 py-3.5 max-w-[180px]">
                          <span className="text-gray-900 font-medium truncate block" title={c.suspect_drug || c.drug_name}>{c.suspect_drug || c.drug_name || 'N/A'}</span>
                        </td>
                        {/* Adverse Event */}
                        <td className="px-3 py-3.5 max-w-[200px]">
                          <span className="text-gray-600 truncate block" title={c.adverse_event}>{c.adverse_event || 'N/A'}</span>
                        </td>
                        {/* Risk Score Badge */}
                        <td className="px-3 py-3.5">
                          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ring-1 ${risk.bg} ${risk.text} ${risk.ring}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${risk.dot}`} />
                            {pct(score)}%
                          </span>
                        </td>
                        {/* Completeness Progress */}
                        <td className="px-3 py-3.5">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                              <div className={`h-full rounded-full ${compColor} transition-all`} style={{ width: `${comp}%` }} />
                            </div>
                            <span className="text-xs font-semibold text-gray-700 tabular-nums w-9 text-right">{comp}%</span>
                          </div>
                        </td>
                        {/* Seriousness */}
                        <td className="px-3 py-3.5">
                          <span className="text-sm font-semibold text-gray-900">{pct(score)}%</span>
                        </td>
                        {/* Status */}
                        <td className="px-3 py-3.5">
                          <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-medium ${status.cls}`}>{status.label}</span>
                        </td>
                        {/* Actions */}
                        <td className="px-3 pr-5 py-3.5 text-right">
                          <div className="flex items-center justify-end gap-2 opacity-70 group-hover:opacity-100 transition-opacity">
                            <button onClick={() => navigate(`/cases/${c.primaryid}`)}
                              className="px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-xs font-medium transition-colors">
                              Analyze
                            </button>
                            <button onClick={() => navigate(`/cases/${c.primaryid}`)}
                              className="px-3 py-1.5 bg-white border text-gray-700 rounded-lg hover:bg-gray-50 text-xs font-medium transition-colors">
                              View
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* ═══ PAGINATION ═══ */}
          {filteredCases.length > 0 && (
            <div className="border-t bg-gray-50/50 px-5 py-3 flex items-center justify-between text-sm">
              <p className="text-gray-500">
                Showing <span className="font-medium text-gray-900">{rangeStart}</span>–<span className="font-medium text-gray-900">{rangeEnd}</span> of{' '}
                <span className="font-medium text-gray-900">{filteredCases.length}</span> cases
              </p>
              <div className="flex items-center gap-1">
                <button disabled={currentPage <= 1} onClick={() => setCurrentPage(p => p - 1)}
                  className="px-3 py-1.5 rounded-lg border text-gray-600 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed text-xs font-medium transition-colors">
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
                        className={`w-8 h-8 rounded-lg text-xs font-medium transition-colors ${p === currentPage ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-white border'}`}>
                        {p}
                      </button>
                  )}
                <button disabled={currentPage >= totalPages} onClick={() => setCurrentPage(p => p + 1)}
                  className="px-3 py-1.5 rounded-lg border text-gray-600 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed text-xs font-medium transition-colors">
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
            <p className="text-sm font-medium text-blue-900">Pharmacovigilance Case Repository</p>
            <p className="text-xs text-blue-700">Real-time data · Click <strong>Analyze</strong> to run AI assessment · Last updated: {new Date().toLocaleString()}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CaseList;
