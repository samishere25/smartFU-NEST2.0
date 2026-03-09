'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import api from '@/lib/api';
import AgentTimeline from '@/components/AgentTimeline';
import AIConfidenceBadge from '@/components/AIConfidenceBadge';
import { ArrowLeft, RefreshCw } from 'lucide-react';

interface AgentMessage {
  agent: string;
  analysis?: string;
  risk_score?: number;
  category?: string;
  reasoning?: string;
  response_probability?: number;
  decision?: string;
}

interface CaseAnalysis {
  decision: string;
  priority: string;
  reasoning: string;
  risk_score: number;
  response_probability: number;
  prediction_confidence: number;
  engagement_risk: string;
  followup_priority: string;
  followup_frequency: number;
  escalation_needed: boolean;
  escalation_reason?: string;
  messages: AgentMessage[];
}

interface CaseAnalysisResponse {
  case_id: number;
  analysis: CaseAnalysis;
}

const CaseAnalysisPage: React.FC = () => {
  const params = useParams();
  const router = useRouter();
  const caseId = params?.caseId as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analysisData, setAnalysisData] = useState<CaseAnalysisResponse | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchAnalysis = async () => {
    if (!caseId) return;

    try {
      setLoading(true);
      setError(null);
      const response = await api.post<CaseAnalysisResponse>(`/api/cases/${caseId}/analyze`);
      setAnalysisData(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch case analysis');
      console.error('Error fetching case analysis:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAnalysis();
  }, [caseId]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchAnalysis();
  };

  if (loading && !refreshing) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-600 text-lg">Waiting for AI analysis…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full">
          <div className="text-red-500 text-5xl mb-4 text-center">⚠️</div>
          <h2 className="text-xl font-bold text-gray-900 mb-2 text-center">
            Error Loading Analysis
          </h2>
          <p className="text-gray-600 text-center mb-6">{error}</p>
          <div className="flex gap-3">
            <button
              onClick={() => router.back()}
              className="flex-1 px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors"
            >
              Go Back
            </button>
            <button
              onClick={handleRefresh}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!analysisData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center text-gray-500">
          <p className="text-lg">No analysis data available</p>
        </div>
      </div>
    );
  }

  const { analysis } = analysisData;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.back()}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  Case Analysis #{caseId}
                </h1>
                <p className="text-sm text-gray-600 mt-1">
                  Agentic Follow-Up Orchestration
                </p>
              </div>
            </div>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              {refreshing ? 'Refreshing…' : 'Refresh'}
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - AI Confidence & Summary */}
          <div className="lg:col-span-1 space-y-6">
            {/* AI Confidence Badge */}
            <AIConfidenceBadge
              confidence={analysis.response_probability}
              variance={0.05}
              caseCount={1456}
            />

            {/* Decision Summary Card */}
            <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Final Decision
              </h2>
              <div className="space-y-3">
                <div>
                  <p className="text-sm text-gray-600 mb-1">Decision:</p>
                  <p className="font-semibold text-gray-900 text-lg">
                    {analysis.decision}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">Priority:</p>
                  <span
                    className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${
                      analysis.priority === 'HIGH'
                        ? 'bg-red-100 text-red-800'
                        : analysis.priority === 'MEDIUM'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-green-100 text-green-800'
                    }`}
                  >
                    {analysis.priority}
                  </span>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">Risk Score:</p>
                  <div className="flex items-center">
                    <div className="flex-1 bg-gray-200 rounded-full h-2 mr-3">
                      <div
                        className={`h-2 rounded-full ${
                          analysis.risk_score > 0.7
                            ? 'bg-red-500'
                            : analysis.risk_score > 0.4
                            ? 'bg-yellow-500'
                            : 'bg-green-500'
                        }`}
                        style={{ width: `${analysis.risk_score * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium text-gray-700">
                      {(analysis.risk_score * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">
                    Response Probability:
                  </p>
                  <div className="flex items-center">
                    <div className="flex-1 bg-gray-200 rounded-full h-2 mr-3">
                      <div
                        className="h-2 rounded-full bg-blue-500"
                        style={{
                          width: `${analysis.response_probability * 100}%`,
                        }}
                      />
                    </div>
                    <span className="text-sm font-medium text-gray-700">
                      {(analysis.response_probability * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">
                    Prediction Confidence:
                  </p>
                  <div className="flex items-center">
                    <div className="flex-1 bg-gray-200 rounded-full h-2 mr-3">
                      <div
                        className="h-2 rounded-full bg-purple-500"
                        style={{
                          width: `${analysis.prediction_confidence * 100}%`,
                        }}
                      />
                    </div>
                    <span className="text-sm font-medium text-gray-700">
                      {(analysis.prediction_confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Engagement Risk Card */}
            <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Follow-Up Strategy
              </h2>
              <div className="space-y-3">
                <div>
                  <p className="text-sm text-gray-600 mb-1">
                    Engagement Risk:
                  </p>
                  <span
                    className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${
                      analysis.engagement_risk === 'HIGH_RISK_ENGAGEMENT'
                        ? 'bg-red-100 text-red-800'
                        : analysis.engagement_risk === 'MEDIUM_RISK_ENGAGEMENT'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-green-100 text-green-800'
                    }`}
                  >
                    {analysis.engagement_risk?.replace('_', ' ')}
                  </span>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">
                    Follow-Up Priority:
                  </p>
                  <span
                    className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${
                      analysis.followup_priority === 'CRITICAL'
                        ? 'bg-red-100 text-red-800'
                        : analysis.followup_priority === 'HIGH'
                        ? 'bg-orange-100 text-orange-800'
                        : analysis.followup_priority === 'MEDIUM'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-green-100 text-green-800'
                    }`}
                  >
                    {analysis.followup_priority}
                  </span>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">
                    Follow-Up Frequency:
                  </p>
                  <p className="font-semibold text-gray-900">
                    Every {analysis.followup_frequency} hours
                  </p>
                </div>
                {analysis.escalation_needed && (
                  <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <div className="flex items-start gap-2">
                      <span className="text-red-600 font-semibold text-sm">
                        ⚠️ Escalation Required
                      </span>
                    </div>
                    {analysis.escalation_reason && (
                      <p className="text-sm text-red-700 mt-1">
                        {analysis.escalation_reason}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Reasoning Card */}
            <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">
                Reasoning
              </h2>
              <p className="text-sm text-gray-700 leading-relaxed">
                {analysis.reasoning}
              </p>
            </div>
          </div>

          {/* Right Column - Agent Timeline */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900 mb-6">
                Agent Decision Flow
              </h2>
              <p className="text-sm text-gray-600 mb-6">
                Each AI agent analyzed the case step-by-step. Click to expand and see detailed reasoning.
              </p>
              <AgentTimeline messages={analysis.messages} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CaseAnalysisPage;
