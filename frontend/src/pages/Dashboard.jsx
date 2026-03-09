import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../utils/api';
import { useCaseEventListener } from '../context/CaseEventContext';
import RepoDocumentsBlock from '../components/RepoDocumentsBlock';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell
} from 'recharts';

const COLORS = ['#2563EB', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

const MiniDonut = ({ data, size = 140 }) => {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (!total) return null;
  const cx = size / 2, cy = size / 2, r = size / 2 - 14, sw = 18;
  let cum = 0;
  const arcs = data.map((d) => {
    const frac = d.value / total;
    const start = cum * 2 * Math.PI - Math.PI / 2;
    cum += frac;
    const end = cum * 2 * Math.PI - Math.PI / 2;
    const large = frac > 0.5 ? 1 : 0;
    const x1 = cx + r * Math.cos(start), y1 = cy + r * Math.sin(start);
    const x2 = cx + r * Math.cos(end), y2 = cy + r * Math.sin(end);
    return (
      <path key={d.name} d={`M${x1},${y1} A${r},${r} 0 ${large} 1 ${x2},${y2}`}
        fill="none" stroke={d.color} strokeWidth={sw} strokeLinecap="round" />
    );
  });
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {arcs}
      <text x={cx} y={cy - 4} textAnchor="middle" className="text-xl font-bold" fill="#111827">{total.toLocaleString()}</text>
      <text x={cx} y={cy + 12} textAnchor="middle" className="text-[10px]" fill="#9CA3AF">Total</text>
    </svg>
  );
};

const Dashboard = () => {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState(null);
  const [highRiskCases, setHighRiskCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  // PDF Upload
  const [pdfFile, setPdfFile] = useState(null);
  const [pdfUploading, setPdfUploading] = useState(false);
  const [pdfResult, setPdfResult] = useState(null);
  const [pdfError, setPdfError] = useState(null);

  // XML Upload
  const [xmlFile, setXmlFile] = useState(null);
  const [xmlUploading, setXmlUploading] = useState(false);
  const [xmlResult, setXmlResult] = useState(null);
  const [xmlError, setXmlError] = useState(null);

  useEffect(() => { fetchDashboardData(); }, []);

  useCaseEventListener((ev) => { fetchDashboardData(); });

  const fetchDashboardData = async () => {
    try {
      setLoading(true); setError(null);
      const [metricsData, casesRes] = await Promise.all([
        api.getDashboardMetrics(),
        fetch(`/api/cases/?risk_level=HIGH&limit=50`, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}`, 'Content-Type': 'application/json' }
        })
      ]);
      setMetrics(metricsData);
      if (casesRes.ok) { const d = await casesRes.json(); setHighRiskCases(d.cases || []); }
      setLastRefresh(new Date());
    } catch (err) { setError(err.message || 'Failed to load'); } finally { setLoading(false); }
  };

  const handlePdfUpload = useCallback(async () => {
    if (!pdfFile) return;
    setPdfUploading(true); setPdfError(null); setPdfResult(null);
    try {
      const fd = new FormData(); fd.append('file', pdfFile);
      const token = localStorage.getItem('access_token');
      const res = await fetch('/api/cases/upload-pdf', {
        method: 'POST', headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) }, body: fd
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed');
      setPdfResult(data); fetchDashboardData();
      if (data.primaryid) {
        setTimeout(() => navigate(`/cases/${data.primaryid}`), 1500);
      }
    } catch (e) { setPdfError(e.message); } finally { setPdfUploading(false); }
  }, [pdfFile, navigate]);

  if (loading) return (
    <div className="min-h-screen bg-[#F7F8FA] flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-10 w-10 border-2 border-gray-300 border-t-[#2563EB] mx-auto" />
        <p className="mt-3 text-sm text-gray-500">Loading operations data...</p>
      </div>
    </div>
  );
  if (error) return (
    <div className="min-h-screen bg-[#F7F8FA] flex items-center justify-center">
      <div className="max-w-md w-full bg-white rounded-lg border border-gray-200 p-6 text-center">
        <p className="text-red-600 text-sm font-medium mb-4">{error}</p>
        <button onClick={fetchDashboardData} className="px-4 py-2 bg-[#2563EB] text-white rounded text-sm hover:bg-blue-700">Retry</button>
      </div>
    </div>
  );

  const m = metrics;

  const statusBadge = (s) => {
    const map = { 'INITIAL_RECEIVED': 'bg-blue-50 text-blue-700 border-blue-200', 'PENDING_FOLLOWUP': 'bg-amber-50 text-amber-700 border-amber-200',
      'FOLLOWUP_RECEIVED': 'bg-emerald-50 text-emerald-700 border-emerald-200', 'ESCALATED': 'bg-red-50 text-red-700 border-red-200',
      'COMPLETE': 'bg-gray-50 text-gray-600 border-gray-200', 'FOLLOWUP_DECLINED': 'bg-orange-50 text-orange-700 border-orange-200' };
    const label = { 'INITIAL_RECEIVED': 'New', 'PENDING_FOLLOWUP': 'Follow-Up', 'FOLLOWUP_RECEIVED': 'Responded',
      'ESCALATED': 'Escalated', 'COMPLETE': 'Complete', 'FOLLOWUP_DECLINED': 'Declined' };
    return <span className={`px-1.5 py-0.5 rounded text-[9px] font-semibold border ${map[s] || 'bg-gray-50 text-gray-600 border-gray-200'}`}>{label[s] || s}</span>;
  };

  return (
    <div className="min-h-screen bg-[#F7F8FA]">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-[1400px] mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-gray-900">Safety Operations Dashboard</h1>
            <p className="text-xs text-gray-400 mt-0.5">SmartFU Pharmacovigilance Platform</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[10px] text-gray-400">Updated {lastRefresh.toLocaleTimeString()}</span>
            <button onClick={fetchDashboardData} className="px-3 py-1.5 border border-gray-200 rounded text-xs text-gray-600 hover:bg-gray-50">Refresh</button>
            <button onClick={() => navigate('/case-analysis')} className="px-3 py-1.5 bg-[#2563EB] text-white rounded text-xs font-medium hover:bg-blue-700">Open Case Repository</button>
          </div>
        </div>
      </div>

      <div className="max-w-[1400px] mx-auto px-6 py-5 space-y-5">

        {/* KPI Strip */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          <KpiCard label="Total Cases" value={m.total_cases} sub="All time" indicator={m.total_cases > 0 ? 'neutral' : 'none'} />
          <KpiCard label="PDF Uploads" value={m.pdf_uploads ?? 0} sub={`${m.total_cases ? Math.round(((m.pdf_uploads || 0) / m.total_cases) * 100) : 0}% of intake`} indicator="info" />
          <KpiCard label="Serious Cases" value={m.serious_cases ?? m.high_risk_cases} sub={`${m.total_cases ? Math.round((m.high_risk_cases / m.total_cases) * 100) : 0}% of total`} indicator="danger" />
          <KpiCard label="Open Follow-Ups" value={m.pending_followups} sub="Pending action" indicator={m.pending_followups > 0 ? 'warning' : 'success'} />
          <KpiCard label="Escalated" value={m.escalated_cases ?? 0} sub="Requires review" indicator={m.escalated_cases > 0 ? 'danger' : 'success'} />
        </div>

        {/* Status + Completeness */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-gray-900">Case Status Overview</h3>
                <p className="text-[10px] text-gray-400 mt-0.5">Distribution by processing stage</p>
              </div>
              <button onClick={() => navigate('/case-analysis')} className="text-[10px] text-[#2563EB] hover:underline font-medium">View All</button>
            </div>
            <div className="flex items-center gap-5">
              <MiniDonut data={m.status_distribution || []} size={130} />
              <div className="space-y-1.5 flex-1">
                {(m.status_distribution || []).map(d => (
                  <div key={d.name} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ backgroundColor: d.color }} />
                      <span className="text-gray-600">{d.name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-gray-800 tabular-nums">{d.value.toLocaleString()}</span>
                      <span className="text-[10px] text-gray-400 w-8 text-right">{Math.round(d.value / (m.total_cases || 1) * 100)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <button onClick={() => navigate('/case-analysis')} className="mt-4 w-full py-2 bg-[#2563EB] text-white rounded text-xs font-medium hover:bg-blue-700">View All Cases</button>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-gray-900">Data Completeness</h3>
                <p className="text-[10px] text-gray-400 mt-0.5">Case data quality distribution</p>
              </div>
              <button onClick={() => navigate('/case-analysis')} className="text-[10px] text-[#2563EB] hover:underline font-medium">Details</button>
            </div>
            <div className="grid grid-cols-3 gap-2 mb-3">
              <div className="bg-gray-50 rounded p-2.5 border border-gray-100">
                <p className="text-[9px] text-gray-400 uppercase tracking-wider font-medium">Total</p>
                <p className="text-lg font-bold text-gray-900 mt-0.5">{m.total_cases?.toLocaleString()}</p>
              </div>
              <div className="bg-gray-50 rounded p-2.5 border border-gray-100">
                <p className="text-[9px] text-gray-400 uppercase tracking-wider font-medium">Emerging Signals</p>
                <p className="text-lg font-bold text-gray-900 mt-0.5">{(m.emerging_signals ?? 0).toLocaleString()}</p>
              </div>
              <div className="bg-gray-50 rounded p-2.5 border border-gray-100">
                <p className="text-[9px] text-gray-400 uppercase tracking-wider font-medium">Reporter Mix</p>
                <div className="flex gap-2 mt-1">
                  {Object.entries(m.reporter_breakdown || {}).map(([k, v]) => (
                    <span key={k} className="text-[10px]"><span className="font-semibold text-gray-700">{k}:</span> <span className="text-gray-500">{v.toLocaleString()}</span></span>
                  ))}
                </div>
              </div>
            </div>
            {(m.completeness_distribution && m.completeness_distribution.length > 0) ? (
              <ResponsiveContainer width="100%" height={140}>
                <BarChart data={m.completeness_distribution}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                  <XAxis dataKey="range" tick={{ fontSize: 10, fill: '#9CA3AF' }} axisLine={{ stroke: '#E5E7EB' }} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 9, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ fontSize: 11, borderRadius: 4, border: '1px solid #E5E7EB' }} />
                  <Bar dataKey="count" radius={[3,3,0,0]}>
                    {m.completeness_distribution.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <div className="h-36 flex items-center justify-center text-gray-400 text-xs">No data</div>}
          </div>
        </div>

        {/* PDF Intake + Signals */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-900">Case Intake - PDF Upload</h3>
              <span className="text-[10px] text-gray-400">{m.pdf_uploads ?? 0} uploaded</span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2.5">
                <input type="file" accept=".pdf"
                  onChange={(e) => { setPdfFile(e.target.files[0]); setPdfResult(null); setPdfError(null); }}
                  className="block w-full text-[10px] text-gray-500 file:mr-2 file:py-1.5 file:px-3 file:rounded file:border file:border-gray-200 file:bg-gray-50 file:text-gray-700 file:text-[10px] file:font-medium hover:file:bg-gray-100 file:cursor-pointer" />
                <button onClick={handlePdfUpload} disabled={!pdfFile || pdfUploading}
                  className="w-full px-3 py-2 bg-[#2563EB] text-white rounded text-xs font-medium hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed">
                  {pdfUploading ? 'Processing...' : 'Upload & Create Case'}
                </button>
                <p className="text-[9px] text-gray-400">Supports CIOMS, structured, and free-text PDF reports</p>
              </div>
              <div>
                {pdfError && <p className="text-red-600 text-[10px] bg-red-50 border border-red-200 rounded p-2">{pdfError}</p>}
                {pdfResult ? (
                  <div className="bg-emerald-50 border border-emerald-200 rounded p-3 text-[10px] space-y-1">
                    <div className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      <span className="font-semibold text-emerald-800">Case Created</span>
                    </div>
                    <p><span className="text-gray-500">ID:</span> <span className="font-mono font-medium text-gray-800">{pdfResult.primaryid}</span></p>
                    <p><span className="text-gray-500">Template:</span> {pdfResult.template_detected}</p>
                    <p><span className="text-gray-500">Confidence:</span> {pdfResult.extraction_confidence != null ? `${(pdfResult.extraction_confidence * 100).toFixed(0)}%` : '—'}</p>
                    <p className="text-[#2563EB]">Redirecting to analysis...</p>
                    <button onClick={() => navigate(`/cases/${pdfResult.primaryid}`)}
                      className="mt-1 w-full px-2 py-1 bg-[#2563EB] text-white rounded text-[9px] hover:bg-blue-700 font-medium">Open Case</button>
                  </div>
                ) : (
                  <div className="h-full flex items-center justify-center text-gray-300 text-[10px] border border-dashed border-gray-200 rounded">Upload a PDF to create a case</div>
                )}
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-semibold text-gray-900">Severity Monitor</h3>
                <p className="text-[10px] text-gray-400 mt-0.5">Active risk trend surveillance</p>
              </div>
              <button onClick={() => navigate('/signals')} className="text-[10px] text-[#2563EB] hover:underline font-medium">Open Console</button>
            </div>
            <div className="flex gap-3 mb-3">
              <SignalStat label="Active" value={m.active_signals ?? 0} color="text-amber-600" bg="bg-amber-50 border-amber-100" />
              <SignalStat label="High PRR" value={m.strong_signals ?? 0} color="text-red-600" bg="bg-red-50 border-red-100" />
              <SignalStat label="Emerging" value={m.emerging_signals ?? 0} color="text-blue-600" bg="bg-blue-50 border-blue-100" />
            </div>
            <div className="divide-y divide-gray-100 max-h-[160px] overflow-y-auto">
              {(m.top_signals || []).length > 0 ? m.top_signals.map((s, i) => (
                <div key={i} className="py-2 flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-800 truncate">{s.drug_name}</p>
                    <p className="text-[10px] text-gray-400 truncate">{s.adverse_event}</p>
                  </div>
                  <div className="text-right ml-3 flex-shrink-0">
                    <span className={`text-[10px] font-bold tabular-nums ${s.signal_strength === 'STRONG' ? 'text-red-600' : 'text-amber-600'}`}>
                      PRR {s.prr}
                    </span>
                    <p className="text-[9px] text-gray-400">{s.case_count} cases</p>
                  </div>
                </div>
              )) : <p className="py-6 text-center text-gray-400 text-xs">No active signals</p>}
            </div>
            <button onClick={() => navigate('/signals')} className="mt-2 w-full py-2 border border-gray-200 text-gray-600 rounded text-xs font-medium hover:bg-gray-50">Open Severity Console</button>
          </div>
        </div>

        {/* Document Repository */}
        <RepoDocumentsBlock />

        {/* Severity + Recent Cases */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-semibold text-gray-900">Seriousness Breakdown</h3>
                <p className="text-[10px] text-gray-400 mt-0.5">Case severity distribution</p>
              </div>
              <button onClick={() => navigate('/case-analysis')} className="text-[10px] text-[#2563EB] hover:underline font-medium">View Cases</button>
            </div>
            <div className="flex items-center gap-5">
              <MiniDonut data={m.severity_distribution || []} size={130} />
              <div className="space-y-1.5 flex-1">
                {(m.severity_distribution || []).map(d => (
                  <div key={d.name} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ backgroundColor: d.color }} />
                      <span className="text-gray-600">{d.name}</span>
                    </div>
                    <span className="font-semibold text-gray-800 tabular-nums">{d.value.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-900">Recent High-Risk Cases</h3>
              <button onClick={() => navigate('/case-analysis')} className="text-[10px] text-[#2563EB] hover:underline font-medium">View All</button>
            </div>
            <div className="divide-y divide-gray-100 max-h-[240px] overflow-y-auto">
              {(m.recent_cases || highRiskCases.slice(0, 5)).map((c) => (
                <div key={c.primaryid} className="py-2 flex items-center justify-between gap-3 cursor-pointer hover:bg-gray-50 -mx-2 px-2 rounded transition-colors"
                  onClick={() => navigate(`/cases/${c.primaryid}`)}>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${(c.seriousness_score ?? 0) >= 70 ? 'bg-red-500' : (c.seriousness_score ?? 0) >= 40 ? 'bg-amber-400' : 'bg-emerald-500'}`} />
                      <span className="text-xs font-medium text-gray-800">Case {c.primaryid}</span>
                      {statusBadge(c.case_status)}
                      {c.intake_source === 'PDF' && <span className="px-1 py-0.5 rounded text-[8px] font-bold bg-purple-50 text-purple-600 border border-purple-200">PDF</span>}
                    </div>
                    <p className="text-[10px] text-gray-400 mt-0.5 truncate ml-3.5">{c.drug_name || c.suspect_drug || 'N/A'} — {c.adverse_event || 'N/A'}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-[10px] font-semibold text-gray-700 tabular-nums">{c.completeness_score ?? Math.round((c.data_completeness_score || 0) * 100)}%</p>
                    <p className="text-[9px] text-gray-400">{c.channel || c.reporter_type || ''}</p>
                  </div>
                </div>
              ))}
              {(!m.recent_cases?.length && !highRiskCases.length) && <p className="py-6 text-center text-gray-400 text-xs">No cases</p>}
            </div>
          </div>
        </div>

        {/* Before/After + Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-sm font-semibold text-gray-900">Completeness: Before vs After</h3>
              <button onClick={() => navigate('/lifecycle')} className="text-[10px] text-[#2563EB] hover:underline font-medium">Lifecycle Report</button>
            </div>
            <p className="text-[10px] text-gray-400 mb-3">Avg Before: {m.completeness_before_avg ?? 0}% | After: {m.completeness_after_avg ?? 0}%</p>
            {(m.completeness_chart?.length > 0) ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={m.completeness_chart} barGap={4}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                  <XAxis dataKey="range" tick={{ fontSize: 9, fill: '#9CA3AF' }} axisLine={{ stroke: '#E5E7EB' }} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 9, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ fontSize: 11, borderRadius: 4, border: '1px solid #E5E7EB' }} />
                  <Legend wrapperStyle={{ fontSize: 10 }} />
                  <Bar dataKey="before" name="Before" fill="#ef4444" radius={[3,3,0,0]} />
                  <Bar dataKey="after" name="After" fill="#10b981" radius={[3,3,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <div className="h-48 flex items-center justify-center text-gray-400 text-xs">No data — analyze cases first</div>}
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-900">Recent Activity</h3>
              <button onClick={() => navigate('/case-analysis')} className="text-[10px] text-[#2563EB] hover:underline font-medium">View All</button>
            </div>
            <div className="divide-y divide-gray-100 max-h-[200px] overflow-y-auto">
              {(m.recent_cases || []).slice(0, 6).map((c) => (
                <div key={c.primaryid} className="py-2 flex items-center justify-between cursor-pointer hover:bg-gray-50 -mx-2 px-2 rounded transition-colors"
                  onClick={() => navigate(`/cases/${c.primaryid}`)}>
                  <div className="flex items-center gap-2.5 min-w-0 flex-1">
                    <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${(c.seriousness_score || 0) >= 70 ? 'bg-red-500' : (c.seriousness_score || 0) >= 40 ? 'bg-amber-400' : 'bg-emerald-500'}`} />
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-gray-800 truncate">Case {c.primaryid} — {c.drug_name || 'N/A'}</p>
                      <p className="text-[9px] text-gray-400">{c.created_at ? new Date(c.created_at).toLocaleDateString() : ''} · {c.reporter_type || ''}</p>
                    </div>
                  </div>
                  <span className="text-[10px] text-[#2563EB] hover:underline flex-shrink-0 font-medium">View</span>
                </div>
              ))}
              {!m.recent_cases?.length && <p className="py-6 text-center text-gray-400 text-xs">No recent activity</p>}
            </div>
          </div>
        </div>

        {/* Status Bar */}
        <div className="bg-white border border-gray-200 rounded-lg px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-xs font-medium text-gray-700">System Operational</span>
            <span className="text-[10px] text-gray-400">All AI agents active · Data pipeline running</span>
          </div>
          <span className="text-[10px] text-gray-400">Last sync: {lastRefresh.toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
};

const KpiCard = ({ label, value, sub, indicator }) => {
  const dotColor = {
    danger: 'bg-red-500',
    warning: 'bg-amber-400',
    success: 'bg-emerald-500',
    info: 'bg-blue-500',
    neutral: 'bg-gray-400',
    none: 'bg-transparent',
  }[indicator] || 'bg-gray-300';

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-1.5">
        <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
        <span className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">{label}</span>
      </div>
      <p className="text-2xl font-bold text-gray-900 tabular-nums">{(value ?? 0).toLocaleString()}</p>
      <p className="text-[10px] text-gray-400 mt-0.5">{sub}</p>
    </div>
  );
};

const SignalStat = ({ label, value, color, bg }) => (
  <div className={`flex-1 rounded px-3 py-2 border ${bg}`}>
    <p className="text-[9px] text-gray-500 font-medium">{label}</p>
    <p className={`text-lg font-bold ${color}`}>{value}</p>
  </div>
);

export default Dashboard;
