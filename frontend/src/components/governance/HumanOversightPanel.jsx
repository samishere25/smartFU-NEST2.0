import React, { useState, useEffect } from 'react';
import { api } from '../../utils/api';

const HumanOversightPanel = ({ caseId, onActionComplete }) => {
  const [oversightData, setOversightData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [showOverrideForm, setShowOverrideForm] = useState(false);
  const [overrideReason, setOverrideReason] = useState('');

  useEffect(() => {
    if (caseId) {
      fetchOversightData();
    }
  }, [caseId]);

  const fetchOversightData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getCaseOversight(caseId);
      setOversightData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (action) => {
    if (action === 'OVERRIDE' && !overrideReason.trim()) {
      alert('Please provide a reason for overriding the AI decision');
      return;
    }

    try {
      setSubmitting(true);
      await api.submitOversightAction(caseId, action, overrideReason || null);
      
      // Refresh oversight data
      await fetchOversightData();
      
      // Reset form
      setShowOverrideForm(false);
      setOverrideReason('');
      
      // Notify parent component
      if (onActionComplete) {
        onActionComplete(action);
      }
    } catch (err) {
      alert(`Failed to submit action: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4 animate-pulse">
        <div className="h-5 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="space-y-3">
          <div className="h-10 bg-gray-200 rounded"></div>
          <div className="h-10 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <p className="text-gray-500 text-sm">⚠️ Oversight data unavailable</p>
      </div>
    );
  }

  if (!oversightData) return null;

  const getStatusBadge = (status) => {
    const configs = {
      'REQUIRED': { color: 'bg-red-100 text-red-800', icon: '⚠️' },
      'OPTIONAL': { color: 'bg-blue-100 text-blue-800', icon: 'ℹ️' },
      'COMPLETED': { color: 'bg-green-100 text-green-800', icon: '✓' }
    };
    const config = configs[status] || configs['OPTIONAL'];
    return (
      <span className={`px-3 py-1 rounded-full text-xs font-medium ${config.color}`}>
        {config.icon} {status}
      </span>
    );
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <span>👤</span>
          Human-in-the-Loop Governance
        </h3>
        {getStatusBadge(oversightData.review_status)}
      </div>

      {/* Last Review Info */}
      {oversightData.last_reviewed_by && (
        <div className="mb-4 p-3 bg-gray-50 rounded-lg">
          <div className="text-sm">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium text-gray-700">Last Reviewed By:</span>
              <span className="text-gray-900">{oversightData.last_reviewed_by}</span>
            </div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium text-gray-700">Date:</span>
              <span className="text-gray-900">{formatDate(oversightData.last_reviewed_at)}</span>
            </div>
            {oversightData.notes && (
              <div className="mt-2 pt-2 border-t border-gray-200">
                <span className="font-medium text-gray-700">Notes:</span>
                <p className="text-gray-900 mt-1">{oversightData.notes}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      {!showOverrideForm ? (
        <div className="flex gap-3">
          <button
            onClick={() => handleAction('APPROVE')}
            disabled={submitting}
            className="flex-1 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium transition-colors"
          >
            {submitting ? '⏳ Processing...' : '✓ Approve AI Decision'}
          </button>
          <button
            onClick={() => setShowOverrideForm(true)}
            disabled={submitting}
            className="flex-1 px-4 py-3 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium transition-colors"
          >
            🔄 Override AI Decision
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Reason for Override <span className="text-red-600">*</span>
            </label>
            <textarea
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              placeholder="Provide clinical judgement or additional context..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows="3"
            />
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => handleAction('OVERRIDE')}
              disabled={submitting || !overrideReason.trim()}
              className="flex-1 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium"
            >
              {submitting ? '⏳ Submitting...' : 'Submit Override'}
            </button>
            <button
              onClick={() => {
                setShowOverrideForm(false);
                setOverrideReason('');
              }}
              disabled={submitting}
              className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 disabled:cursor-not-allowed font-medium"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex items-start gap-2 text-xs text-gray-600">
          <span>📋</span>
          <span>
            All oversight actions are logged for audit and regulatory compliance.
          </span>
        </div>
      </div>
    </div>
  );
};

export default HumanOversightPanel;
