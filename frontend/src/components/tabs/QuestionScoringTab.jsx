import React, { useState } from 'react';
import { api } from '../../utils/api';
import {
  Feature3StatusHeader,
  ResumedBanner,
  DuplicateQuestionLabel,
  RLOptimizationTooltip,
  ManualOverrideBadge,
  CriticalQuestionWarning
} from '../Feature3Components';

const QuestionScoringTab = ({ analysis, caseId }) => {
  const [showCriticalWarning, setShowCriticalWarning] = useState(false);

  if (!analysis || !analysis.missing_fields) {
    return (
      <div className="text-center py-12 text-gray-500">
        No question scoring data available
      </div>
    );
  }

  // Extract question scoring data
  const questions = analysis?.questions || [];
  const stopFollowup = analysis?.stop_followup || false;
  const stopReason = analysis?.stop_reason || '';
  const questionStats = analysis?.question_stats || {};

  // Feature-3: Extract new adaptive questioning data (graceful fallback)
  const answeredFields = analysis?.answered_fields || [];
  const previousAttempts = analysis?.previous_attempts || analysis?.previous_question_attempts || [];
  const daysToDeadline = analysis?.days_to_deadline;
  const isResumed = answeredFields.length > 0 || analysis?.is_resumed;
  const rlEnabled = questionStats?.rl_enabled || false;



  // Use questions array if present, fallback to missing_fields
  const fieldsToDisplay = questions.length > 0 ? questions : analysis?.missing_fields || [];

  const getCriticalityColor = (criticality) => {
    switch (criticality?.toUpperCase()) {
      case 'CRITICAL': return 'bg-purple-100 text-purple-800 border-purple-300';
      case 'HIGH': return 'bg-red-100 text-red-800 border-red-300';
      case 'MEDIUM': return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'LOW': return 'bg-green-100 text-green-800 border-green-300';
      default: return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const getDecisionBadge = (criticality) => {
    switch (criticality?.toUpperCase()) {
      case 'CRITICAL': return { label: 'ASK', color: 'bg-purple-600 text-white' };
      case 'HIGH': return { label: 'ASK', color: 'bg-green-600 text-white' };
      case 'MEDIUM': return { label: 'DEFER', color: 'bg-yellow-600 text-white' };
      case 'LOW': return { label: 'SKIP', color: 'bg-gray-600 text-white' };
      default: return { label: 'UNKNOWN', color: 'bg-gray-400 text-white' };
    }
  };

  const criticalityOrder = { 'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3 };
  
  // Sort by value_score if present, otherwise by criticality
  const sortedFields = [...fieldsToDisplay].sort((a, b) => {
    // Sort by value_score if present (descending)
    if (a.value_score !== undefined && b.value_score !== undefined) {
      return b.value_score - a.value_score;
    }
    // Fallback to criticality priority
    return (criticalityOrder[a.criticality?.toUpperCase()] || 999) - 
           (criticalityOrder[b.criticality?.toUpperCase()] || 999);
  });

  const criticalCount = fieldsToDisplay.filter(f => f.criticality?.toUpperCase() === 'CRITICAL').length;
  const highCount = fieldsToDisplay.filter(f => f.criticality?.toUpperCase() === 'HIGH').length;
  const mediumCount = fieldsToDisplay.filter(f => f.criticality?.toUpperCase() === 'MEDIUM').length;
  const lowCount = fieldsToDisplay.filter(f => f.criticality?.toUpperCase() === 'LOW').length;
  
  const completenessScore = analysis.completeness_score !== undefined 
    ? Math.round(analysis.completeness_score * 100) 
    : Math.round((1 - (fieldsToDisplay.length / 15)) * 100);

  return (
    <div className="space-y-6">
      {/* Feature-3: Status Header with Risk, Confidence, Deadline */}
      <Feature3StatusHeader
        daysToDeadline={daysToDeadline}
        confidence={analysis?.final_confidence || analysis?.confidence}
        riskScore={analysis?.risk_score}
        isResumed={isResumed}
        answeredFields={answeredFields}
        rlEnabled={rlEnabled}
      />

      {/* Feature-3: Resumed Follow-up Banner */}
      <ResumedBanner 
        answeredFields={answeredFields} 
        isResumed={isResumed} 
      />

      {/* Adaptive Stopping Alert */}
      {stopFollowup && (
        <div className="bg-green-50 border-l-4 border-green-500 p-6 rounded-lg shadow">
          <div className="flex items-start">
            <span className="text-3xl mr-4">✅</span>
            <div className="flex-1">
              <h3 className="text-lg font-bold text-green-900 mb-2">
                Follow-Up Stopped (Adaptive Decision)
              </h3>
              <p className="text-sm text-green-800 mb-3">
                <span className="font-semibold">Reason:</span> {stopReason === 'CONFIDENCE_THRESHOLD_REACHED' 
                  ? 'Confidence threshold reached - sufficient data for safety assessment'
                  : stopReason === 'LOW_RISK_SUFFICIENT_DATA'
                  ? 'Low-risk case with sufficient data quality'
                  : stopReason === 'NO_ACTION_REQUIRED'
                  ? 'No follow-up action required based on case decision'
                  : stopReason === 'SUFFICIENT_DATA_NO_CRITICAL_GAPS'
                  ? 'Sufficient data with no critical information gaps'
                  : stopReason || 'System determined no additional questions needed'}
              </p>
              <div className="flex items-center gap-4 text-xs text-green-700">
                <span>📊 Completeness: <strong>{completenessScore}%</strong></span>
                <span>⚠️ Risk: <strong>{Math.round((questionStats.risk_score || analysis.risk_score || 0) * 100)}%</strong></span>
                <span>🔴 Critical Missing: <strong>{questionStats.critical_missing || 0}</strong></span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg shadow p-4 border border-blue-200">
          <div className="text-sm text-blue-700 mb-1">Completeness</div>
          <div className="text-3xl font-bold text-blue-900">{completenessScore}%</div>
          <div className="text-xs text-blue-600 mt-1 font-medium">Data quality</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600 mb-1">Total {stopFollowup ? 'Excluded' : 'Missing'}</div>
          <div className="text-3xl font-bold text-gray-900">{fieldsToDisplay.length}</div>
          <div className="text-xs text-gray-500 mt-1">Data fields</div>
        </div>
        {criticalCount > 0 && (
          <div className="bg-purple-50 rounded-lg shadow p-4 border border-purple-200">
            <div className="text-sm text-purple-600 mb-1">Critical Priority</div>
            <div className="text-3xl font-bold text-purple-900">{criticalCount}</div>
            <div className="text-xs text-purple-600 mt-1 font-medium">Must ASK</div>
          </div>
        )}
        <div className="bg-red-50 rounded-lg shadow p-4 border border-red-200">
          <div className="text-sm text-red-600 mb-1">High Priority</div>
          <div className="text-3xl font-bold text-red-900">{highCount}</div>
          <div className="text-xs text-red-600 mt-1 font-medium">Must ASK</div>
        </div>
        <div className="bg-yellow-50 rounded-lg shadow p-4 border border-yellow-200">
          <div className="text-sm text-yellow-600 mb-1">Medium Priority</div>
          <div className="text-3xl font-bold text-yellow-900">{mediumCount}</div>
          <div className="text-xs text-yellow-600 mt-1 font-medium">Can DEFER</div>
        </div>
        <div className="bg-green-50 rounded-lg shadow p-4 border border-green-200">
          <div className="text-sm text-green-600 mb-1">Low Priority</div>
          <div className="text-3xl font-bold text-green-900">{lowCount}</div>
          <div className="text-xs text-green-600 mt-1 font-medium">Will SKIP</div>
        </div>
      </div>

      {/* Intelligence Statement */}
      {!stopFollowup && (
        <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
          <div className="flex items-start">
            <svg className="w-6 h-6 text-blue-600 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
              <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
            </svg>
            <div>
              <h3 className="text-sm font-semibold text-blue-900 mb-1">Question Value Scoring Active</h3>
              <p className="text-sm text-blue-800">
                {questions.length > 0 ? (
                  <>
                    Scored {questionStats.total_scored || fieldsToDisplay.length} missing fields and selected{' '}
                    <span className="font-semibold">{questions.length} high-value questions</span> to ask.
                    {questionStats.avg_value_score && (
                      <> Average question value: <span className="font-semibold">{(questionStats.avg_value_score * 100).toFixed(0)}%</span></>
                    )}
                  </>
                ) : (
                  <>
                    Analyzing {fieldsToDisplay.length} missing fields. Questions will be prioritized by{' '}
                    <span className="font-semibold">criticality × risk × urgency</span>.
                  </>
                )}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Question List */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            {stopFollowup ? 'Excluded Fields (Not Asked)' : questions.length > 0 ? 'Selected Questions' : 'Missing Fields & AI Decisions'}
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            Questions are prioritized by safety impact and data completeness value
          </p>
        </div>
        <div className="divide-y divide-gray-200">
          {sortedFields.map((field, index) => {
            const badge = getDecisionBadge(field.criticality);
            // Feature-3: Check if question was previously asked
            const isDuplicate = previousAttempts?.includes(field.field);
            const isReviewerAdded = field.isReviewerAdded || field.category === 'Reviewer';
            const forceCritical = field.force_critical;
            
            return (
              <div 
                key={index} 
                className={`p-4 hover:bg-gray-50 transition-colors ${
                  // Feature-3: Reduce opacity for duplicates (unless force_critical)
                  isDuplicate && !forceCritical ? 'opacity-75' : ''
                } ${
                  // Feature-3: Highlight force_critical with red border
                  forceCritical ? 'border-l-4 border-red-500 bg-red-50' : ''
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getCriticalityColor(field.criticality)}`}>
                        {field.criticality || 'N/A'} CRITICALITY
                      </span>
                      {field.value_score !== undefined && (
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${
                          field.value_score >= 0.75 ? 'bg-red-100 text-red-800 border-red-300' :
                          field.value_score >= 0.50 ? 'bg-yellow-100 text-yellow-800 border-yellow-300' :
                          'bg-green-100 text-green-800 border-green-300'
                        }`}>
                          VALUE: {Math.round(field.value_score * 100)}%
                        </span>
                      )}
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${badge.color}`}>
                        {badge.label}
                      </span>
                      
                      {/* Feature-3: Duplicate Question Label */}
                      <DuplicateQuestionLabel 
                        fieldName={field.field} 
                        previousAttempts={previousAttempts}
                        forceCritical={forceCritical}
                      />
                      
                      {/* Feature-3: Manual Override Badge */}
                      {isReviewerAdded && (
                        <ManualOverrideBadge forceCritical={forceCritical} />
                      )}
                      
                      {/* Feature-3: RL Optimization Tooltip */}
                      {field.score_breakdown && (
                        <RLOptimizationTooltip scoreBreakdown={field.score_breakdown} />
                      )}
                    </div>
                    <h4 className="text-base font-semibold text-gray-900 mb-1">
                      {field.field_display || field.field_name || field.field || 'Unknown Field'}
                    </h4>
                    {field.question && (
                      <p className="text-sm text-indigo-700 mb-2 italic">
                        📝 "{field.question}"
                      </p>
                    )}
                    <p className="text-sm text-gray-700 mb-2">
                      <span className="font-medium">Category:</span> {field.category || 'N/A'}
                    </p>
                    {field.safety_impact && (
                      <div className="flex items-start gap-2 mt-2 bg-gray-50 rounded p-2 border border-gray-200">
                        <svg className="w-4 h-4 text-gray-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 2a8 8 0 100 16 8 8 0 000-16zM9 9a1 1 0 012 0v4a1 1 0 01-2 0V9zm1-5a1 1 0 100 2 1 1 0 000-2z" clipRule="evenodd" />
                        </svg>
                        <p className="text-xs text-gray-700 flex-1">
                          <span className="font-semibold">Safety Rationale:</span> {field.safety_impact}
                        </p>
                      </div>
                    )}
                  </div>
                  {field.impact_score !== undefined && (
                    <div className="text-right flex-shrink-0">
                      <div className="text-2xl font-bold text-gray-900">{field.impact_score}</div>
                      <div className="text-xs text-gray-500">Impact</div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Feature-3: Critical Question Warning Modal (Section 6 - Safety Guarantee) */}
      <CriticalQuestionWarning 
        show={showCriticalWarning}
        onClose={() => setShowCriticalWarning(false)}
        onProceed={() => {
          setShowCriticalWarning(false);
          // Handle proceed action - in actual implementation would submit
        }}
      />
    </div>
  );
};

export default QuestionScoringTab;
