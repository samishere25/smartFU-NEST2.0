import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../utils/api';
import { useCaseEventListener } from '../context/CaseEventContext';
import {
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, Cell
} from 'recharts';

export default function Signals() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [signalsData, setSignalsData] = useState(null);
  const [escalating, setEscalating] = useState({});
  const [workflows, setWorkflows] = useState({});  // signalId -> workflow object
  const [selectedId, setSelectedId] = useState(null);
  const [search, setSearch] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('ALL');
  const [sortBy, setSortBy] = useState('prr'); // 'prr' | 'cases' | 'drug'

  useEffect(() => {
    fetchSignals();
    const interval = setInterval(fetchSignals, 60000);
    return () => clearInterval(interval);
  }, []);

  useCaseEventListener(() => { fetchSignals(); });

  const fetchSignals = async () => {
    try {
      setError(null);
      const data = await api.getActiveSignals();
      setSignalsData(data);
    } catch (err) {
      setError('Unable to load signals. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleStartRegulatory = async (signalId) => {
    try {
      setEscalating(prev => ({ ...prev, [signalId]: true }));
      const token = localStorage.getItem('access_token');
      const res = await fetch('/api/regulatory/start', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ signalId }),
      });
      if (!res.ok) throw new Error('Failed');
      const wf = await res.json();
      setWorkflows(prev => ({ ...prev, [signalId]: wf }));
    } catch {
      alert('Failed to start regulatory workflow');
    } finally {
      setEscalating(prev => ({ ...prev, [signalId]: false }));
    }
  };

  const handleViewCases = (drug, event) => {
    navigate(`/cases?drug=${encodeURIComponent(drug)}&event=${encodeURIComponent(event)}`);
  };

  // Derived data
  const signals = signalsData?.signals || [];
  const systemStatus = signalsData?.system_status || 'NORMAL';
  const highPriorityCount = signalsData?.high_priority_count || 0;
  const lastUpdated = signalsData?.last_updated;

  // Filter, search, sort
  const filtered = useMemo(() => {
    let list = [...signals];
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(s =>
        s.drug?.toLowerCase().includes(q) ||
        s.event?.toLowerCase().includes(q)
      );
    }
    if (priorityFilter !== 'ALL') {
      list = list.filter(s => s.escalation_level === priorityFilter);
    }
    list.sort((a, b) => {
      if (sortBy === 'prr') return (b.prr || 0) - (a.prr || 0);
      if (sortBy === 'cases') return (b.cases || 0) - (a.cases || 0);
      return (a.drug || '').localeCompare(b.drug || '');
    });
    return list;
  }, [signals, search, priorityFilter, sortBy]);

  const selected = useMemo(() => {
    if (!selectedId) return filtered[0] || null;
    return signals.find(s => s.signal_id === selectedId) || filtered[0] || null;
  }, [selectedId, signals, filtered]);

  // Auto-select first when filter changes
  useEffect(() => {
    if (filtered.length && !filtered.find(s => s.signal_id === selectedId)) {
      setSelectedId(filtered[0]?.signal_id || null);
    }
  }, [filtered]);

  // Chart data derived from signals — top 15 by PRR, capped for display readability
  const prrChartData = useMemo(() => {
    const sorted = [...signals].sort((a, b) => (b.prr || 0) - (a.prr || 0));
    const top = sorted.slice(0, 15);
    return top.map(s => {
      const drug = (s.drug || 'N/A').substring(0, 10);
      return {
        name: drug,
        fullName: `${s.drug || 'N/A'} - ${s.event || 'N/A'}`,
        prr: +(s.prr || 0).toFixed(2),
        prrDisplay: Math.min(+(s.prr || 0).toFixed(2), 100), // cap at 100 for chart scale
        prrCapped: (s.prr || 0) > 100,
        cases: s.cases || 0,
      };
    });
  }, [signals]);

  // Loading
  if (loading) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-10 w-10 border-2 border-gray-300 border-t-blue-600 mx-auto" />
        <p className="mt-3 text-sm text-gray-500">Loading signal data...</p>
      </div>
    </div>
  );

  // Fatal error
  if (error && !signalsData) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow p-8 max-w-md w-full text-center">
        <p className="text-red-600 mb-4">{error}</p>
        <button onClick={fetchSignals} className="px-5 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm">Retry</button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-[1440px] mx-auto px-5 py-5 space-y-4">

        {/* ── PAGE HEADER ────────────────────────────────── */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Severity Monitoring Console</h1>
            <p className="text-xs text-gray-500 mt-0.5">Real-time risk trend monitoring and regulatory escalation</p>
          </div>
          <button onClick={fetchSignals} className="px-3 py-1.5 border border-gray-300 rounded text-xs text-gray-600 hover:bg-gray-50">Refresh</button>
        </div>

        {/* ── STATUS STRIP ───────────────────────────────── */}
        <StatusStrip
          systemStatus={systemStatus}
          activeCount={signals.length}
          highPriority={highPriorityCount}
          lastScan={lastUpdated}
          error={error}
        />

        {/* ── MAIN 2-COLUMN AREA ─────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">

          {/* LEFT — SIGNAL LIST */}
          <div className="lg:col-span-5 xl:col-span-4 bg-white rounded-lg border border-gray-200 shadow-sm flex flex-col overflow-hidden">
            {/* Toolbar */}
            <div className="p-3 border-b border-gray-100 space-y-2">
              <input
                type="text"
                placeholder="Search drug or event..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full px-3 py-1.5 border border-gray-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 bg-gray-50"
              />
              <div className="flex gap-2">
                <select
                  value={priorityFilter}
                  onChange={e => setPriorityFilter(e.target.value)}
                  className="flex-1 px-2 py-1 border border-gray-200 rounded text-xs bg-gray-50 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="ALL">All Priorities</option>
                  <option value="IMMEDIATE">Immediate</option>
                  <option value="HIGH">High</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="LOW">Low</option>
                </select>
                <select
                  value={sortBy}
                  onChange={e => setSortBy(e.target.value)}
                  className="flex-1 px-2 py-1 border border-gray-200 rounded text-xs bg-gray-50 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="prr">Sort: PRR (High)</option>
                  <option value="cases">Sort: Cases</option>
                  <option value="drug">Sort: Drug A-Z</option>
                </select>
              </div>
            </div>

            {/* List header */}
            <div className="grid grid-cols-12 gap-1 px-3 py-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-100 bg-gray-50">
              <span className="col-span-5">Signal</span>
              <span className="col-span-2 text-right">PRR</span>
              <span className="col-span-2 text-right">Cases</span>
              <span className="col-span-1 text-center">Trend</span>
              <span className="col-span-2 text-center">Priority</span>
            </div>

            {/* List body — fixed max-height, scrollable */}
            <div className="overflow-y-auto divide-y divide-gray-50" style={{ maxHeight: 380 }}>
              {filtered.length === 0 ? (
                <div className="flex items-center justify-center text-gray-400 text-xs py-12">
                  {signals.length === 0 ? 'No active signals detected' : 'No signals match filters'}
                </div>
              ) : (
                filtered.map(s => (
                  <SignalRow
                    key={s.signal_id}
                    signal={s}
                    isSelected={selected?.signal_id === s.signal_id}
                    onClick={() => setSelectedId(s.signal_id)}
                  />
                ))
              )}
            </div>

            {/* List footer */}
            <div className="px-3 py-2 border-t border-gray-100 bg-gray-50 text-[10px] text-gray-400">
              {filtered.length} of {signals.length} signals
            </div>
          </div>

          {/* RIGHT — SIGNAL DETAIL */}
          <div className="lg:col-span-7 xl:col-span-8 bg-white rounded-lg border border-gray-200 shadow-sm">
            {selected ? (
              <SignalDetail
                signal={selected}
                escalating={escalating}
                workflow={workflows[selected.signal_id] || null}
                onStartRegulatory={handleStartRegulatory}
                onViewCases={handleViewCases}
                onRefresh={fetchSignals}
              />
            ) : (
              <div className="flex items-center justify-center py-20 text-gray-400 text-sm">
                Select a signal to view details
              </div>
            )}
          </div>
        </div>

        {/* ── CHARTS SECTION ─────────────────────────────── */}
        {prrChartData.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ChartCard title="PRR Distribution" subtitle={`Top ${prrChartData.length} signals by PRR (capped at 100 for readability)`}>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={prrChartData} margin={{ top: 12, right: 16, left: 4, bottom: 40 }} barCategoryGap="15%">
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 9, fill: '#6b7280' }}
                    axisLine={{ stroke: '#e5e7eb' }}
                    tickLine={false}
                    angle={-35}
                    textAnchor="end"
                    height={50}
                    interval={0}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: '#9ca3af' }}
                    axisLine={false}
                    tickLine={false}
                    domain={[0, 'auto']}
                    label={{ value: 'PRR', angle: -90, position: 'insideLeft', style: { fontSize: 10, fill: '#9ca3af' } }}
                  />
                  <Tooltip
                    contentStyle={{ fontSize: 11, borderRadius: 6, border: '1px solid #e5e7eb', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}
                    labelFormatter={(_, payload) => payload?.[0]?.payload?.fullName || ''}
                    formatter={(v, name, entry) => {
                      const actual = entry?.payload?.prr;
                      return [actual != null ? actual.toFixed(2) : v.toFixed(2), 'PRR'];
                    }}
                    cursor={{ fill: 'rgba(0,0,0,0.03)' }}
                  />
                  <Bar dataKey="prrDisplay" name="PRR" radius={[4, 4, 0, 0]} maxBarSize={40}>
                    {prrChartData.map((entry, i) => (
                      <Cell key={i} fill={entry.prr >= 5 ? '#ef4444' : entry.prr >= 3 ? '#f59e0b' : '#2563EB'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <div className="flex items-center justify-center gap-4 mt-1 text-[10px] text-gray-400">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-[#ef4444] inline-block" /> PRR &ge; 5 (Very High)</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-[#f59e0b] inline-block" /> PRR 3-5 (High)</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-[#2563EB] inline-block" /> PRR &lt; 3 (Moderate)</span>
              </div>
            </ChartCard>

            <ChartCard title="Case Volume" subtitle={`Reported case count per signal (Top ${prrChartData.length})`}>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={prrChartData} margin={{ top: 12, right: 16, left: 4, bottom: 40 }} barCategoryGap="15%">
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 9, fill: '#6b7280' }}
                    axisLine={{ stroke: '#e5e7eb' }}
                    tickLine={false}
                    angle={-35}
                    textAnchor="end"
                    height={50}
                    interval={0}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: '#9ca3af' }}
                    axisLine={false}
                    tickLine={false}
                    allowDecimals={false}
                    label={{ value: 'Cases', angle: -90, position: 'insideLeft', style: { fontSize: 10, fill: '#9ca3af' } }}
                  />
                  <Tooltip
                    contentStyle={{ fontSize: 11, borderRadius: 6, border: '1px solid #e5e7eb', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}
                    labelFormatter={(_, payload) => payload?.[0]?.payload?.fullName || ''}
                    formatter={(v) => [v.toLocaleString(), 'Cases']}
                    cursor={{ fill: 'rgba(0,0,0,0.03)' }}
                  />
                  <Bar dataKey="cases" name="Cases" fill="#6366f1" radius={[4, 4, 0, 0]} maxBarSize={40} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        )}

        {/* ── FOOTER INFO ────────────────────────────────── */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg px-4 py-3 flex items-start gap-3">
          <span className="text-gray-400 text-sm mt-0.5">i</span>
          <div className="text-xs text-gray-500 leading-relaxed">
            <span className="font-medium text-gray-600">Signal Detection.</span>{' '}
            Signals are automatically detected using Proportional Reporting Ratio (PRR) analysis.
            PRR &gt; 2 with case count &gt; 3 triggers investigation.
            Escalation levels are determined by signal strength, trend, and regulatory requirements.
          </div>
        </div>
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════
   SUB-COMPONENTS
   ═══════════════════════════════════════════════════════════ */

function StatusStrip({ systemStatus, activeCount, highPriority, lastScan, error }) {
  const statusColor = {
    CRITICAL: 'bg-red-500',
    ELEVATED: 'bg-amber-500',
    NORMAL: 'bg-emerald-500',
  }[systemStatus] || 'bg-gray-400';

  const statusText = {
    CRITICAL: 'text-red-700',
    ELEVATED: 'text-amber-700',
    NORMAL: 'text-emerald-700',
  }[systemStatus] || 'text-gray-600';

  const statusBg = {
    CRITICAL: 'bg-red-50',
    ELEVATED: 'bg-amber-50',
    NORMAL: 'bg-emerald-50',
  }[systemStatus] || 'bg-gray-50';

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm px-5 py-3">
      <div className="flex items-center justify-between flex-wrap gap-y-2">
        {/* System Status */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${statusColor} ${systemStatus === 'CRITICAL' ? 'animate-pulse' : ''}`} />
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">System</span>
          </div>
          <span className={`text-xs font-semibold px-2 py-0.5 rounded ${statusBg} ${statusText}`}>
            {systemStatus}
          </span>
        </div>

        <Divider />

        {/* Active Signals */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Active Signals</span>
          <span className="text-sm font-bold text-gray-900">{activeCount}</span>
        </div>

        <Divider />

        {/* High Priority */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">High Priority</span>
          <span className={`text-sm font-bold ${highPriority > 0 ? 'text-red-600' : 'text-gray-900'}`}>
            {highPriority}
          </span>
          {highPriority > 0 && (
            <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
          )}
        </div>

        <Divider />

        {/* Last Scan */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Last Scan</span>
          <span className="text-xs font-medium text-gray-700">
            {lastScan ? new Date(lastScan).toLocaleString() : 'N/A'}
          </span>
        </div>

        {error && (
          <>
            <Divider />
            <span className="text-xs text-amber-600">{error}</span>
          </>
        )}
      </div>
    </div>
  );
}

function Divider() {
  return <span className="hidden sm:block w-px h-5 bg-gray-200" />;
}


function SignalRow({ signal, isSelected, onClick }) {
  const s = signal;
  const priorityColors = {
    IMMEDIATE: 'bg-red-100 text-red-700',
    HIGH: 'bg-orange-100 text-orange-700',
    MEDIUM: 'bg-yellow-100 text-yellow-700',
    LOW: 'bg-blue-100 text-blue-700',
  };
  const trendIcon = { UP: '\u2191', DOWN: '\u2193', STABLE: '\u2192' };

  return (
    <div
      onClick={onClick}
      className={`grid grid-cols-12 gap-1 px-3 py-2.5 cursor-pointer transition-colors text-xs items-center ${
        isSelected ? 'bg-blue-50 border-l-2 border-blue-500' : 'hover:bg-gray-50 border-l-2 border-transparent'
      }`}
    >
      <div className="col-span-5 min-w-0">
        <p className="font-medium text-gray-900 truncate">{s.drug || 'Unknown'}</p>
        <p className="text-[10px] text-gray-400 truncate">{s.event || ''}</p>
      </div>
      <div className="col-span-2 text-right">
        <span className={`font-bold ${(s.prr || 0) >= 5 ? 'text-red-600' : (s.prr || 0) >= 3 ? 'text-amber-600' : 'text-gray-700'}`}>
          {(s.prr || 0).toFixed(1)}
        </span>
      </div>
      <div className="col-span-2 text-right text-gray-700">{s.cases || 0}</div>
      <div className="col-span-1 text-center">
        <span className={`text-xs ${s.trend === 'UP' ? 'text-red-500' : s.trend === 'DOWN' ? 'text-green-500' : 'text-gray-400'}`}>
          {trendIcon[s.trend] || '\u2022'}
        </span>
      </div>
      <div className="col-span-2 text-center">
        <span className={`inline-block px-1.5 py-0.5 rounded text-[9px] font-semibold ${priorityColors[s.escalation_level] || 'bg-gray-100 text-gray-600'}`}>
          {s.escalation_level || 'N/A'}
        </span>
      </div>
    </div>
  );
}


function SignalDetail({ signal, escalating, workflow, onStartRegulatory, onViewCases, onRefresh }) {
  const s = signal;
  const [reviewAction, setReviewAction] = useState('');
  const [reviewNote, setReviewNote] = useState('');
  const [reviewPriority, setReviewPriority] = useState('');
  const [submittingReview, setSubmittingReview] = useState(false);
  const [signalCases, setSignalCases] = useState(null);
  const [showCases, setShowCases] = useState(false);
  const [loadingCases, setLoadingCases] = useState(false);

  const priorityColors = {
    CRITICAL: 'bg-red-100 text-red-700 border-red-200',
    IMMEDIATE: 'bg-red-100 text-red-700 border-red-200',
    HIGH: 'bg-orange-100 text-orange-700 border-orange-200',
    MEDIUM: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    LOW: 'bg-blue-100 text-blue-700 border-blue-200',
  };
  const trendLabel = { UP: 'Increasing', DOWN: 'Decreasing', STABLE: 'Stable' };
  const trendColor = { UP: 'text-red-600', DOWN: 'text-green-600', STABLE: 'text-gray-500' };
  const trendArrow = { UP: '\u2191', DOWN: '\u2193', STABLE: '\u2192' };

  const handleSubmitReview = async () => {
    if (!reviewAction || !reviewNote.trim()) return;
    try {
      setSubmittingReview(true);
      await api.reviewSignal(
        s.signal_id,
        reviewAction,
        reviewNote,
        reviewPriority || null
      );
      setReviewAction('');
      setReviewNote('');
      setReviewPriority('');
      if (onRefresh) onRefresh();
    } catch {
      alert('Failed to submit review');
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleLoadCases = async () => {
    if (signalCases) { setShowCases(!showCases); return; }
    try {
      setLoadingCases(true);
      const data = await api.getSignalCases(s.signal_id);
      setSignalCases(data);
      setShowCases(true);
    } catch {
      alert('Failed to load signal cases');
    } finally {
      setLoadingCases(false);
    }
  };

  return (
    <div className="p-5 space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-lg font-semibold text-gray-900">{s.drug} &rarr; {s.event}</h2>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${priorityColors[s.escalation_level] || 'bg-gray-100 text-gray-600 border-gray-200'}`}>
              {s.escalation_level}
            </span>
            {s.signal_status && (
              <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-600 border border-gray-200">
                {s.signal_status}
              </span>
            )}
          </div>
          <div className="flex items-center gap-4 mt-1.5 text-xs text-gray-500">
            <span>PRR <strong className="text-gray-800">{(s.prr || 0).toFixed(2)}</strong></span>
            {s.seriousness_ratio != null && (
              <span>Serious <strong className={s.seriousness_ratio >= 0.5 ? 'text-red-600' : 'text-gray-800'}>
                {(s.seriousness_ratio * 100).toFixed(0)}%
              </strong></span>
            )}
            <span className={trendColor[s.trend] || 'text-gray-500'}>
              {trendArrow[s.trend] || ''} {trendLabel[s.trend] || s.trend}
            </span>
            {s.detected_at && <span>Detected {new Date(s.detected_at).toLocaleDateString()}</span>}
            {s.last_updated && <span>Updated {new Date(s.last_updated).toLocaleDateString()}</span>}
          </div>
        </div>
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-4 gap-3">
        <MetricCard
          label="PRR (Risk Ratio)"
          value={(s.prr || 0).toFixed(2)}
          sub={s.prr >= 5 ? 'Very High' : s.prr >= 3 ? 'High' : s.prr >= 2 ? 'Moderate' : 'Low'}
          valueColor={s.prr >= 5 ? 'text-red-600' : s.prr >= 3 ? 'text-amber-600' : 'text-gray-900'}
        />
        <MetricCard
          label="Case Count"
          value={s.cases || 0}
          sub="Reported events"
        />
        <MetricCard
          label="Seriousness"
          value={s.seriousness_ratio != null ? `${(s.seriousness_ratio * 100).toFixed(0)}%` : 'N/A'}
          sub="Serious case ratio"
          valueColor={s.seriousness_ratio >= 0.5 ? 'text-red-600' : 'text-gray-900'}
        />
        <MetricCard
          label="Trend Direction"
          value={`${trendArrow[s.trend] || ''} ${trendLabel[s.trend] || s.trend || 'Unknown'}`}
          sub={s.trend === 'UP' ? 'Requires attention' : 'Monitoring'}
          valueColor={trendColor[s.trend] || 'text-gray-900'}
        />
      </div>

      {/* Review note (if exists) */}
      {s.review_note && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-semibold text-amber-700 uppercase">Reviewer Note</span>
            {s.reviewed_by && <span className="text-[10px] text-amber-500">by {s.reviewed_by.substring(0, 12)}</span>}
            {s.reviewed_at && <span className="text-[10px] text-amber-400">{new Date(s.reviewed_at).toLocaleDateString()}</span>}
          </div>
          <p className="text-xs text-amber-800">{s.review_note}</p>
        </div>
      )}

      {/* Recommended actions */}
      {s.recommended_actions?.length > 0 && (
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
          <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">Recommended Actions</h3>
          <ul className="space-y-1.5">
            {s.recommended_actions.map((action, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                <span className="w-1 h-1 rounded-full bg-gray-400 mt-1.5 flex-shrink-0" />
                {action}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── HUMAN OVERSIGHT PANEL ── */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
        <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">Human Oversight</h3>
        <div className="flex flex-wrap gap-2 items-end">
          <div className="flex-1 min-w-[130px]">
            <label className="block text-[10px] text-gray-500 mb-1">Action</label>
            <select value={reviewAction} onChange={e => setReviewAction(e.target.value)}
              className="w-full px-2 py-1.5 border border-gray-200 rounded text-xs bg-gray-50 focus:outline-none focus:ring-1 focus:ring-blue-500">
              <option value="">Select action...</option>
              <option value="DOWNGRADE">Downgrade Priority</option>
              <option value="ESCALATE">Escalate Priority</option>
              <option value="FALSE_POSITIVE">Mark False Positive</option>
              <option value="NOTE">Add Review Note</option>
            </select>
          </div>
          {(reviewAction === 'DOWNGRADE' || reviewAction === 'ESCALATE') && (
            <div className="min-w-[110px]">
              <label className="block text-[10px] text-gray-500 mb-1">New Priority</label>
              <select value={reviewPriority} onChange={e => setReviewPriority(e.target.value)}
                className="w-full px-2 py-1.5 border border-gray-200 rounded text-xs bg-gray-50 focus:outline-none focus:ring-1 focus:ring-blue-500">
                <option value="">Select...</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>
          )}
          <div className="flex-[2] min-w-[200px]">
            <label className="block text-[10px] text-gray-500 mb-1">Note (required)</label>
            <input type="text" value={reviewNote} onChange={e => setReviewNote(e.target.value)}
              placeholder="Reason for review action..."
              className="w-full px-2 py-1.5 border border-gray-200 rounded text-xs bg-gray-50 focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
          <button onClick={handleSubmitReview}
            disabled={submittingReview || !reviewAction || !reviewNote.trim()}
            className="px-3 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed">
            {submittingReview ? 'Submitting...' : 'Submit'}
          </button>
        </div>
      </div>

      {/* Regulatory Workflow Status */}
      {workflow && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
              <span className="text-xs font-semibold text-blue-800">Regulatory Workflow Active</span>
            </div>
            <span className="text-[10px] font-medium text-blue-600 bg-blue-100 px-2 py-0.5 rounded">{workflow.status}</span>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <p className="text-[10px] text-blue-500 font-medium uppercase tracking-wide">Report Type</p>
              <p className="text-xs font-semibold text-blue-900 mt-0.5">{workflow.report_type?.replace('_', ' ') || 'CIOMS DRAFT'}</p>
            </div>
            <div>
              <p className="text-[10px] text-blue-500 font-medium uppercase tracking-wide">Due Date</p>
              <p className="text-xs font-semibold text-blue-900 mt-0.5">{workflow.due_date ? new Date(workflow.due_date).toLocaleDateString() : '—'}</p>
            </div>
            <div>
              <p className="text-[10px] text-blue-500 font-medium uppercase tracking-wide">Progress</p>
              <div className="flex items-center gap-2 mt-1">
                <div className="flex-1 h-1.5 bg-blue-200 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-600 rounded-full" style={{ width: workflow.status === 'COMPLETED' ? '100%' : workflow.status === 'IN_PROGRESS' ? '40%' : '10%' }} />
                </div>
                <span className="text-[10px] font-medium text-blue-700">{workflow.status === 'COMPLETED' ? '100%' : workflow.status === 'IN_PROGRESS' ? '40%' : '10%'}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── LINKED CASES PANEL ── */}
      <div className="border-t border-gray-100 pt-3 space-y-2">
        <button onClick={handleLoadCases} disabled={loadingCases}
          className="text-xs text-blue-600 hover:underline font-medium">
          {loadingCases ? 'Loading cases...' : showCases ? 'Hide Linked Cases' : `Show Linked Cases (${s.cases || 0})`}
        </button>
        {showCases && signalCases && (
          <div className="space-y-2">
            {/* Risk distribution */}
            {signalCases.risk_distribution && Object.keys(signalCases.risk_distribution).length > 0 && (
              <div className="flex gap-2 flex-wrap">
                {Object.entries(signalCases.risk_distribution).map(([risk, count]) => (
                  <span key={risk} className="text-[10px] px-2 py-0.5 rounded bg-gray-100 text-gray-600">
                    {risk}: <strong>{count}</strong>
                  </span>
                ))}
              </div>
            )}
            {/* Case list */}
            <div className="max-h-[200px] overflow-y-auto divide-y divide-gray-50 border border-gray-200 rounded">
              {(signalCases.cases || []).slice(0, 50).map(c => (
                <div key={c.case_id} className="px-3 py-2 flex items-center justify-between text-xs hover:bg-gray-50">
                  <div>
                    <span className="font-mono text-gray-600">{c.primaryid || c.case_id?.substring(0, 8)}</span>
                    <span className="ml-2 text-gray-400">{c.suspect_drug} / {c.adverse_event}</span>
                  </div>
                  <div className="flex gap-2">
                    {c.is_serious && <span className="text-[9px] px-1.5 py-0.5 rounded bg-red-100 text-red-600 font-semibold">SERIOUS</span>}
                    {c.risk_level && <span className="text-[9px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">{c.risk_level}</span>}
                    {c.followup_status && <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600">{c.followup_status}</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-3 pt-2 border-t border-gray-100">
        <button
          onClick={() => onViewCases(s.drug, s.event)}
          className="flex-1 px-4 py-2 bg-white border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
        >
          View Related Cases
        </button>
        {workflow ? (
          <button
            disabled
            className="flex-1 px-4 py-2 bg-blue-50 border border-blue-200 text-blue-600 text-sm font-medium rounded-lg cursor-default flex items-center justify-center gap-2"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            Regulatory Workflow Active
          </button>
        ) : (
          <button
            onClick={() => onStartRegulatory(s.signal_id)}
            disabled={escalating[s.signal_id]}
            className="flex-1 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {escalating[s.signal_id] ? 'Processing...' : 'Start Regulatory Process'}
          </button>
        )}
      </div>
    </div>
  );
}


function MetricCard({ label, value, sub, valueColor }) {
  return (
    <div className="bg-gray-50 rounded-lg border border-gray-200 p-3">
      <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-xl font-bold mt-1 ${valueColor || 'text-gray-900'}`}>{value}</p>
      {sub && <p className="text-[10px] text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}


function ChartCard({ title, subtitle, children }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
        {subtitle && <p className="text-[10px] text-gray-400">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}
