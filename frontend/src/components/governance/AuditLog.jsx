import React, { useState, useEffect } from 'react';
import { api } from '../../utils/api';

const AuditLog = ({ caseId }) => {
  const [auditLog, setAuditLog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    if (caseId) {
      fetchAuditLog();
    }
  }, [caseId]);

  const fetchAuditLog = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getCaseAuditLog(caseId);
      setAuditLog(data || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const getAgentIcon = (actor) => {
    const icons = {
      'RiskAssessmentAgent': '⚠️',
      'DataCompletenessAgent': '📋',
      'ResponseStrategyAgent': '📊',
      'EscalationAgent': '🚨',
      'QuestionGenerationAgent': '❓',
      'SignalDetectionAgent': '🔍',
      'HumanReviewer': '👤',
      'System': '⚙️'
    };
    return icons[actor] || '🤖';
  };

  const getDecisionBadge = (decision) => {
    const configs = {
      'HIGH_RISK': 'bg-red-100 text-red-800',
      'MEDIUM_RISK': 'bg-yellow-100 text-yellow-800',
      'LOW_RISK': 'bg-green-100 text-green-800',
      'ESCALATE': 'bg-orange-100 text-orange-800',
      'NO_ACTION': 'bg-gray-100 text-gray-800',
      'APPROVED': 'bg-green-100 text-green-800',
      'OVERRIDE': 'bg-purple-100 text-purple-800'
    };
    
    const colorClass = configs[decision] || 'bg-blue-100 text-blue-800';
    return (
      <span className={`px-2 py-1 rounded text-xs font-medium ${colorClass}`}>
        {decision}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4 animate-pulse">
        <div className="h-5 bg-gray-200 rounded w-1/4 mb-3"></div>
        <div className="space-y-2">
          <div className="h-16 bg-gray-200 rounded"></div>
          <div className="h-16 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <p className="text-gray-500 text-sm">⚠️ Audit log unavailable</p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-5 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <span>📜</span>
          Audit & Explainability Log
          <span className="text-sm font-normal text-gray-500">
            ({auditLog.length} {auditLog.length === 1 ? 'entry' : 'entries'})
          </span>
        </h3>
        <span className="text-gray-400">
          {isExpanded ? '▼' : '▶'}
        </span>
      </button>

      {isExpanded && (
        <div className="px-5 pb-5 border-t border-gray-200">
          {auditLog.length === 0 ? (
            <div className="py-8 text-center text-gray-500 text-sm">
              No audit entries yet
            </div>
          ) : (
            <div className="mt-4 space-y-3">
              {auditLog.map((entry, index) => (
                <div
                  key={index}
                  className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{getAgentIcon(entry.actor)}</span>
                      <div>
                        <div className="font-medium text-gray-900 text-sm">
                          {entry.actor}
                        </div>
                        <div className="text-xs text-gray-500">
                          {formatTimestamp(entry.timestamp)}
                        </div>
                      </div>
                    </div>
                    {getDecisionBadge(entry.decision)}
                  </div>
                  
                  {entry.reason && (
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      <div className="text-xs font-medium text-gray-700 mb-1">
                        Reasoning:
                      </div>
                      <div className="text-sm text-gray-900 bg-gray-50 p-2 rounded">
                        {entry.reason}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
          
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="flex items-start gap-2 text-xs text-gray-600">
              <span>🔒</span>
              <span>
                This audit log is immutable and complies with regulatory requirements for traceability.
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AuditLog;
