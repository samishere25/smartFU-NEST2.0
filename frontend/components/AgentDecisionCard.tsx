import React from 'react';

interface AgentDecisionCardProps {
  agentName: string;
  summary: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH';
}

const AgentDecisionCard: React.FC<AgentDecisionCardProps> = ({
  agentName,
  summary,
  priority,
}) => {
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'HIGH':
        return 'bg-red-100 text-red-800 border-red-300';
      case 'MEDIUM':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'LOW':
        return 'bg-green-100 text-green-800 border-green-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'HIGH':
        return '🔴';
      case 'MEDIUM':
        return '🟡';
      case 'LOW':
        return '🟢';
      default:
        return '⚪';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">{agentName}</h3>
        <span
          className={`px-3 py-1 rounded-full text-xs font-medium border ${getPriorityColor(
            priority
          )}`}
        >
          {getPriorityIcon(priority)} {priority}
        </span>
      </div>
      <p className="text-gray-700 text-sm leading-relaxed">{summary}</p>
    </div>
  );
};

export default AgentDecisionCard;
