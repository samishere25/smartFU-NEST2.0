'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
  const router = useRouter();
  const [caseId, setCaseId] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (caseId.trim()) {
      router.push(`/case-analysis/${caseId}`);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">SmartFU</h1>
          <p className="text-gray-600">Agentic Follow-Up Orchestration</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label
              htmlFor="caseId"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Enter Case ID
            </label>
            <input
              type="text"
              id="caseId"
              value={caseId}
              onChange={(e) => setCaseId(e.target.value)}
              placeholder="e.g., 1, 2, 3..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={!caseId.trim()}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Analyze Case
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-gray-200">
          <p className="text-sm text-gray-600 text-center mb-4">
            Quick Links:
          </p>
          <div className="grid grid-cols-3 gap-2">
            {[1, 2, 3].map((id) => (
              <button
                key={id}
                onClick={() => router.push(`/case-analysis/${id}`)}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium"
              >
                Case {id}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <p className="text-xs text-blue-800">
            <strong>ℹ️ Feature 1:</strong> Agentic Follow-Up Orchestration
            <br />
            <span className="text-blue-600">
              View AI agent decision flow with real backend data
            </span>
          </p>
        </div>
      </div>
    </div>
  );
}
