import React from 'react';

/**
 * Safety Confidence Panel Component
 * Displays safety and completeness metrics
 * 
 * Displays:
 * - safety_confidence_score
 * - completeness_score
 * - closure_eligible (true/false)
 * - critical_fields_covered (if provided)
 */
const SafetyConfidencePanel = ({ lifecycle }) => {
  if (!lifecycle) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Safety & Confidence</h3>
        <p className="text-gray-500">No data available</p>
      </div>
    );
  }

  const safetyConfidence = lifecycle.safety_confidence_score ?? null;
  const completeness = lifecycle.completeness_score ?? null;
  const targetCompleteness = lifecycle.target_completeness ?? 0.85;
  const mandatoryComplete = lifecycle.mandatory_fields_complete ?? false;
  const responseStatus = lifecycle.response_status || 'pending';

  // Determine closure eligibility based on backend state
  const closureEligible = 
    responseStatus === 'complete' || 
    (completeness !== null && completeness >= targetCompleteness && mandatoryComplete);

  // Calculate score color
  const getScoreColor = (score) => {
    if (score === null || score === undefined) return 'text-gray-400';
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.5) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getProgressColor = (score) => {
    if (score === null || score === undefined) return 'bg-gray-200';
    if (score >= 0.8) return 'bg-green-500';
    if (score >= 0.5) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const formatPercent = (score) => {
    if (score === null || score === undefined) return 'N/A';
    return `${(score * 100).toFixed(0)}%`;
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-6">Safety & Confidence</h3>

      {/* Metrics Grid */}
      <div className="space-y-6">
        {/* Safety Confidence Score */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Safety Confidence</span>
            <span className={`text-lg font-bold ${getScoreColor(safetyConfidence)}`}>
              {formatPercent(safetyConfidence)}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className={`h-2.5 rounded-full transition-all duration-300 ${getProgressColor(safetyConfidence)}`}
              style={{ width: safetyConfidence !== null ? `${safetyConfidence * 100}%` : '0%' }}
            />
          </div>
          <p className="mt-1 text-xs text-gray-500">
            Confidence in safety assessment based on available data
          </p>
        </div>

        {/* Completeness Score */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Data Completeness</span>
            <span className={`text-lg font-bold ${getScoreColor(completeness)}`}>
              {formatPercent(completeness)}
            </span>
          </div>
          <div className="relative w-full bg-gray-200 rounded-full h-2.5">
            <div
              className={`h-2.5 rounded-full transition-all duration-300 ${getProgressColor(completeness)}`}
              style={{ width: completeness !== null ? `${completeness * 100}%` : '0%' }}
            />
            {/* Target marker */}
            <div 
              className="absolute top-0 w-0.5 h-2.5 bg-gray-600"
              style={{ left: `${targetCompleteness * 100}%` }}
              title={`Target: ${formatPercent(targetCompleteness)}`}
            />
          </div>
          <p className="mt-1 text-xs text-gray-500">
            Target: {formatPercent(targetCompleteness)}
          </p>
        </div>

        {/* Closure Eligibility */}
        <div className="pt-4 border-t border-gray-100">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">Closure Eligible</span>
            {closureEligible ? (
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-green-500" />
                <span className="text-sm font-medium text-green-600">Yes</span>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-red-500" />
                <span className="text-sm font-medium text-red-600">No</span>
              </div>
            )}
          </div>
          {!closureEligible && (
            <div className="mt-2 p-3 bg-red-50 rounded-lg">
              <p className="text-xs text-red-700">
                {completeness !== null && completeness < targetCompleteness && (
                  <span className="block">• Completeness below target ({formatPercent(completeness)} / {formatPercent(targetCompleteness)})</span>
                )}
                {!mandatoryComplete && (
                  <span className="block">• Mandatory fields incomplete</span>
                )}
                {responseStatus === 'pending' && (
                  <span className="block">• Awaiting reporter response</span>
                )}
              </p>
            </div>
          )}
          {closureEligible && (
            <div className="mt-2 p-3 bg-green-50 rounded-lg">
              <p className="text-xs text-green-700">
                All requirements met. Case is eligible for closure.
              </p>
            </div>
          )}
        </div>

        {/* Mandatory Fields Status */}
        <div className="pt-4 border-t border-gray-100">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">Mandatory Fields</span>
            {mandatoryComplete ? (
              <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                Complete
              </span>
            ) : (
              <span className="px-2 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-800">
                Incomplete
              </span>
            )}
          </div>
        </div>

        {/* Quick Stats */}
        <div className="pt-4 border-t border-gray-100 grid grid-cols-2 gap-4">
          <div className="p-3 bg-gray-50 rounded-lg text-center">
            <p className="text-xs text-gray-500 mb-1">Questions Sent</p>
            <p className="text-lg font-semibold text-gray-800">
              {lifecycle.total_questions_sent ?? 0}
            </p>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg text-center">
            <p className="text-xs text-gray-500 mb-1">Questions Answered</p>
            <p className="text-lg font-semibold text-gray-800">
              {lifecycle.total_questions_answered ?? 0}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SafetyConfidencePanel;
