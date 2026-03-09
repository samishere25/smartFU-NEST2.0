import React from 'react';

/**
 * Attempt Timeline Table Component
 * Displays chronological history of follow-up attempts
 * 
 * Columns:
 * - Attempt Number
 * - Channel
 * - Sent At
 * - Response Received
 * - Escalation Triggered
 */
const AttemptTimelineTable = ({ attempts }) => {
  if (!attempts || attempts.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Attempt History</h3>
        <div className="text-center py-8">
          <div className="text-gray-400 text-4xl mb-2">📋</div>
          <p className="text-gray-500">No attempts recorded yet</p>
        </div>
      </div>
    );
  }

  // Sort attempts chronologically (oldest first)
  const sortedAttempts = [...attempts].sort((a, b) => {
    const dateA = new Date(a.sent_at || a.created_at || 0);
    const dateB = new Date(b.sent_at || b.created_at || 0);
    return dateA - dateB;
  });

  const formatDateTime = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  const getChannelBadge = (channel) => {
    const channelColors = {
      'EMAIL': 'bg-blue-100 text-blue-800',
      'WHATSAPP': 'bg-green-100 text-green-800',
      'SMS': 'bg-purple-100 text-purple-800',
      'PHONE': 'bg-orange-100 text-orange-800'
    };
    return channelColors[channel?.toUpperCase()] || 'bg-gray-100 text-gray-800';
  };

  const getAttemptTypeBadge = (type) => {
    const typeColors = {
      'initial': 'bg-blue-50 text-blue-700',
      'followup': 'bg-indigo-50 text-indigo-700',
      'reminder': 'bg-yellow-50 text-yellow-700',
      'escalation': 'bg-red-50 text-red-700'
    };
    return typeColors[type?.toLowerCase()] || 'bg-gray-50 text-gray-700';
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-800">Attempt History</h3>
        <span className="text-sm text-gray-500">
          {sortedAttempts.length} attempt{sortedAttempts.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                #
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Type
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Channel
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Sent At
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Questions
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Response
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Compliance
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedAttempts.map((attempt, index) => {
              const attemptNumber = attempt.attempt_number || index + 1;
              const attemptType = attempt.attempt_type || 'followup';
              const channel = attempt.channel || 'N/A';
              const sentAt = attempt.sent_at || attempt.created_at;
              const questionsCount = attempt.questions_count ?? attempt.questions_sent?.length ?? 0;
              const responseReceived = attempt.response_received ?? false;
              const questionsAnswered = attempt.questions_answered ?? 0;
              const compliance24h = attempt.compliance_24h_met ?? true;
              const reminderSent = attempt.reminder_sent ?? false;

              return (
                <tr key={attempt.attempt_id || index} className="hover:bg-gray-50">
                  {/* Attempt Number */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="text-sm font-medium text-gray-900">
                      {attemptNumber}
                    </span>
                  </td>

                  {/* Attempt Type */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${getAttemptTypeBadge(attemptType)}`}>
                      {attemptType.charAt(0).toUpperCase() + attemptType.slice(1)}
                    </span>
                  </td>

                  {/* Channel */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${getChannelBadge(channel)}`}>
                      {channel}
                    </span>
                  </td>

                  {/* Sent At */}
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                    {formatDateTime(sentAt)}
                    {reminderSent && (
                      <span className="ml-1 text-xs text-yellow-600">📧</span>
                    )}
                  </td>

                  {/* Questions */}
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                    {questionsCount > 0 ? questionsCount : '-'}
                  </td>

                  {/* Response */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    {responseReceived ? (
                      <div className="flex items-center gap-1">
                        <span className="text-green-600">✓</span>
                        <span className="text-sm text-gray-600">
                          {questionsAnswered > 0 ? `${questionsAnswered} answered` : 'Received'}
                        </span>
                      </div>
                    ) : (
                      <span className="text-sm text-gray-400">Awaiting</span>
                    )}
                  </td>

                  {/* 24h Compliance */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    {compliance24h ? (
                      <span className="text-green-600 text-sm">✓ Met</span>
                    ) : (
                      <span className="text-red-600 text-sm">✗ Violated</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Summary Footer */}
      <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between text-sm text-gray-500">
        <div>
          Total Questions Sent: {sortedAttempts.reduce((sum, a) => sum + (a.questions_count || a.questions_sent?.length || 0), 0)}
        </div>
        <div>
          Responses Received: {sortedAttempts.filter(a => a.response_received).length}/{sortedAttempts.length}
        </div>
      </div>
    </div>
  );
};

export default AttemptTimelineTable;
