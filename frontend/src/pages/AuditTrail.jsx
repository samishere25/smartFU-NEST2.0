import React, { useState, useEffect, useMemo } from 'react';
import { api } from '../utils/api';

const ACTOR_COLORS = {
  AI: 'bg-purple-100 text-purple-700',
  HUMAN: 'bg-blue-100 text-blue-700',
  SYSTEM: 'bg-gray-100 text-gray-600',
  REPORTER: 'bg-emerald-100 text-emerald-700',
};

const ACTION_ICONS = {
  CASE_CREATED: { icon: '+', color: 'bg-emerald-500' },
  CIOMS_PARSED: { icon: 'D', color: 'bg-indigo-500' },
  FIELDS_EXTRACTED: { icon: 'F', color: 'bg-indigo-400' },
  AI_RISK_DECISION: { icon: 'R', color: 'bg-purple-500' },
  AI_FOLLOWUP_DECISION: { icon: 'Q', color: 'bg-purple-400' },
  HUMAN_OVERRIDE: { icon: 'O', color: 'bg-red-500' },
  FOLLOWUP_SENT: { icon: 'S', color: 'bg-amber-500' },
  RESPONSE_RECEIVED: { icon: 'R', color: 'bg-emerald-500' },
  REVIEWER_NOTE_ADDED: { icon: 'N', color: 'bg-blue-500' },
  REGULATORY_ESCALATION: { icon: 'E', color: 'bg-red-600' },
  SIGNAL_DETECTED: { icon: 'S', color: 'bg-orange-500' },
  SIGNAL_REVIEWED: { icon: 'V', color: 'bg-blue-500' },
  SIGNAL_PRIORITY_CHANGED: { icon: 'P', color: 'bg-amber-500' },
  SIGNAL_FALSE_POSITIVE: { icon: 'X', color: 'bg-gray-500' },
  LIFECYCLE_STAGE_CHANGE: { icon: 'L', color: 'bg-teal-500' },
  CASE_CLOSED: { icon: 'C', color: 'bg-gray-600' },
  REGULATORY_WORKFLOW_CREATED: { icon: 'W', color: 'bg-red-500' },
};

export default function AuditTrail() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [actionTypes, setActionTypes] = useState([]);
  const [filterAction, setFilterAction] = useState('');
  const [filterActor, setFilterActor] = useState('');
  const [search, setSearch] = useState('');
  const [caseSearch, setCaseSearch] = useState('');
  const [caseAudit, setCaseAudit] = useState(null);
  const [loadingCase, setLoadingCase] = useState(false);

  useEffect(() => {
    fetchAuditTrail();
    fetchActionTypes();
  }, [filterAction, filterActor]);

  const fetchAuditTrail = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await api.getAuditTrail(
        filterAction || null,
        filterActor || null,
        500,
        0
      );
      setData(result);
    } catch (err) {
      setError('Failed to load audit trail');
    } finally {
      setLoading(false);
    }
  };

  const fetchActionTypes = async () => {
    try {
      const result = await api.getAuditActionTypes();
      setActionTypes(result.action_types || []);
    } catch { /* ignore */ }
  };

  const handleCaseSearch = async () => {
    if (!caseSearch.trim()) return;
    try {
      setLoadingCase(true);
      const result = await api.getCaseAuditTrailPV(caseSearch.trim());
      setCaseAudit(result);
    } catch {
      setCaseAudit({ entries: [], error: 'Case not found or no audit entries' });
    } finally {
      setLoadingCase(false);
    }
  };

  // Filter by text search
  const filteredEntries = useMemo(() => {
    const entries = caseAudit ? (caseAudit.entries || []) : (data?.entries || []);
    if (!search.trim()) return entries;
    const q = search.toLowerCase();
    return entries.filter(e =>
      e.description?.toLowerCase().includes(q) ||
      e.action_type?.toLowerCase().includes(q) ||
      e.actor_type?.toLowerCase().includes(q) ||
      e.actor_id?.toLowerCase().includes(q)
    );
  }, [data, caseAudit, search]);

  const stats = data?.statistics || {};

  if (loading && !data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-2 border-gray-300 border-t-blue-600 mx-auto" />
          <p className="mt-3 text-sm text-gray-500">Loading audit trail...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-[1440px] mx-auto px-5 py-5 space-y-4">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">PV Audit Trail</h1>
            <p className="text-xs text-gray-500 mt-0.5">Immutable compliance logging — FDA 21 CFR Part 11 / EMA GVP / MHRA</p>
          </div>
          <button onClick={() => { setCaseAudit(null); fetchAuditTrail(); }} className="px-3 py-1.5 border border-gray-300 rounded text-xs text-gray-600 hover:bg-gray-50">
            Refresh
          </button>
        </div>

        {/* Stats Strip */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm px-5 py-3">
          <div className="flex items-center gap-6 flex-wrap text-xs">
            <div>
              <span className="text-gray-500">Total Entries</span>
              <span className="ml-2 font-bold text-gray-900">{stats.total_entries || 0}</span>
            </div>
            <div className="w-px h-5 bg-gray-200" />
            {Object.entries(stats.by_actor_type || {}).map(([actor, count]) => (
              <div key={actor} className="flex items-center gap-1.5">
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${ACTOR_COLORS[actor] || 'bg-gray-100 text-gray-600'}`}>{actor}</span>
                <span className="font-bold text-gray-800">{count}</span>
              </div>
            ))}
            {error && (
              <>
                <div className="w-px h-5 bg-gray-200" />
                <span className="text-amber-600">{error}</span>
              </>
            )}
          </div>
        </div>

        {/* Filters + Case Search */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
          {/* Filters */}
          <div className="lg:col-span-8 bg-white rounded-lg border border-gray-200 shadow-sm p-3">
            <div className="flex flex-wrap gap-2 items-end">
              <div className="flex-1 min-w-[160px]">
                <label className="block text-[10px] text-gray-500 mb-1">Action Type</label>
                <select value={filterAction} onChange={e => { setFilterAction(e.target.value); setCaseAudit(null); }}
                  className="w-full px-2 py-1.5 border border-gray-200 rounded text-xs bg-gray-50 focus:outline-none focus:ring-1 focus:ring-blue-500">
                  <option value="">All Actions</option>
                  {actionTypes.map(at => <option key={at} value={at}>{at.replace(/_/g, ' ')}</option>)}
                </select>
              </div>
              <div className="flex-1 min-w-[120px]">
                <label className="block text-[10px] text-gray-500 mb-1">Actor Type</label>
                <select value={filterActor} onChange={e => { setFilterActor(e.target.value); setCaseAudit(null); }}
                  className="w-full px-2 py-1.5 border border-gray-200 rounded text-xs bg-gray-50 focus:outline-none focus:ring-1 focus:ring-blue-500">
                  <option value="">All Actors</option>
                  <option value="AI">AI</option>
                  <option value="HUMAN">Human</option>
                  <option value="SYSTEM">System</option>
                  <option value="REPORTER">Reporter</option>
                </select>
              </div>
              <div className="flex-1 min-w-[180px]">
                <label className="block text-[10px] text-gray-500 mb-1">Search</label>
                <input type="text" placeholder="Search descriptions..." value={search} onChange={e => setSearch(e.target.value)}
                  className="w-full px-2 py-1.5 border border-gray-200 rounded text-xs bg-gray-50 focus:outline-none focus:ring-1 focus:ring-blue-500" />
              </div>
            </div>
          </div>

          {/* Case-specific search */}
          <div className="lg:col-span-4 bg-white rounded-lg border border-gray-200 shadow-sm p-3">
            <label className="block text-[10px] text-gray-500 mb-1">Case Audit Lookup</label>
            <div className="flex gap-2">
              <input type="text" placeholder="Case UUID or primaryid..." value={caseSearch}
                onChange={e => setCaseSearch(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleCaseSearch()}
                className="flex-1 px-2 py-1.5 border border-gray-200 rounded text-xs bg-gray-50 focus:outline-none focus:ring-1 focus:ring-blue-500" />
              <button onClick={handleCaseSearch} disabled={loadingCase}
                className="px-3 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50">
                {loadingCase ? '...' : 'Search'}
              </button>
            </div>
            {caseAudit && (
              <div className="mt-2 flex items-center justify-between">
                <span className="text-[10px] text-gray-500">
                  {caseAudit.error || `${caseAudit.entries?.length || 0} entries for case ${caseAudit.primaryid || caseAudit.case_id || ''}`}
                </span>
                <button onClick={() => setCaseAudit(null)} className="text-[10px] text-blue-600 hover:underline">Clear</button>
              </div>
            )}
          </div>
        </div>

        {/* Timeline */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-900">
              {caseAudit ? 'Case Audit Timeline' : 'System Audit Timeline'}
            </h2>
            <span className="text-[10px] text-gray-400">{filteredEntries.length} entries</span>
          </div>

          <div className="divide-y divide-gray-50 max-h-[600px] overflow-y-auto">
            {filteredEntries.length === 0 ? (
              <div className="py-16 text-center text-sm text-gray-400">
                {caseAudit?.error || 'No audit entries found for current filters'}
              </div>
            ) : (
              filteredEntries.map((entry) => (
                <AuditEntry key={entry.audit_id} entry={entry} />
              ))
            )}
          </div>
        </div>

        {/* Action Type Distribution */}
        {stats.by_action_type && Object.keys(stats.by_action_type).length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Action Distribution</h3>
            <div className="flex flex-wrap gap-2">
              {Object.entries(stats.by_action_type).sort((a, b) => b[1] - a[1]).map(([action, count]) => (
                <button key={action} onClick={() => { setFilterAction(action); setCaseAudit(null); }}
                  className="flex items-center gap-1.5 px-2 py-1 rounded border border-gray-200 hover:bg-gray-50 transition-colors">
                  <ActionIcon action={action} size="sm" />
                  <span className="text-[10px] text-gray-600">{action.replace(/_/g, ' ')}</span>
                  <span className="text-[10px] font-bold text-gray-800">{count}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg px-4 py-3 flex items-start gap-3">
          <span className="text-gray-400 text-sm mt-0.5">i</span>
          <div className="text-xs text-gray-500 leading-relaxed">
            <span className="font-medium text-gray-600">Compliance Note.</span>{' '}
            This audit trail is immutable and append-only. No entries can be modified or deleted.
            Every AI decision, human override, follow-up action, and signal event is permanently recorded
            for regulatory inspection readiness (FDA 21 CFR Part 11, EMA GVP Module VI, ICH E2B).
          </div>
        </div>
      </div>
    </div>
  );
}


/* ── Sub-components ── */

function AuditEntry({ entry }) {
  const [expanded, setExpanded] = useState(false);
  const ai = ACTION_ICONS[entry.action_type] || { icon: '?', color: 'bg-gray-400' };
  const actorColor = ACTOR_COLORS[entry.actor_type] || 'bg-gray-100 text-gray-600';
  const isOverride = entry.action_type === 'HUMAN_OVERRIDE';

  return (
    <div className={`px-4 py-3 hover:bg-gray-50/50 transition-colors cursor-pointer ${isOverride ? 'bg-red-50/30' : ''}`}
      onClick={() => setExpanded(!expanded)}>
      <div className="flex items-start gap-3">
        {/* Icon */}
        <ActionIcon action={entry.action_type} />

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-medium text-gray-900">{entry.description}</span>
            {isOverride && <span className="text-[9px] font-bold text-red-600 bg-red-100 px-1.5 py-0.5 rounded">OVERRIDE</span>}
          </div>
          <div className="flex items-center gap-3 mt-1 text-[10px] text-gray-400">
            <span className={`px-1.5 py-0.5 rounded font-semibold ${actorColor}`}>{entry.actor_type}</span>
            {entry.actor_id && <span>by {entry.actor_id.substring(0, 12)}</span>}
            {entry.channel && <span className="text-blue-500">{entry.channel}</span>}
            {entry.confidence_score != null && (
              <span>Confidence: {(entry.confidence_score * 100).toFixed(0)}%</span>
            )}
            {entry.model_version && <span className="text-purple-500">{entry.model_version}</span>}
            {entry.case_id && <span className="font-mono text-gray-400">Case: {entry.case_id.substring(0, 8)}</span>}
            {entry.signal_id && <span className="font-mono text-orange-400">Signal: {entry.signal_id.substring(0, 8)}</span>}
          </div>
        </div>

        {/* Timestamp */}
        <div className="text-right shrink-0">
          <p className="text-[10px] text-gray-500">{new Date(entry.timestamp).toLocaleDateString()}</p>
          <p className="text-[10px] text-gray-400">{new Date(entry.timestamp).toLocaleTimeString()}</p>
          {entry.regulatory_impact && <span className="text-[9px] text-red-500 font-medium">REG</span>}
        </div>
      </div>

      {/* Expanded metadata */}
      {expanded && (
        <div className="mt-3 ml-9 space-y-2">
          {entry.previous_value && (
            <div className="bg-red-50 rounded px-3 py-2">
              <p className="text-[10px] font-semibold text-red-600 mb-1">Previous Value</p>
              <pre className="text-[10px] text-red-800 whitespace-pre-wrap overflow-x-auto">{JSON.stringify(entry.previous_value, null, 2)}</pre>
            </div>
          )}
          {entry.new_value && (
            <div className="bg-emerald-50 rounded px-3 py-2">
              <p className="text-[10px] font-semibold text-emerald-600 mb-1">New Value</p>
              <pre className="text-[10px] text-emerald-800 whitespace-pre-wrap overflow-x-auto">{JSON.stringify(entry.new_value, null, 2)}</pre>
            </div>
          )}
          {entry.decision_metadata && (
            <div className="bg-purple-50 rounded px-3 py-2">
              <p className="text-[10px] font-semibold text-purple-600 mb-1">Decision Metadata</p>
              <pre className="text-[10px] text-purple-800 whitespace-pre-wrap overflow-x-auto">{JSON.stringify(entry.decision_metadata, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ActionIcon({ action, size = 'md' }) {
  const ai = ACTION_ICONS[action] || { icon: '?', color: 'bg-gray-400' };
  const sizeClass = size === 'sm' ? 'w-4 h-4 text-[8px]' : 'w-6 h-6 text-[10px]';
  return (
    <span className={`${sizeClass} rounded-full ${ai.color} text-white flex items-center justify-center font-bold shrink-0`}>
      {ai.icon}
    </span>
  );
}
