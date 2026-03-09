import React from 'react';
import FollowUpOptimizationCard from '../FollowUpOptimizationCard';

const AgenticDecisionTab = ({ analysis }) => {
  if (!analysis) {
    return (
      <div className="text-center py-12 text-gray-500">
        No analysis data available
      </div>
    );
  }

  const getDecisionColor = (decision) => {
    switch (decision?.toUpperCase()) {
      case 'ASK': return 'border-green-500 bg-green-50';
      case 'DEFER': return 'border-yellow-500 bg-yellow-50';
      case 'ESCALATE': return 'border-red-500 bg-red-50';
      default: return 'border-gray-500 bg-gray-50';
    }
  };

  const getDecisionIcon = (decision) => {
    switch (decision?.toUpperCase()) {
      case 'ASK': return '✅';
      case 'DEFER': return '⏸️';
      case 'ESCALATE': return '🚨';
      default: return '❓';
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority?.toUpperCase()) {
      case 'HIGH': return 'bg-red-100 text-red-800';
      case 'MEDIUM': return 'bg-yellow-100 text-yellow-800';
      case 'LOW': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      {/* Hero Decision Card */}
      <div className={`border-l-4 rounded-lg p-6 ${getDecisionColor(analysis.decision)}`}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="text-4xl">{getDecisionIcon(analysis.decision)}</span>
              <div>
                <h2 className="text-2xl font-bold text-gray-900">
                  {analysis.decision || 'N/A'}
                </h2>
                <p className="text-sm text-gray-600">Agentic Decision</p>
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold text-gray-900">
              {analysis.confidence !== undefined ? Math.round(analysis.confidence * 100) : 0}%
            </div>
            <div className="text-sm text-gray-600">Confidence</div>
          </div>
        </div>

        {/* Quick Metrics */}
        <div className="grid grid-cols-3 gap-4 mt-6">
          <div className="bg-white rounded-lg p-4">
            <div className="text-sm text-gray-600 mb-1">Priority Level</div>
            <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getPriorityColor(analysis.priority)}`}>
              {analysis.priority || 'N/A'}
            </span>
          </div>
          <div className="bg-white rounded-lg p-4">
            <div className="text-sm text-gray-600 mb-1">Risk Score</div>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-gray-200 rounded-full h-2">
                <div
                  className="bg-red-600 h-2 rounded-full"
                  style={{ width: `${(analysis.risk_score || 0) * 100}%` }}
                ></div>
              </div>
              <span className="text-sm font-semibold">{Math.round((analysis.risk_score || 0) * 100)}%</span>
            </div>
          </div>
          <div className="bg-white rounded-lg p-4">
            <div className="text-sm text-gray-600 mb-1">Urgency</div>
            <div className="text-lg font-semibold text-gray-900">
              {analysis.urgency || 'Standard'}
            </div>
          </div>
        </div>
      </div>

      {/* Follow-Up Optimization Card - Feature 2 */}
      <FollowUpOptimizationCard analysis={analysis} />

      {/* AI Reasoning Section - Enhanced */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 rounded-full bg-gradient-to-r from-blue-500 to-indigo-600 flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Decision Rationale</h3>
            <p className="text-xs text-gray-500">Explainable AI reasoning for this case</p>
          </div>
        </div>

        {/* Decision Summary Card */}
        {analysis.decision && (
          <div className={`mb-4 p-4 rounded-lg border-l-4 ${
            analysis.decision === 'ESCALATE' ? 'bg-red-50 border-red-500' :
            analysis.decision === 'FOLLOWUP' ? 'bg-orange-50 border-orange-500' :
            analysis.decision === 'CLOSE' ? 'bg-green-50 border-green-500' :
            'bg-blue-50 border-blue-500'
          }`}>
            <div className="flex items-center gap-3">
              <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                analysis.decision === 'ESCALATE' ? 'bg-red-500 text-white' :
                analysis.decision === 'FOLLOWUP' ? 'bg-orange-500 text-white' :
                analysis.decision === 'CLOSE' ? 'bg-green-500 text-white' :
                'bg-blue-500 text-white'
              }`}>
                {analysis.decision}
              </span>
              <span className="text-sm font-medium text-gray-700">
                {analysis.decision === 'ESCALATE' ? 'Requires immediate expert review' :
                 analysis.decision === 'FOLLOWUP' ? 'Additional information needed' :
                 analysis.decision === 'CLOSE' ? 'Case can be closed' :
                 'Decision pending'}
              </span>
            </div>
          </div>
        )}

        {/* Key Factors Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          {analysis.risk_score !== undefined && (
            <div className="p-3 bg-gray-50 rounded-lg text-center">
              <p className="text-xs text-gray-500 mb-1">Risk Score</p>
              <p className={`text-xl font-bold ${
                analysis.risk_score >= 0.7 ? 'text-red-600' :
                analysis.risk_score >= 0.4 ? 'text-orange-600' :
                'text-green-600'
              }`}>
                {(analysis.risk_score * 100).toFixed(0)}%
              </p>
            </div>
          )}
          {analysis.response_probability !== undefined && (
            <div className="p-3 bg-gray-50 rounded-lg text-center">
              <p className="text-xs text-gray-500 mb-1">Response Prob.</p>
              <p className={`text-xl font-bold ${
                analysis.response_probability >= 0.6 ? 'text-green-600' :
                analysis.response_probability >= 0.3 ? 'text-orange-600' :
                'text-red-600'
              }`}>
                {(analysis.response_probability * 100).toFixed(0)}%
              </p>
            </div>
          )}
          {analysis.engagement_risk && (
            <div className="p-3 bg-gray-50 rounded-lg text-center">
              <p className="text-xs text-gray-500 mb-1">Engagement Risk</p>
              <p className={`text-sm font-bold ${
                analysis.engagement_risk.includes('HIGH') ? 'text-red-600' :
                analysis.engagement_risk.includes('MEDIUM') ? 'text-orange-600' :
                'text-green-600'
              }`}>
                {analysis.engagement_risk.replace('_ENGAGEMENT', '').replace('_RISK', '')}
              </p>
            </div>
          )}
          {analysis.missing_fields_count !== undefined && (
            <div className="p-3 bg-gray-50 rounded-lg text-center">
              <p className="text-xs text-gray-500 mb-1">Missing Fields</p>
              <p className={`text-xl font-bold ${
                analysis.missing_fields_count >= 5 ? 'text-red-600' :
                analysis.missing_fields_count >= 2 ? 'text-orange-600' :
                'text-green-600'
              }`}>
                {analysis.missing_fields_count}
              </p>
            </div>
          )}
        </div>

        {/* Reasoning Text - Properly Formatted */}
        <div className="bg-gradient-to-r from-gray-50 to-slate-50 rounded-lg p-4 border border-gray-200">
          <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <svg className="w-4 h-4 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
            Detailed Reasoning
          </h4>
          <div className="text-sm text-gray-700 leading-relaxed space-y-2">
            {(analysis.reasoning || 'No reasoning available')
              .split('. ')
              .filter(s => s.trim())
              .map((sentence, idx) => {
                // Parse **bold** text
                const parts = sentence.split(/\*\*(.*?)\*\*/g);
                return (
                  <p key={idx} className="flex items-start gap-2">
                    <span className="text-blue-500 mt-0.5">•</span>
                    <span>
                      {parts.map((part, i) => 
                        i % 2 === 1 ? (
                          <span key={i} className="font-semibold text-blue-700 bg-blue-50 px-1 rounded">
                            {part}
                          </span>
                        ) : (
                          <span key={i}>{part}</span>
                        )
                      )}
                      {!sentence.endsWith('.') && '.'}
                    </span>
                  </p>
                );
              })}
          </div>
        </div>
      </div>

      {/* Decision Factors - Enhanced */}
      {analysis.decision_factors && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-full bg-gradient-to-r from-green-500 to-emerald-600 flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Decision Factors</h3>
              <p className="text-xs text-gray-500">Key factors influencing this decision</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.entries(analysis.decision_factors).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between p-3 bg-gradient-to-r from-gray-50 to-slate-50 rounded-lg border border-gray-100 hover:border-blue-200 transition-colors">
                <span className="text-sm font-medium text-gray-700 capitalize">
                  {key.replace(/_/g, ' ')}
                </span>
                {typeof value === 'boolean' ? (
                  <span className={`w-6 h-6 rounded-full flex items-center justify-center ${
                    value ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
                  }`}>
                    {value ? '✓' : '✗'}
                  </span>
                ) : (
                  <span className="text-sm font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                    {value}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Metadata - Enhanced */}
      <div className="bg-gradient-to-r from-slate-100 to-gray-100 rounded-lg p-4 border border-gray-200">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-white shadow-sm flex items-center justify-center">
                <svg className="w-4 h-4 text-gray-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                </svg>
              </div>
              <div>
                <p className="text-xs text-gray-500">Timestamp</p>
                <p className="text-sm font-medium text-gray-800">{new Date().toLocaleString()}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-white shadow-sm flex items-center justify-center">
                <svg className="w-4 h-4 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6z" />
                </svg>
              </div>
              <div>
                <p className="text-xs text-gray-500">Agent</p>
                <p className="text-sm font-medium text-gray-800">SmartFU v1.0</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-white shadow-sm flex items-center justify-center">
                <svg className="w-4 h-4 text-purple-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M12.316 3.051a1 1 0 01.633 1.265l-4 12a1 1 0 11-1.898-.632l4-12a1 1 0 011.265-.633zM5.707 6.293a1 1 0 010 1.414L3.414 10l2.293 2.293a1 1 0 11-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0zm8.586 0a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 11-1.414-1.414L16.586 10l-2.293-2.293a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </div>
              <div>
                <p className="text-xs text-gray-500">Model</p>
                <p className="text-sm font-medium text-gray-800">Mistral Large</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full flex items-center gap-1">
              <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
              Verified
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AgenticDecisionTab;
