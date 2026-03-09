import React from 'react';

const AIConfidenceBadge = ({ confidence, caseCount }) => {
  const getConfidenceLevel = (conf) => {
    if (conf >= 0.8) return { level: 'HIGH', color: 'bg-green-100 border-green-500 text-green-800' };
    if (conf >= 0.6) return { level: 'MEDIUM', color: 'bg-yellow-100 border-yellow-500 text-yellow-800' };
    return { level: 'LOW', color: 'bg-red-100 border-red-500 text-red-800' };
  };

  const { level, color } = getConfidenceLevel(confidence);

  return (
    <div className={`rounded-lg border-2 p-4 ${color}`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-semibold">🤖 AI Decision Quality:</span>
        <span className="font-bold text-lg">{level}</span>
      </div>
      
      <div className="space-y-2 text-sm">
        <div className="flex items-start">
          <span className="mr-2">✓</span>
          <span>Confidence: {(confidence * 100).toFixed(1)}%</span>
        </div>
        
        {caseCount && (
          <div className="flex items-start">
            <span className="mr-2">✓</span>
            <span>Based on {caseCount.toLocaleString()} similar cases</span>
          </div>
        )}
        
        <div className="flex items-start">
          <span className="mr-2">✓</span>
          <span>Human override available</span>
        </div>
      </div>
    </div>
  );
};

export default AIConfidenceBadge;
