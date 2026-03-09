'use client';

import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface AgentMessage {
  agent: string;
  analysis?: string;
  risk_score?: number;
  category?: string;
  reasoning?: string;
  response_probability?: number;
  decision?: string;
}

interface AgentTimelineProps {
  messages: AgentMessage[];
}

const AgentTimeline: React.FC<AgentTimelineProps> = ({ messages }) => {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(0);

  const toggleExpand = (index: number) => {
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  const getAgentIcon = (agentName: string) => {
    switch (agentName) {
      case 'DataCompleteness':
        return '📋';
      case 'RiskAssessment':
        return '⚠️';
      case 'ResponseStrategy':
        return '🎯';
      case 'Escalation':
        return '🚨';
      default:
        return '🤖';
    }
  };

  const getAgentColor = (agentName: string) => {
    switch (agentName) {
      case 'DataCompleteness':
        return 'border-blue-500 bg-blue-50';
      case 'RiskAssessment':
        return 'border-orange-500 bg-orange-50';
      case 'ResponseStrategy':
        return 'border-purple-500 bg-purple-50';
      case 'Escalation':
        return 'border-red-500 bg-red-50';
      default:
        return 'border-gray-500 bg-gray-50';
    }
  };

  if (!messages || messages.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No agent analysis available
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {messages.map((message, index) => {
        const isExpanded = expandedIndex === index;
        const isLast = index === messages.length - 1;

        return (
          <div key={index} className="flex">
            {/* Timeline line */}
            <div className="flex flex-col items-center mr-4">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center text-xl ${getAgentColor(
                  message.agent
                )} border-2`}
              >
                {getAgentIcon(message.agent)}
              </div>
              {!isLast && (
                <div className="w-0.5 h-full bg-gray-300 mt-2 min-h-[40px]" />
              )}
            </div>

            {/* Content */}
            <div className="flex-1 pb-8">
              <button
                onClick={() => toggleExpand(index)}
                className="w-full text-left bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow border border-gray-200"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-gray-900 text-lg">
                      {message.agent}
                    </h3>
                    {message.decision && (
                      <p className="text-sm text-gray-600 mt-1">
                        Decision: <span className="font-medium">{message.decision}</span>
                      </p>
                    )}
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="w-5 h-5 text-gray-500" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-gray-500" />
                  )}
                </div>
              </button>

              {/* Expanded content */}
              {isExpanded && (
                <div className="mt-3 bg-gray-50 rounded-lg p-4 border border-gray-200">
                  {message.analysis && (
                    <div className="mb-3">
                      <p className="text-sm font-medium text-gray-700 mb-1">
                        Analysis:
                      </p>
                      <p className="text-sm text-gray-600">{message.analysis}</p>
                    </div>
                  )}

                  {message.reasoning && (
                    <div className="mb-3">
                      <p className="text-sm font-medium text-gray-700 mb-1">
                        Reasoning:
                      </p>
                      <p className="text-sm text-gray-600">{message.reasoning}</p>
                    </div>
                  )}

                  {message.risk_score !== undefined && (
                    <div className="mb-3">
                      <p className="text-sm font-medium text-gray-700 mb-1">
                        Risk Score:
                      </p>
                      <div className="flex items-center">
                        <div className="flex-1 bg-gray-200 rounded-full h-2 mr-3">
                          <div
                            className={`h-2 rounded-full ${
                              message.risk_score > 0.7
                                ? 'bg-red-500'
                                : message.risk_score > 0.4
                                ? 'bg-yellow-500'
                                : 'bg-green-500'
                            }`}
                            style={{ width: `${message.risk_score * 100}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium text-gray-700">
                          {(message.risk_score * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  )}

                  {message.response_probability !== undefined && (
                    <div className="mb-3">
                      <p className="text-sm font-medium text-gray-700 mb-1">
                        Response Probability:
                      </p>
                      <div className="flex items-center">
                        <div className="flex-1 bg-gray-200 rounded-full h-2 mr-3">
                          <div
                            className="h-2 rounded-full bg-blue-500"
                            style={{
                              width: `${message.response_probability * 100}%`,
                            }}
                          />
                        </div>
                        <span className="text-sm font-medium text-gray-700">
                          {(message.response_probability * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  )}

                  {message.category && (
                    <div className="mb-3">
                      <p className="text-sm font-medium text-gray-700 mb-1">
                        Category:
                      </p>
                      <p className="text-sm text-gray-600">{message.category}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default AgentTimeline;
