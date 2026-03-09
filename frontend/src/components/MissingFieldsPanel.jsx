import React, { useState } from 'react';

const criticalityConfig = {
  CRITICAL: { bg: 'bg-red-50', text: 'text-red-700', ring: 'ring-red-600/20', dot: 'bg-red-500', label: 'Critical' },
  HIGH:     { bg: 'bg-amber-50', text: 'text-amber-700', ring: 'ring-amber-600/20', dot: 'bg-amber-500', label: 'High' },
  MEDIUM:   { bg: 'bg-blue-50', text: 'text-blue-700', ring: 'ring-blue-600/20', dot: 'bg-blue-500', label: 'Medium' },
  LOW:      { bg: 'bg-gray-50', text: 'text-gray-600', ring: 'ring-gray-300/50', dot: 'bg-gray-400', label: 'Low' },
};

const MissingFieldsPanel = ({ missingFields = [], completenessScore, totalExtracted }) => {
  const [expanded, setExpanded] = useState(true);

  if (!missingFields || missingFields.length === 0) {
    return (
      <div className="bg-white rounded-xl border shadow-sm p-5">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-7 h-7 rounded-lg bg-emerald-50 flex items-center justify-center">
            <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="text-sm font-semibold text-gray-900">Data Completeness</h3>
        </div>
        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3">
          <p className="text-sm text-emerald-800 font-medium">All required fields extracted successfully</p>
          {totalExtracted != null && (
            <p className="text-xs text-emerald-600 mt-1">{totalExtracted} fields extracted from PDF</p>
          )}
        </div>
      </div>
    );
  }

  // Group by criticality
  const grouped = {};
  missingFields.forEach(f => {
    const key = f.criticality || f.safety_criticality || 'MEDIUM';
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(f);
  });

  const criticalCount = (grouped.CRITICAL || []).length;
  const highCount = (grouped.HIGH || []).length;

  return (
    <div className="bg-white rounded-xl border shadow-sm">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-5 text-left"
      >
        <div className="flex items-center gap-2">
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${
            criticalCount > 0 ? 'bg-red-50' : highCount > 0 ? 'bg-amber-50' : 'bg-blue-50'
          }`}>
            <svg className={`w-4 h-4 ${
              criticalCount > 0 ? 'text-red-600' : highCount > 0 ? 'text-amber-600' : 'text-blue-600'
            }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900">
              Missing Fields
              <span className="ml-2 text-xs font-normal text-gray-500">({missingFields.length})</span>
            </h3>
            {completenessScore != null && (
              <p className="text-xs text-gray-500 mt-0.5">Completeness: {Math.round(completenessScore * 100)}%</p>
            )}
          </div>
        </div>
        <svg className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="px-5 pb-5 space-y-4">
          {/* Completeness bar */}
          {completenessScore != null && (
            <div>
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-gray-500">CIOMS Completeness</span>
                <span className="font-semibold text-gray-900">{Math.round(completenessScore * 100)}%</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2">
                <div
                  className={`h-full rounded-full transition-all ${
                    completenessScore >= 0.8 ? 'bg-emerald-500' : completenessScore >= 0.6 ? 'bg-blue-500' : 'bg-red-400'
                  }`}
                  style={{ width: `${Math.round(completenessScore * 100)}%` }}
                />
              </div>
            </div>
          )}

          {/* Severity counts */}
          <div className="grid grid-cols-4 gap-2">
            {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(level => {
              const cfg = criticalityConfig[level];
              const count = (grouped[level] || []).length;
              return (
                <div key={level} className={`rounded-lg p-2 text-center ${cfg.bg}`}>
                  <p className={`text-lg font-bold ${cfg.text}`}>{count}</p>
                  <p className="text-[10px] uppercase tracking-wide opacity-70">{cfg.label}</p>
                </div>
              );
            })}
          </div>

          {/* Field list grouped by criticality */}
          {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(level => {
            const fields = grouped[level];
            if (!fields || fields.length === 0) return null;
            const cfg = criticalityConfig[level];

            return (
              <div key={level}>
                <p className={`text-[10px] font-semibold uppercase tracking-wider mb-2 ${cfg.text}`}>
                  {cfg.label} ({fields.length})
                </p>
                <div className="space-y-1.5">
                  {fields.map((f, i) => {
                    const fieldName = f.field_display || f.field_name || f.field || f;
                    const displayName = typeof fieldName === 'string'
                      ? fieldName.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
                      : String(fieldName);

                    return (
                      <div key={i} className="flex items-start gap-2 py-1.5 px-2 rounded-lg hover:bg-gray-50">
                        <span className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${cfg.dot}`} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-gray-800">{displayName}</p>
                          {f.safety_impact && (
                            <p className="text-[11px] text-gray-500 mt-0.5 leading-snug">{f.safety_impact}</p>
                          )}
                          {f.category && (
                            <span className="inline-flex text-[10px] text-gray-400 mt-0.5">{f.category}</span>
                          )}
                        </div>
                        <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-semibold ring-1 flex-shrink-0 ${cfg.bg} ${cfg.text} ${cfg.ring}`}>
                          {cfg.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default MissingFieldsPanel;
