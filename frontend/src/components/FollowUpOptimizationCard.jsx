import React from 'react';
import {
  getResponseConfidence,
  getTimingRecommendation,
  getChannelRecommendation,
  getReporterTypeLabel,
  getConfidenceColor,
  formatProbability
} from '../utils/followUpOptimization';

/**
 * Follow-Up Optimization Card
 * Displays AI-assisted follow-up strategy based on backend analysis
 * - Response probability prediction
 * - Recommended timing
 * - Recommended communication channel
 * All derived from real backend data (NO hardcoding)
 */
const FollowUpOptimizationCard = ({ analysis }) => {
  if (!analysis) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-2">
          Follow-Up Optimization (AI-Assisted)
        </h3>
        <p className="text-gray-500 text-sm">No analysis data available</p>
      </div>
    );
  }

  const responseProbability = analysis.response_probability || 0;
  const confidence = getResponseConfidence(responseProbability);
  const timingRec = getTimingRecommendation(analysis);
  const channelRec = getChannelRecommendation(analysis);
  const reporterType = analysis.case_data?.reporter_type || 'UNKNOWN';
  
  // NEW: Feature-2 fields from backend
  const predictionConfidence = analysis.prediction_confidence || 0;
  const engagementRisk = analysis.engagement_risk || 'UNKNOWN';
  const followupPriority = analysis.followup_priority || 'STANDARD';
  const followupFrequency = analysis.followup_frequency || 48;
  const escalationNeeded = analysis.escalation_needed || false;
  const escalationReason = analysis.escalation_reason || '';

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 border-l-4 border-indigo-500">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
          <span className="text-2xl">🎯</span>
          Follow-Up Optimization (AI-Assisted)
        </h3>
        <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
          Real-time Analysis
        </span>
      </div>

      {/* Response Prediction Section */}
      <div className="mb-6 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-200">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-semibold text-gray-700">
            Predicted Response Probability
          </h4>
          <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${getConfidenceColor(confidence)}`}>
            {confidence} CONFIDENCE
          </span>
        </div>
        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-4xl font-bold text-indigo-900">
            {formatProbability(responseProbability)}
          </span>
          <span className="text-sm text-gray-600">
            likelihood of reporter response
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
          <div
            className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${Math.round(responseProbability * 100)}%` }}
          />
        </div>
        <p className="text-xs text-gray-600 mt-2">
          Reporter: <span className="font-semibold">{getReporterTypeLabel(reporterType)}</span>
        </p>
        
        {/* NEW: Prediction Confidence */}
        {predictionConfidence > 0 && (
          <div className="mt-3 pt-3 border-t border-blue-300">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-gray-700">
                Prediction Confidence
              </span>
              <span className="text-xs font-bold text-purple-700">
                {Math.round(predictionConfidence * 100)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-1.5">
              <div
                className="bg-purple-600 h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${Math.round(predictionConfidence * 100)}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* NEW: Engagement Risk & Follow-Up Strategy */}
      {engagementRisk && engagementRisk !== 'UNKNOWN' && (
        <div className="mb-4 bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-200">
          <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <span className="text-xl">📊</span>
            Follow-Up Strategy
          </h4>
          
          <div className="space-y-3">
            {/* Engagement Risk */}
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600">Engagement Risk:</span>
              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                engagementRisk === 'VERY_HIGH' ? 'bg-red-100 text-red-800 border border-red-300' :
                engagementRisk === 'HIGH' || engagementRisk === 'HIGH_RISK_ENGAGEMENT' ? 'bg-orange-100 text-orange-800 border border-orange-300' :
                engagementRisk === 'MODERATE' || engagementRisk === 'MEDIUM_RISK_ENGAGEMENT' ? 'bg-yellow-100 text-yellow-800 border border-yellow-300' :
                'bg-green-100 text-green-800 border border-green-300'
              }`}>
                {engagementRisk.replace(/_/g, ' ')}
              </span>
            </div>
            
            {/* Follow-Up Priority */}
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600">Priority:</span>
              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                followupPriority === 'URGENT' || followupPriority === 'CRITICAL' ? 'bg-red-100 text-red-800 border border-red-300' :
                followupPriority === 'ELEVATED' || followupPriority === 'HIGH' ? 'bg-orange-100 text-orange-800 border border-orange-300' :
                followupPriority === 'STANDARD' || followupPriority === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800 border border-yellow-300' :
                'bg-green-100 text-green-800 border border-green-300'
              }`}>
                {followupPriority}
              </span>
            </div>
            
            {/* Follow-Up Frequency */}
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600">Follow-Up Frequency:</span>
              <span className="text-xs font-bold text-gray-900">
                Every {followupFrequency} hours
              </span>
            </div>
          </div>
        </div>
      )}

      {/* NEW: Escalation Alert */}
      {escalationNeeded && (
        <div className="mb-4 bg-red-50 rounded-lg p-4 border-2 border-red-300">
          <div className="flex items-start gap-3">
            <span className="text-2xl">⚠️</span>
            <div className="flex-1">
              <h4 className="text-sm font-bold text-red-800 mb-1">
                Escalation Required
              </h4>
              {escalationReason && (
                <p className="text-xs text-red-700">
                  {escalationReason}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Timing Recommendation Section */}
      <div className="mb-4 bg-gradient-to-br from-yellow-50 to-orange-50 rounded-lg p-4 border border-yellow-200">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xl">⏰</span>
          <h4 className="text-sm font-semibold text-gray-700">
            Recommended Timing
          </h4>
          <span className={`ml-auto px-2 py-1 rounded text-xs font-semibold ${
            timingRec.urgency === 'CRITICAL' ? 'bg-red-100 text-red-800' :
            timingRec.urgency === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' :
            timingRec.urgency === 'LOW' ? 'bg-green-100 text-green-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            {timingRec.urgency}
          </span>
        </div>
        <p className="text-base font-bold text-gray-900 mb-1">
          {timingRec.timing}
        </p>
        <p className="text-xs text-gray-600">
          {timingRec.reasoning}
        </p>
      </div>

      {/* Channel Recommendation Section */}
      <div className="bg-gradient-to-br from-green-50 to-teal-50 rounded-lg p-4 border border-green-200">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xl">{channelRec.icon}</span>
          <h4 className="text-sm font-semibold text-gray-700">
            Recommended Channel
          </h4>
        </div>
        <p className="text-base font-bold text-gray-900 mb-1">
          {channelRec.channel}
        </p>
        <p className="text-xs text-gray-600 mb-2">
          {channelRec.reasoning}
        </p>
        {channelRec.alternatives && channelRec.alternatives.length > 0 && (
          <div className="mt-2 pt-2 border-t border-green-300">
            <p className="text-xs text-gray-500 mb-1">Alternatives:</p>
            <div className="flex flex-wrap gap-1">
              {channelRec.alternatives.map((alt, idx) => (
                <span
                  key={idx}
                  className="px-2 py-1 bg-white text-gray-700 text-xs rounded border border-gray-300"
                >
                  {alt}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* AI Decision Context */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span>🤖</span>
          <span>
            Based on: Risk Score ({(analysis.risk_score * 100).toFixed(0)}%), 
            Decision ({analysis.decision}), 
            Reporter Type ({reporterType})
          </span>
        </div>
      </div>
    </div>
  );
};

export default FollowUpOptimizationCard;
