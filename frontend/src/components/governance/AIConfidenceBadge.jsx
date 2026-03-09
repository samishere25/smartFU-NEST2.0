import React, { useState, useEffect } from 'react';
import { api } from '../../utils/api';

const AIConfidenceBadge = ({ caseId }) => {
  const [trustData, setTrustData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (caseId) {
      fetchTrustData();
    }
  }, [caseId]);

  const fetchTrustData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getCaseTrust(caseId);
      setTrustData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-gray-50 border-2 border-gray-200 rounded-lg p-4 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/3 mb-3"></div>
        <div className="space-y-2">
          <div className="h-3 bg-gray-200 rounded"></div>
          <div className="h-3 bg-gray-200 rounded w-5/6"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border-2 border-red-200 rounded-lg p-4">
        <p className="text-red-700 text-sm">⚠️ Unable to load AI confidence data</p>
      </div>
    );
  }

  if (!trustData) return null;

  const getConfidenceLevelConfig = (level) => {
    switch (level?.toUpperCase()) {
      case 'HIGH':
        return {
          color: 'bg-green-50 border-green-500 text-green-800',
          icon: '✓',
          badgeColor: 'bg-green-100 text-green-800'
        };
      case 'MEDIUM':
        return {
          color: 'bg-yellow-50 border-yellow-500 text-yellow-800',
          icon: '⚠',
          badgeColor: 'bg-yellow-100 text-yellow-800'
        };
      case 'LOW':
        return {
          color: 'bg-red-50 border-red-500 text-red-800',
          icon: '!',
          badgeColor: 'bg-red-100 text-red-800'
        };
      default:
        return {
          color: 'bg-gray-50 border-gray-500 text-gray-800',
          icon: '?',
          badgeColor: 'bg-gray-100 text-gray-800'
        };
    }
  };

  const config = getConfidenceLevelConfig(trustData.confidence_level);
  const confidencePercent = (trustData.confidence_score * 100).toFixed(1);
  const variancePercent = (trustData.variance * 100).toFixed(1);

  return (
    <div className={`rounded-lg border-2 p-4 ${config.color} shadow-sm`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{config.icon}</span>
          <span className="font-semibold text-sm">AI Confidence & Trust</span>
        </div>
        <span className={`px-3 py-1 rounded-full font-bold text-sm ${config.badgeColor}`}>
          {trustData.confidence_level}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="bg-white bg-opacity-50 rounded p-2">
          <div className="text-xs text-gray-600 mb-1">Confidence Score</div>
          <div className="text-2xl font-bold">{confidencePercent}%</div>
        </div>
        <div className="bg-white bg-opacity-50 rounded p-2">
          <div className="text-xs text-gray-600 mb-1">Similar Cases</div>
          <div className="text-2xl font-bold">{trustData.similar_cases.toLocaleString()}</div>
        </div>
      </div>

      <div className="space-y-2 text-sm">
        <div className="flex items-start gap-2">
          <span>📊</span>
          <span>Variance Range: ±{variancePercent}%</span>
        </div>
        
        {trustData.human_override_allowed && (
          <div className="flex items-start gap-2">
            <span>👤</span>
            <span className="font-medium">Human override available</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default AIConfidenceBadge;
