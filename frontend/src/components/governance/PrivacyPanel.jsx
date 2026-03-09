import React, { useState, useEffect } from 'react';
import { api } from '../../utils/api';

const PrivacyPanel = ({ caseId }) => {
  const [privacyData, setPrivacyData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (caseId) {
      fetchPrivacyData();
    }
  }, [caseId]);

  const fetchPrivacyData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getCasePrivacy(caseId);
      setPrivacyData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4 animate-pulse">
        <div className="h-5 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="space-y-2">
          <div className="h-4 bg-gray-200 rounded"></div>
          <div className="h-4 bg-gray-200 rounded"></div>
          <div className="h-4 bg-gray-200 rounded w-5/6"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <p className="text-gray-500 text-sm">⚠️ Privacy data unavailable</p>
      </div>
    );
  }

  if (!privacyData) return null;

  const getPurposeLabel = (purpose) => {
    const labels = {
      'risk_assessment': 'Risk Assessment',
      'causality_analysis': 'Causality Analysis',
      'safety_evaluation': 'Safety Evaluation',
      'follow_up_decision': 'Follow-up Decision',
      'signal_detection': 'Signal Detection',
      'regulatory_compliance': 'Regulatory Compliance'
    };
    return labels[purpose] || purpose;
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <span>🔒</span>
          Privacy & Data Minimization
        </h3>
        {privacyData.minimization_active && (
          <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
            ✓ Active
          </span>
        )}
      </div>

      <div className="mb-4">
        <div className="text-sm text-gray-600 mb-2">
          <span className="font-medium">Retention Policy:</span> {privacyData.retention_days} days
        </div>
      </div>

      <div className="space-y-3">
        <div className="text-sm font-medium text-gray-700 mb-2">Exposed Data Fields:</div>
        {privacyData.exposed_fields && privacyData.exposed_fields.length > 0 ? (
          <div className="space-y-2">
            {privacyData.exposed_fields.map((field, index) => (
              <div
                key={index}
                className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200"
              >
                <div className="flex-shrink-0 mt-0.5">
                  <span className="text-green-600 font-bold">✓</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-gray-900 text-sm">
                    {field.field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </div>
                  <div className="text-xs text-gray-600 mt-1 flex items-center gap-1">
                    <span className="font-medium">Purpose:</span>
                    <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                      {getPurposeLabel(field.purpose)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-gray-500 bg-gray-50 p-3 rounded-lg">
            No data fields currently exposed
          </div>
        )}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex items-start gap-2 text-xs text-gray-600">
          <span>ℹ️</span>
          <span>
            All data is processed in compliance with regulatory requirements and deleted after retention period.
          </span>
        </div>
      </div>
    </div>
  );
};

export default PrivacyPanel;
