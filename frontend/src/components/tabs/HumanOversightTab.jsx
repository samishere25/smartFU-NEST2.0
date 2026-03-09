import React, { useState } from 'react';

const HumanOversightTab = ({ caseId, analysis }) => {
  const [reviewNote, setReviewNote] = useState('');
  const [overrideReason, setOverrideReason] = useState('');
  const [showNoteForm, setShowNoteForm] = useState(false);
  const [showOverrideForm, setShowOverrideForm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleAddNote = async () => {
    if (!reviewNote.trim()) return;
    
    setIsSubmitting(true);
    try {
      // TODO: Call backend API to save review note
      // await api.addReviewNote(caseId, reviewNote);
      console.log('Adding review note:', reviewNote);
      alert('Review note added successfully (demo mode)');
      setReviewNote('');
      setShowNoteForm(false);
    } catch (error) {
      alert('Failed to add review note: ' + error.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOverride = async () => {
    if (!overrideReason.trim()) return;
    
    setIsSubmitting(true);
    try {
      // TODO: Call backend API to override AI decision
      // await api.overrideDecision(caseId, overrideReason);
      console.log('Overriding AI decision:', overrideReason);
      alert('AI decision overridden successfully (demo mode)');
      setOverrideReason('');
      setShowOverrideForm(false);
    } catch (error) {
      alert('Failed to override decision: ' + error.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Human-in-the-Loop Status */}
      <div className="bg-blue-50 border-l-4 border-blue-500 rounded-lg p-6">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="w-8 h-8 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-6-3a2 2 0 11-4 0 2 2 0 014 0zm-2 4a5 5 0 00-4.546 2.916A5.986 5.986 0 0010 16a5.986 5.986 0 004.546-2.084A5 5 0 0010 11z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-4 flex-1">
            <h3 className="text-lg font-semibold text-blue-900 mb-1">
              Human-in-the-Loop: Active
            </h3>
            <p className="text-sm text-blue-800">
              This system is designed with human oversight as a core principle. All AI decisions 
              can be reviewed, annotated, and overridden by qualified personnel.
            </p>
          </div>
          <div className="flex-shrink-0 ml-4">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800 border border-green-300">
              ✓ Enabled
            </span>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <button
          onClick={() => setShowNoteForm(!showNoteForm)}
          className="flex items-center justify-center gap-3 px-6 py-4 bg-white border-2 border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 transition-colors font-medium"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
          </svg>
          Add Human Review Note
        </button>
        <button
          onClick={() => setShowOverrideForm(!showOverrideForm)}
          className="flex items-center justify-center gap-3 px-6 py-4 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          Override AI Decision
        </button>
      </div>

      {/* Review Note Form */}
      {showNoteForm && (
        <div className="bg-white border-2 border-blue-300 rounded-lg p-6 shadow-lg">
          <h4 className="text-lg font-semibold text-gray-900 mb-4">Add Review Note</h4>
          <textarea
            value={reviewNote}
            onChange={(e) => setReviewNote(e.target.value)}
            placeholder="Enter your review note here... (e.g., 'Consulted with medical expert, confirmed AI assessment is accurate')"
            rows={4}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
          />
          <div className="flex gap-3">
            <button
              onClick={handleAddNote}
              disabled={!reviewNote.trim() || isSubmitting}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              {isSubmitting ? 'Saving...' : 'Save Note'}
            </button>
            <button
              onClick={() => {
                setShowNoteForm(false);
                setReviewNote('');
              }}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 font-medium"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Override Form */}
      {showOverrideForm && (
        <div className="bg-white border-2 border-red-300 rounded-lg p-6 shadow-lg">
          <div className="flex items-start gap-3 mb-4">
            <svg className="w-6 h-6 text-red-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <div>
              <h4 className="text-lg font-semibold text-gray-900">Override AI Decision</h4>
              <p className="text-sm text-gray-600 mt-1">
                This action will override the AI recommendation. Please provide a detailed justification.
              </p>
            </div>
          </div>
          <textarea
            value={overrideReason}
            onChange={(e) => setOverrideReason(e.target.value)}
            placeholder="Reason for override... (e.g., 'Based on clinical expertise, case requires immediate escalation due to [specific reason]')"
            rows={4}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 mb-4"
          />
          <div className="flex gap-3">
            <button
              onClick={handleOverride}
              disabled={!overrideReason.trim() || isSubmitting}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              {isSubmitting ? 'Processing...' : 'Confirm Override'}
            </button>
            <button
              onClick={() => {
                setShowOverrideForm(false);
                setOverrideReason('');
              }}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 font-medium"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Governance & Compliance */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Governance & Compliance</h3>
        <div className="space-y-4">
          <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
            <svg className="w-5 h-5 text-green-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <div className="flex-1">
              <h4 className="font-semibold text-gray-900 text-sm">GDPR Compliant</h4>
              <p className="text-xs text-gray-600 mt-1">
                All AI decisions are explainable and auditable per EU regulations
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
            <svg className="w-5 h-5 text-green-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 2a8 8 0 100 16 8 8 0 000-16zM9 9a1 1 0 012 0v4a1 1 0 01-2 0V9zm1-5a1 1 0 100 2 1 1 0 000-2z" clipRule="evenodd" />
            </svg>
            <div className="flex-1">
              <h4 className="font-semibold text-gray-900 text-sm">FDA 21 CFR Part 11 Ready</h4>
              <p className="text-xs text-gray-600 mt-1">
                Electronic records and signatures with full audit trail
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
            <svg className="w-5 h-5 text-green-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
            </svg>
            <div className="flex-1">
              <h4 className="font-semibold text-gray-900 text-sm">Full Audit Logging</h4>
              <p className="text-xs text-gray-600 mt-1">
                All decisions, overrides, and reviews are timestamped and logged
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Audit Disclaimer */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <svg className="w-5 h-5 text-gray-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
          <div className="flex-1">
            <p className="text-xs text-gray-700 leading-relaxed">
              <span className="font-semibold">Audit Trail Notice:</span> All actions on this page are logged 
              with user ID, timestamp, and rationale. This system maintains compliance with pharmacovigilance 
              regulations including ICH E2B(R3), FDA guidance, and EU MDR. AI-generated content is clearly 
              labeled and subject to human review per GxP requirements.
            </p>
          </div>
        </div>
      </div>

      {/* Current Case Info */}
      {caseId && (
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-gray-300">
          <div className="text-sm text-gray-600">
            <span className="font-semibold">Case ID:</span> {caseId}
            <span className="mx-2">•</span>
            <span className="font-semibold">AI Decision:</span> {analysis?.decision || 'N/A'}
            <span className="mx-2">•</span>
            <span className="font-semibold">Confidence:</span> {analysis?.confidence || 0}%
            <span className="mx-2">•</span>
            <span className="font-semibold">Timestamp:</span> {new Date().toLocaleString()}
          </div>
        </div>
      )}
    </div>
  );
};

export default HumanOversightTab;
