import React from 'react';

const QuestionIntelligence = ({ analysisData }) => {
  if (!analysisData) {
    return null;
  }

  const { analysis } = analysisData;
  const missingFields = analysis?.missing_fields || [];
  const riskScore = analysis?.risk_score || 0;
  const decision = analysis?.decision || 'PENDING';
  const responseProbability = analysis?.response_probability || 0;

  // Calculate safety confidence (inverse of risk)
  const safetyConfidence = (1 - riskScore) * 100;

  // Categorize questions based on criticality
  const categorizeQuestions = () => {
    const ask = [];
    const defer = [];
    const skip = [];

    missingFields.forEach((field) => {
      const criticality = field.criticality || field.safety_criticality || 'UNKNOWN';
      const fieldName = field.field_name || field.field || 'Unknown Field';

      const item = {
        fieldName,
        criticality,
        rawField: field
      };

      if (criticality === 'HIGH' || criticality === 'CRITICAL') {
        ask.push(item);
      } else if (criticality === 'MEDIUM') {
        defer.push(item);
      } else {
        skip.push(item);
      }
    });

    return { ask, defer, skip };
  };

  const { ask, defer, skip } = categorizeQuestions();

  // Get decision badge color
  const getDecisionColor = (criticality) => {
    if (criticality === 'HIGH' || criticality === 'CRITICAL') {
      return 'bg-green-100 text-green-800 border-green-300';
    } else if (criticality === 'MEDIUM') {
      return 'bg-yellow-100 text-yellow-800 border-yellow-300';
    } else {
      return 'bg-gray-100 text-gray-600 border-gray-300';
    }
  };

  const getDecisionText = (criticality) => {
    if (criticality === 'HIGH' || criticality === 'CRITICAL') {
      return 'ASK';
    } else if (criticality === 'MEDIUM') {
      return 'DEFER';
    } else {
      return 'SKIP';
    }
  };

  const getCriticalityColor = (criticality) => {
    if (criticality === 'HIGH' || criticality === 'CRITICAL') {
      return 'bg-red-100 text-red-800 border-red-300';
    } else if (criticality === 'MEDIUM') {
      return 'bg-yellow-100 text-yellow-800 border-yellow-300';
    } else {
      return 'bg-gray-100 text-gray-600 border-gray-300';
    }
  };

  // Generate explanation text
  const getExplanationText = () => {
    if (missingFields.length === 0) {
      return 'All critical data fields are complete. No follow-up questions needed.';
    }

    const parts = [];

    if (ask.length > 0) {
      parts.push(`${ask.length} high-priority question${ask.length > 1 ? 's' : ''} will be asked immediately for safety validation.`);
    }

    if (defer.length > 0) {
      parts.push(`${defer.length} medium-priority question${defer.length > 1 ? 's' : ''} deferred to reduce reporter fatigue.`);
    }

    if (skip.length > 0) {
      parts.push(`${skip.length} low-priority question${skip.length > 1 ? 's' : ''} skipped as safety confidence (${safetyConfidence.toFixed(0)}%) is sufficient.`);
    }

    return parts.join(' ');
  };

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-50 to-pink-50 px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            🎯 Question Value Scoring & Adaptive Reduction
          </h3>
          <span className="text-xs text-gray-500 font-medium">Feature 3</span>
        </div>
        <p className="text-sm text-gray-600 mt-1">
          AI prioritizes critical questions and reduces follow-up fatigue
        </p>
      </div>

      <div className="p-6 space-y-6">
        {/* Summary Cards Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Total Missing Fields */}
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4 border border-blue-200">
            <div className="text-sm text-blue-700 font-medium mb-1">Total Missing</div>
            <div className="text-3xl font-bold text-blue-900">{missingFields.length}</div>
            <div className="text-xs text-blue-600 mt-1">Fields</div>
          </div>

          {/* Questions to Ask */}
          <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-4 border border-green-200">
            <div className="text-sm text-green-700 font-medium mb-1">Will Ask</div>
            <div className="text-3xl font-bold text-green-900">{ask.length}</div>
            <div className="text-xs text-green-600 mt-1">High Priority</div>
          </div>

          {/* Questions Deferred */}
          <div className="bg-gradient-to-br from-yellow-50 to-yellow-100 rounded-lg p-4 border border-yellow-200">
            <div className="text-sm text-yellow-700 font-medium mb-1">Deferred</div>
            <div className="text-3xl font-bold text-yellow-900">{defer.length}</div>
            <div className="text-xs text-yellow-600 mt-1">Medium Priority</div>
          </div>

          {/* Questions Skipped */}
          <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg p-4 border border-gray-200">
            <div className="text-sm text-gray-700 font-medium mb-1">Skipped</div>
            <div className="text-3xl font-bold text-gray-900">{skip.length}</div>
            <div className="text-xs text-gray-600 mt-1">Low Priority</div>
          </div>
        </div>

        {/* Safety Confidence Indicator */}
        <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg p-5 border border-indigo-200">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center">
              <svg className="w-6 h-6 text-indigo-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              <h4 className="text-sm font-semibold text-gray-900">Safety Confidence</h4>
            </div>
            <span className="text-2xl font-bold text-indigo-900">
              {safetyConfidence.toFixed(0)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <div
              className={`h-3 transition-all duration-500 rounded-full ${
                safetyConfidence >= 70
                  ? 'bg-green-500'
                  : safetyConfidence >= 50
                  ? 'bg-yellow-500'
                  : 'bg-red-500'
              }`}
              style={{ width: `${safetyConfidence}%` }}
            />
          </div>
          <p className="text-xs text-gray-600 mt-2">
            Based on risk assessment and data completeness analysis
          </p>
        </div>

        {/* Question Prioritization Table */}
        {missingFields.length > 0 ? (
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
              <h4 className="text-sm font-semibold text-gray-900">Question Prioritization Matrix</h4>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                      Missing Field
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                      Criticality
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                      AI Decision
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                      Reasoning
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {missingFields.map((field, index) => {
                    const criticality = field.criticality || field.safety_criticality || 'UNKNOWN';
                    const fieldName = field.field_name || field.field || 'Unknown Field';
                    const decision = getDecisionText(criticality);
                    
                    let reasoning = '';
                    if (decision === 'ASK') {
                      reasoning = 'Critical for safety assessment';
                    } else if (decision === 'DEFER') {
                      reasoning = 'Can wait for follow-up round';
                    } else {
                      reasoning = 'Non-essential, skip to reduce fatigue';
                    }

                    return (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm text-gray-900">
                          {fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full border ${getCriticalityColor(criticality)}`}>
                            {criticality}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex px-3 py-1 text-xs font-bold rounded-full border ${getDecisionColor(criticality)}`}>
                            {decision}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {reasoning}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="text-center py-8 bg-green-50 rounded-lg border border-green-200">
            <svg className="w-16 h-16 mx-auto text-green-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-lg font-semibold text-green-900 mb-1">Complete Data Set</p>
            <p className="text-sm text-green-700">No missing fields detected — no follow-up needed</p>
          </div>
        )}

        {/* Explanation Section */}
        <div className="bg-purple-50 rounded-lg p-5 border border-purple-200">
          <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
            <svg className="w-5 h-5 mr-2 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            How AI Reduces Follow-Up Fatigue
          </h4>
          
          <div className="space-y-3 text-sm text-gray-700">
            <p className="leading-relaxed">
              {getExplanationText()}
            </p>

            {ask.length > 0 && (
              <div className="bg-white rounded p-3 border border-purple-200">
                <p className="font-medium text-purple-900 mb-1">✓ Critical Questions (Will Ask)</p>
                <p className="text-xs text-gray-600">
                  These fields are essential for safety signal detection and regulatory compliance. AI prioritizes these to ensure patient safety.
                </p>
              </div>
            )}

            {defer.length > 0 && (
              <div className="bg-white rounded p-3 border border-purple-200">
                <p className="font-medium text-purple-900 mb-1">⏸ Deferred Questions (Batched for Later)</p>
                <p className="text-xs text-gray-600">
                  These fields add value but are not immediately critical. AI groups them into a single follow-up to reduce contact frequency.
                </p>
              </div>
            )}

            {skip.length > 0 && (
              <div className="bg-white rounded p-3 border border-purple-200">
                <p className="font-medium text-purple-900 mb-1">⊘ Skipped Questions (Protecting Reporter)</p>
                <p className="text-xs text-gray-600">
                  With {safetyConfidence.toFixed(0)}% safety confidence, these low-value questions are skipped entirely. AI respects human time and prevents survey fatigue.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* AI Intelligence Summary */}
        <div className="border-t border-gray-200 pt-4">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center">
                <span className="text-xl">🤖</span>
              </div>
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900 mb-1">AI Intelligence at Work</p>
              <p className="text-sm text-gray-600">
                The system dynamically adjusts question volume based on safety needs, response probability ({(responseProbability * 100).toFixed(0)}%), 
                and current risk level ({(riskScore * 100).toFixed(0)}%). This prevents unnecessary follow-ups while maintaining safety standards.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default QuestionIntelligence;
