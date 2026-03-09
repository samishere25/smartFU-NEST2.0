import React, { useState } from 'react';

const fieldGroups = [
  {
    title: 'Patient Information',
    icon: (
      <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    ),
    fields: [
      { key: 'patient_initials', label: 'Patient Initials' },
      { key: 'patient_age', label: 'Age' },
      { key: 'patient_sex', label: 'Sex' },
      { key: 'medical_history', label: 'Medical History' },
    ],
  },
  {
    title: 'Drug Information',
    icon: (
      <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
      </svg>
    ),
    fields: [
      { key: 'suspect_drug', label: 'Suspect Drug' },
      { key: 'drug_dose', label: 'Dose' },
      { key: 'drug_route', label: 'Route' },
      { key: 'indication', label: 'Indication' },
      { key: 'concomitant_drugs', label: 'Concomitant Drugs' },
    ],
  },
  {
    title: 'Therapy Timeline',
    icon: (
      <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    fields: [
      { key: 'therapy_start', label: 'Therapy Start', isDate: true },
      { key: 'therapy_end', label: 'Therapy End', isDate: true },
      { key: 'therapy_duration', label: 'Duration (days)' },
      { key: 'dechallenge', label: 'Dechallenge' },
      { key: 'rechallenge', label: 'Rechallenge' },
    ],
  },
  {
    title: 'Event Details',
    icon: (
      <svg className="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
      </svg>
    ),
    fields: [
      { key: 'adverse_event', label: 'Adverse Event' },
      { key: 'event_date', label: 'Event Date', isDate: true },
      { key: 'event_outcome', label: 'Outcome' },
    ],
  },
  {
    title: 'Reporter & Administrative',
    icon: (
      <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    fields: [
      { key: 'reporter_type', label: 'Reporter Type' },
      { key: 'reporter_email', label: 'Reporter Email' },
      { key: 'reporter_phone', label: 'Reporter Phone' },
      { key: 'report_type', label: 'Report Type' },
      { key: 'manufacturer_name', label: 'Manufacturer' },
      { key: 'reporter_country', label: 'Country' },
    ],
  },
];

const formatValue = (value, isDate) => {
  if (value == null || value === '' || value === 'MISSING' || value === 'UNK') return null;
  if (isDate && value) {
    try {
      const d = new Date(value);
      if (!isNaN(d.getTime())) return d.toLocaleDateString();
    } catch { /* ignore */ }
  }
  return String(value);
};

const CiomsDetailsSection = ({ caseData = {} }) => {
  const [expanded, setExpanded] = useState(true);

  // Count how many CIOMS-specific fields have values
  const allFieldKeys = fieldGroups.flatMap(g => g.fields.map(f => f.key));
  const filledCount = allFieldKeys.filter(k => {
    const v = caseData[k];
    return v != null && v !== '' && v !== 'MISSING' && v !== 'UNK';
  }).length;

  if (filledCount === 0) return null;

  return (
    <div className="bg-white rounded-xl border shadow-sm">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-5 text-left"
      >
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-purple-50 flex items-center justify-center">
            <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900">CIOMS Form-I Details</h3>
            <p className="text-xs text-gray-500 mt-0.5">{filledCount} of {allFieldKeys.length} fields extracted</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex px-2 py-0.5 rounded-full text-[10px] font-semibold bg-purple-50 text-purple-700 ring-1 ring-purple-600/20">
            CIOMS
          </span>
          <svg className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {expanded && (
        <div className="px-5 pb-5">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {fieldGroups.map((group) => {
              // Only show groups that have at least one filled field
              const hasData = group.fields.some(f => {
                const v = formatValue(caseData[f.key], f.isDate);
                return v !== null;
              });

              return (
                <div key={group.title} className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-6 h-6 rounded-md bg-white flex items-center justify-center shadow-sm">
                      {group.icon}
                    </div>
                    <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">{group.title}</h4>
                  </div>
                  <div className="space-y-2">
                    {group.fields.map((field) => {
                      const value = formatValue(caseData[field.key], field.isDate);
                      return (
                        <div key={field.key} className="flex items-start justify-between gap-2">
                          <span className="text-xs text-gray-500 flex-shrink-0">{field.label}</span>
                          {value ? (
                            <span className="text-xs font-medium text-gray-900 text-right max-w-[60%] break-words">{value}</span>
                          ) : (
                            <span className="text-xs text-gray-300 italic">Not provided</span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default CiomsDetailsSection;
