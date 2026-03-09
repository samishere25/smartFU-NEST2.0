import React from 'react';

const ResponsePredictionCard = ({ analysis }) => {
  if (!analysis) {
    return null;
  }

  const responseProbability = analysis.response_probability || 0;
  const responsePercentage = (responseProbability * 100).toFixed(0);
  const reporterType = analysis.case_data?.reporter_type || 'UNKNOWN';
  const missingFieldsCount = analysis.missing_fields?.length || 0;
  
  // Color logic for response probability
  const getProbabilityColor = (probability) => {
    if (probability < 0.4) return 'red';
    if (probability < 0.7) return 'yellow';
    return 'green';
  };

  const color = getProbabilityColor(responseProbability);
  
  const colorClasses = {
    red: {
      bg: 'bg-red-500',
      text: 'text-red-700',
      border: 'border-red-200',
      lightBg: 'bg-red-50'
    },
    yellow: {
      bg: 'bg-yellow-500',
      text: 'text-yellow-700',
      border: 'border-yellow-200',
      lightBg: 'bg-yellow-50'
    },
    green: {
      bg: 'bg-green-500',
      text: 'text-green-700',
      border: 'border-green-200',
      lightBg: 'bg-green-50'
    }
  };

  // Reporter type mapping
  const reporterTypeLabels = {
    'HP': 'Healthcare Professional',
    'MD': 'Physician',
    'PH': 'Pharmacist',
    'OT': 'Other Healthcare',
    'LW': 'Lawyer',
    'CN': 'Consumer',
    'Unknown': 'Unknown Reporter'
  };

  const reporterLabel = reporterTypeLabels[reporterType] || reporterType;

  // Generate explanation text
  const getExplanationText = () => {
    const parts = [];
    
    // Reporter type impact
    if (reporterType === 'HP' || reporterType === 'MD' || reporterType === 'PH') {
      parts.push(`${reporterLabel} reporters typically respond to follow-ups`);
    } else if (reporterType === 'CN') {
      parts.push(`Consumer reporters have lower response rates`);
    } else {
      parts.push(`${reporterLabel} has moderate engagement likelihood`);
    }

    // Missing fields impact
    if (missingFieldsCount === 0) {
      parts.push('complete data suggests high engagement');
    } else if (missingFieldsCount <= 2) {
      parts.push(`${missingFieldsCount} missing field${missingFieldsCount > 1 ? 's' : ''} detected`);
    } else {
      parts.push(`${missingFieldsCount} missing fields may reduce response likelihood`);
    }

    // Criticality analysis
    const criticalFields = analysis.missing_fields?.filter(f => 
      f.criticality === 'HIGH' || f.criticality === 'CRITICAL'
    ) || [];
    
    if (criticalFields.length > 0) {
      parts.push(`${criticalFields.length} critical field${criticalFields.length > 1 ? 's' : ''} missing`);
    }

    return parts.join(', ') + '.';
  };

  // Decision impact based on threshold
  const willFollowUp = responseProbability >= 0.5;
  const decisionImpact = willFollowUp
    ? 'AI considers follow-up worthwhile'
    : 'AI will avoid immediate follow-up to reduce fatigue';

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            🧠 Human Response Prediction
          </h3>
          <span className="text-xs text-gray-500 font-medium">Feature 2</span>
        </div>
        <p className="text-sm text-gray-600 mt-1">
          AI predicts human behavior and adapts follow-up strategy
        </p>
      </div>

      <div className="p-6 space-y-6">
        {/* Response Probability Card */}
        <div className={`rounded-lg border-2 ${colorClasses[color].border} ${colorClasses[color].lightBg} p-5`}>
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold text-gray-700">Response Probability</h4>
            <span className={`text-3xl font-bold ${colorClasses[color].text}`}>
              {responsePercentage}%
            </span>
          </div>
          
          {/* Progress Bar */}
          <div className="relative">
            <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
              <div
                className={`h-4 ${colorClasses[color].bg} transition-all duration-500 ease-out rounded-full flex items-center justify-end pr-2`}
                style={{ width: `${responsePercentage}%` }}
              >
                {responseProbability >= 0.15 && (
                  <span className="text-xs font-bold text-white">
                    {responsePercentage}%
                  </span>
                )}
              </div>
            </div>
            
            {/* Threshold marker at 50% */}
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 h-4 w-0.5 bg-gray-400 opacity-50"></div>
          </div>
          
          <div className="flex justify-between mt-2 text-xs text-gray-500">
            <span>Low Response</span>
            <span className="font-medium">50% Threshold</span>
            <span>High Response</span>
          </div>
        </div>

        {/* Explainable AI Section */}
        <div className="bg-gray-50 rounded-lg p-5 border border-gray-200">
          <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
            <svg className="w-5 h-5 mr-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            Why This Prediction?
          </h4>
          
          <div className="space-y-3">
            {/* Reporter Type */}
            <div className="flex items-start">
              <div className="flex-shrink-0 w-2 h-2 mt-1.5 rounded-full bg-blue-500"></div>
              <div className="ml-3">
                <p className="text-sm text-gray-700">
                  <span className="font-semibold">Reporter Type:</span> {reporterLabel}
                </p>
              </div>
            </div>

            {/* Missing Fields & Completeness Score */}
            <div className="flex items-start">
              <div className="flex-shrink-0 w-2 h-2 mt-1.5 rounded-full bg-blue-500"></div>
              <div className="ml-3">
                <p className="text-sm text-gray-700">
                  <span className="font-semibold">Data Completeness:</span>{' '}
                  {analysis.completeness_score !== undefined ? (
                    <span className={analysis.completeness_score >= 0.8 ? 'text-green-600' : analysis.completeness_score >= 0.5 ? 'text-yellow-600' : 'text-red-600'}>
                      {Math.round(analysis.completeness_score * 100)}% ({missingFieldsCount} field{missingFieldsCount !== 1 ? 's' : ''} missing)
                    </span>
                  ) : missingFieldsCount === 0 ? (
                    <span className="text-green-600">All fields complete</span>
                  ) : (
                    <span className={missingFieldsCount > 3 ? 'text-red-600' : 'text-yellow-600'}>
                      {missingFieldsCount} field{missingFieldsCount > 1 ? 's' : ''} missing
                    </span>
                  )}
                </p>
              </div>
            </div>

            {/* Critical Fields */}
            {analysis.missing_fields && analysis.missing_fields.length > 0 && (
              <div className="flex items-start">
                <div className="flex-shrink-0 w-2 h-2 mt-1.5 rounded-full bg-blue-500"></div>
                <div className="ml-3">
                  <p className="text-sm text-gray-700 mb-2">
                    <span className="font-semibold">Missing Critical Fields:</span>
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {analysis.missing_fields.map((field, idx) => (
                      <span
                        key={idx}
                        className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                          field.criticality === 'CRITICAL' || field.criticality === 'HIGH'
                            ? 'bg-red-100 text-red-800'
                            : field.criticality === 'MEDIUM'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {field.field_name || field.field}
                        {field.criticality && (
                          <span className="ml-1 opacity-75">
                            ({field.criticality})
                          </span>
                        )}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Summary Explanation */}
            <div className="mt-4 pt-3 border-t border-gray-200">
              <p className="text-sm text-gray-600 italic">
                {getExplanationText()}
              </p>
            </div>
          </div>
        </div>

        {/* Decision Impact Badge */}
        <div className={`rounded-lg p-4 border-l-4 ${
          willFollowUp 
            ? 'bg-blue-50 border-blue-500' 
            : 'bg-orange-50 border-orange-500'
        }`}>
          <div className="flex items-start">
            <div className="flex-shrink-0">
              {willFollowUp ? (
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              ) : (
                <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              )}
            </div>
            <div className="ml-3">
              <h5 className={`text-sm font-semibold ${
                willFollowUp ? 'text-blue-900' : 'text-orange-900'
              }`}>
                AI Follow-Up Strategy
              </h5>
              <p className={`text-sm mt-1 ${
                willFollowUp ? 'text-blue-700' : 'text-orange-700'
              }`}>
                {decisionImpact}
              </p>
              
              {!willFollowUp && (
                <p className="text-xs text-orange-600 mt-2">
                  💡 Respecting human workload — prevents spam follow-ups
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Confidence Note */}
        <div className="text-center pt-2 border-t border-gray-100">
          <p className="text-xs text-gray-500">
            Prediction based on historical reporter behavior patterns and data quality metrics
          </p>
        </div>
      </div>
    </div>
  );
};

export default ResponsePredictionCard;
