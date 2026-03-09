import React from 'react';

/**
 * Lifecycle Status Card Component
 * Displays key lifecycle metrics for a case
 * 
 * Color rules:
 * - Green → complete
 * - Orange → pending
 * - Red → escalated or deadline <= 2 days
 */
const LifecycleStatusCard = ({ lifecycle, summary }) => {
  if (!lifecycle && !summary) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Lifecycle Status</h3>
        <p className="text-gray-500">No lifecycle data available</p>
      </div>
    );
  }

  // Use summary if provided, otherwise extract from lifecycle
  const data = summary || lifecycle || {};

  const caseId = data.case_id || lifecycle?.case_id || 'N/A';
  const reporterType = data.reporter_type || lifecycle?.reporter_type || 'N/A';
  const attemptCount = data.attempt_count ?? lifecycle?.attempt_count ?? 0;
  const maxAttempts = data.max_attempts ?? lifecycle?.max_attempts ?? 3;
  const responseStatus = data.response_status || lifecycle?.response_status || 'pending';
  const escalationStatus = data.escalation_status || lifecycle?.escalation_status || 'none';
  const deadCaseFlag = data.dead_case_flag ?? lifecycle?.dead_case_flag ?? false;
  const daysRemaining = data.days_remaining ?? lifecycle?.days_remaining ?? null;
  const lifecycleStatus = data.lifecycle_status || lifecycle?.lifecycle_status || 'active';
  const regulatoryDeadline = lifecycle?.regulatory_deadline || null;

  // Determine status colors
  const getStatusColor = (status) => {
    if (status === 'complete' || status === 'completed' || status === 'closed') {
      return 'bg-green-100 text-green-800';
    }
    if (status === 'escalated' || status === 'dead_case') {
      return 'bg-red-100 text-red-800';
    }
    return 'bg-orange-100 text-orange-800';
  };

  const getEscalationColor = (status) => {
    if (status === 'none') return 'bg-gray-100 text-gray-600';
    if (status === 'flagged') return 'bg-yellow-100 text-yellow-800';
    if (status === 'urgent') return 'bg-orange-100 text-orange-800';
    return 'bg-red-100 text-red-800';
  };

  const getDeadlineColor = (days) => {
    if (days === null || days === undefined) return 'text-gray-600';
    if (days <= 0) return 'text-red-600 font-bold';
    if (days <= 2) return 'text-red-600';
    if (days <= 5) return 'text-orange-600';
    return 'text-green-600';
  };

  const getReporterBadgeColor = (type) => {
    if (type === 'HCP') return 'bg-blue-100 text-blue-800';
    return 'bg-purple-100 text-purple-800';
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-800">Lifecycle Status</h3>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(lifecycleStatus)}`}>
          {lifecycleStatus.replace('_', ' ').toUpperCase()}
        </span>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Case ID */}
        <div className="p-3 bg-gray-50 rounded-lg">
          <p className="text-xs text-gray-500 mb-1">Case ID</p>
          <p className="text-sm font-medium text-gray-900 truncate" title={caseId}>
            {caseId.length > 12 ? `${caseId.substring(0, 12)}...` : caseId}
          </p>
        </div>

        {/* Reporter Type with Policy Info */}
        <div className="p-3 bg-gray-50 rounded-lg">
          <p className="text-xs text-gray-500 mb-1">Reporter Type</p>
          <div className="flex items-center gap-2">
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${getReporterBadgeColor(reporterType)}`}>
              {reporterType}
            </span>
            {reporterType === 'HCP' && (
              <span className="text-xs text-blue-600" title="Healthcare Professional: 4 attempts, 5 questions/round, escalates to medical team">
                (4 attempts)
              </span>
            )}
            {reporterType === 'NON_HCP' && (
              <span className="text-xs text-purple-600" title="Consumer/Patient: 3 attempts, 2 questions/round, escalates to supervisor">
                (3 attempts)
              </span>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-1">
            {reporterType === 'HCP' ? 'Medical Team Escalation' : 'Supervisor Escalation'}
          </p>
        </div>

        {/* Attempt Count */}
        <div className="p-3 bg-gray-50 rounded-lg">
          <p className="text-xs text-gray-500 mb-1">Attempts</p>
          <p className="text-sm font-medium text-gray-900">
            {attemptCount} / {maxAttempts}
          </p>
          <div className="mt-1 w-full bg-gray-200 rounded-full h-1.5">
            <div
              className="bg-blue-600 h-1.5 rounded-full"
              style={{ width: `${Math.min((attemptCount / maxAttempts) * 100, 100)}%` }}
            />
          </div>
        </div>

        {/* Response Status */}
        <div className="p-3 bg-gray-50 rounded-lg">
          <p className="text-xs text-gray-500 mb-1">Response Status</p>
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(responseStatus)}`}>
            {responseStatus.toUpperCase()}
          </span>
        </div>

        {/* Escalation Status */}
        <div className="p-3 bg-gray-50 rounded-lg">
          <p className="text-xs text-gray-500 mb-1">Escalation</p>
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${getEscalationColor(escalationStatus)}`}>
            {escalationStatus.replace('_', ' ').toUpperCase()}
          </span>
        </div>

        {/* Dead Case Flag */}
        <div className="p-3 bg-gray-50 rounded-lg">
          <p className="text-xs text-gray-500 mb-1">Dead Case</p>
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${deadCaseFlag ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}`}>
            {deadCaseFlag ? 'YES' : 'NO'}
          </span>
        </div>

        {/* Regulatory Deadline */}
        <div className="p-3 bg-gray-50 rounded-lg">
          <p className="text-xs text-gray-500 mb-1">Deadline</p>
          <p className="text-sm font-medium text-gray-900">
            {formatDate(regulatoryDeadline)}
          </p>
        </div>

        {/* Days Remaining */}
        <div className="p-3 bg-gray-50 rounded-lg">
          <p className="text-xs text-gray-500 mb-1">Days Remaining</p>
          <p className={`text-sm font-medium ${getDeadlineColor(daysRemaining)}`}>
            {daysRemaining !== null ? daysRemaining : 'N/A'}
            {daysRemaining !== null && daysRemaining <= 2 && (
              <span className="ml-1 text-xs">⚠️</span>
            )}
          </p>
        </div>
      </div>
    </div>
  );
};

export default LifecycleStatusCard;
