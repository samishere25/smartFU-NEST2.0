/**
 * Feature-3: Adaptive Questioning UI Components
 * 
 * BACKWARD COMPATIBLE:
 * - All components gracefully handle missing data
 * - No crashes if Feature-3 fields are absent
 * - Existing UI behavior preserved
 * 
 * Components:
 * 1. DeadlineIndicator - Shows regulatory deadline urgency
 * 2. ResumedBanner - Shows resumed follow-up status
 * 3. AnsweredFieldsBadge - Badge for answered questions
 * 4. DuplicateQuestionLabel - Label for previously asked questions
 * 5. RLOptimizationTooltip - Subtle RL learning indicator
 * 6. ReviewerOverridePanel - Manual question injection UI
 * 7. CriticalQuestionWarning - Safety warning before submission
 */

import React, { useState } from 'react';

// ============================================================
// DEADLINE INDICATOR (Section 3)
// ============================================================
export const DeadlineIndicator = ({ daysToDeadline }) => {
  // Graceful fallback if no deadline data
  if (daysToDeadline === undefined || daysToDeadline === null) {
    return null;
  }

  const isUrgent = daysToDeadline <= 3;

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium ${
      isUrgent 
        ? 'bg-red-100 text-red-800 border border-red-300 animate-pulse' 
        : 'bg-gray-100 text-gray-700 border border-gray-200'
    }`}>
      <span className="text-lg">{isUrgent ? '⚠️' : '📅'}</span>
      <span>
        {isUrgent 
          ? 'Regulatory Urgency' 
          : `${daysToDeadline} days to deadline`
        }
      </span>
    </div>
  );
};

// ============================================================
// RESUMED FOLLOW-UP BANNER (Section 1)
// ============================================================
export const ResumedBanner = ({ answeredFields, isResumed }) => {
  // Only show if there are answered fields or explicit resume flag
  if ((!answeredFields || answeredFields.length === 0) && !isResumed) {
    return null;
  }

  return (
    <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded-r-lg mb-4">
      <div className="flex items-center gap-3">
        <span className="text-2xl">🔄</span>
        <div className="flex-1">
          <p className="font-semibold text-blue-900">
            Resumed Follow-up — Remaining Questions Only
          </p>
          {answeredFields && answeredFields.length > 0 && (
            <p className="text-sm text-blue-700 mt-1">
              {answeredFields.length} field(s) already answered and filtered out
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

// ============================================================
// ANSWERED FIELDS BADGE (Section 1)
// ============================================================
export const AnsweredFieldsBadge = () => {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 border border-green-300">
      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
      </svg>
      Answered
    </span>
  );
};

// ============================================================
// DUPLICATE QUESTION LABEL (Section 4)
// ============================================================
export const DuplicateQuestionLabel = ({ fieldName, previousAttempts, forceCritical }) => {
  // Don't show duplicate styling if force_critical
  if (forceCritical) {
    return null;
  }

  // Check if this field was previously asked
  if (!previousAttempts || !previousAttempts.includes(fieldName)) {
    return null;
  }

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-700 border border-orange-200">
      <span>🔁</span>
      Previously Asked
    </span>
  );
};

// ============================================================
// RL OPTIMIZATION TOOLTIP (Section 5)
// ============================================================
export const RLOptimizationTooltip = ({ scoreBreakdown }) => {
  // Only show if RL data is present
  if (!scoreBreakdown || scoreBreakdown.learned_reward === undefined) {
    return null;
  }

  // Only show if there's actual learned data (non-zero)
  if (scoreBreakdown.learned_reward === 0) {
    return null;
  }

  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div className="relative inline-block ml-2">
      <button
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onClick={() => setShowTooltip(!showTooltip)}
        className="text-indigo-500 hover:text-indigo-700 focus:outline-none"
        aria-label="Optimized by Learning Engine"
      >
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path d="M11 3a1 1 0 10-2 0v1a1 1 0 102 0V3zM15.657 5.757a1 1 0 00-1.414-1.414l-.707.707a1 1 0 001.414 1.414l.707-.707zM18 10a1 1 0 01-1 1h-1a1 1 0 110-2h1a1 1 0 011 1zM5.05 6.464A1 1 0 106.464 5.05l-.707-.707a1 1 0 00-1.414 1.414l.707.707zM5 10a1 1 0 01-1 1H3a1 1 0 110-2h1a1 1 0 011 1zM8 16v-1h4v1a2 2 0 11-4 0zM12 14c.015-.34.208-.646.477-.859a4 4 0 10-4.954 0c.27.213.462.519.476.859h4.002z" />
        </svg>
      </button>
      
      {showTooltip && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg whitespace-nowrap z-10">
          <div className="flex items-center gap-2">
            <span>✨</span>
            <span>Optimized by Learning Engine</span>
          </div>
          {/* Arrow */}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
        </div>
      )}
    </div>
  );
};

// ============================================================
// MANUAL OVERRIDE BADGE (Section 2)
// ============================================================
export const ManualOverrideBadge = ({ forceCritical }) => {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold ${
      forceCritical 
        ? 'bg-red-100 text-red-800 border-2 border-red-400' 
        : 'bg-purple-100 text-purple-800 border border-purple-300'
    }`}>
      <span>👤</span>
      Manual Override
    </span>
  );
};

// ============================================================
// REVIEWER NOTES PANEL (Section 2)
// Reviewer adds free-text notes; AI converts them to proper
// PV follow-up questions when "Build Combined Follow-Up" is clicked.
// ============================================================
export const ReviewerNotesPanel = ({
  onAddNote,
  existingQuestions = []
}) => {
  const [noteText, setNoteText] = useState('');
  const [priority, setPriority] = useState('NORMAL');
  const [addedNotes, setAddedNotes] = useState([]);

  const handleAdd = () => {
    if (!noteText.trim()) return;

    const newNote = {
      text: noteText.trim(),
      priority,
      isReviewerNote: true
    };

    setAddedNotes([...addedNotes, newNote]);

    // Callback to parent
    if (onAddNote) {
      onAddNote(newNote);
    }

    // Reset form
    setNoteText('');
    setPriority('NORMAL');
  };

  const handleRemove = (index) => {
    setAddedNotes(addedNotes.filter((_, i) => i !== index));
  };

  const priorityColors = {
    URGENT: 'bg-red-50 border-red-300 text-red-800',
    HIGH: 'bg-orange-50 border-orange-300 text-orange-800',
    NORMAL: 'bg-blue-50 border-blue-300 text-blue-800',
  };

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200 p-4 mt-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xl">📝</span>
        <h3 className="text-lg font-semibold text-gray-900">Reviewer Notes</h3>
      </div>
      <p className="text-xs text-gray-500 mb-4">
        Add notes about what additional information is needed. AI will convert these into proper follow-up questions when you build the combined package.
      </p>

      {/* Added Notes List */}
      {addedNotes.length > 0 && (
        <div className="mb-4 space-y-2">
          <p className="text-sm font-medium text-gray-700">Added Notes:</p>
          {addedNotes.map((note, idx) => (
            <div
              key={idx}
              className={`flex items-center justify-between p-2 rounded-lg border ${priorityColors[note.priority] || priorityColors.NORMAL}`}
            >
              <div className="flex-1">
                <p className="text-sm text-gray-900">{note.text}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold uppercase">{note.priority}</span>
                <button
                  onClick={() => handleRemove(idx)}
                  className="text-red-500 hover:text-red-700 text-sm"
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Note Form */}
      <div className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Reviewer Note
          </label>
          <textarea
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder="e.g., check concomitant medications, verify therapy duration, clarify onset timing..."
            rows={2}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-700">Priority:</label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="border border-gray-300 rounded-lg px-2 py-1 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="NORMAL">Normal</option>
              <option value="HIGH">High</option>
              <option value="URGENT">Urgent</option>
            </select>
          </div>

          <button
            onClick={handleAdd}
            disabled={!noteText.trim()}
            className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            + Add Note
          </button>
        </div>
      </div>
    </div>
  );
};

// Backward compat alias
export const ReviewerOverridePanel = ReviewerNotesPanel;

// ============================================================
// CRITICAL QUESTION WARNING (Section 6)
// ============================================================
export const CriticalQuestionWarning = ({ 
  show,
  questions, 
  onProceed, 
  onCancel,
  onClose // alias for onCancel
}) => {
  // Use show prop if provided, otherwise check questions
  const shouldShow = show !== undefined 
    ? show 
    : !questions?.some(q => q.criticality?.toUpperCase() === 'CRITICAL' || q.force_critical);

  // Handler for cancel - support both onCancel and onClose
  const handleCancel = onCancel || onClose;

  if (!shouldShow) {
    return null; // No warning needed
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0">
            <span className="text-4xl">⚠️</span>
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-bold text-gray-900 mb-2">
              No Critical Questions Selected
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              You are about to submit follow-up without any critical priority questions. 
              This may result in incomplete safety data collection.
            </p>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={handleCancel}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm font-medium cursor-pointer"
              >
                Review Selection
              </button>
              <button
                type="button"
                onClick={onProceed}
                className="px-4 py-2 text-white bg-orange-600 rounded-lg hover:bg-orange-700 text-sm font-medium cursor-pointer"
              >
                Proceed Anyway
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================
// FEATURE-3 STATUS HEADER (Combined Component)
// ============================================================
export const Feature3StatusHeader = ({ 
  daysToDeadline, 
  confidence, 
  riskScore,
  isResumed,
  answeredFields,
  rlEnabled
}) => {
  return (
    <div className="flex flex-wrap items-center gap-3 mb-4">
      {/* Risk Badge */}
      {riskScore !== undefined && (
        <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium ${
          riskScore >= 0.7 ? 'bg-red-100 text-red-800 border border-red-300' :
          riskScore >= 0.4 ? 'bg-yellow-100 text-yellow-800 border border-yellow-300' :
          'bg-green-100 text-green-800 border border-green-300'
        }`}>
          <span>📊</span>
          <span>Risk: {Math.round(riskScore * 100)}%</span>
        </div>
      )}

      {/* Confidence */}
      {confidence !== undefined && (
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium bg-blue-100 text-blue-800 border border-blue-200">
          <span>🎯</span>
          <span>Confidence: {Math.round(confidence * 100)}%</span>
        </div>
      )}

      {/* Deadline */}
      <DeadlineIndicator daysToDeadline={daysToDeadline} />

      {/* Resume Indicator */}
      {isResumed && (
        <div className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
          <span>🔄</span>
          <span>Resumed</span>
        </div>
      )}

      {/* RL Indicator (Subtle) */}
      {rlEnabled && (
        <div className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium bg-indigo-50 text-indigo-600 border border-indigo-200">
          <span>✨</span>
          <span>AI Optimized</span>
        </div>
      )}
    </div>
  );
};

// ============================================================
// REVIEWER OVERRIDE QUESTIONS PANEL (Direct question input)
// ============================================================
export const ReviewerQuestionsPanel = ({
  onAddQuestion,
  existingQuestions = []
}) => {
  const [questionText, setQuestionText] = useState('');
  const [priority, setPriority] = useState('NORMAL');
  const [addedQuestions, setAddedQuestions] = useState([]);

  const handleAdd = () => {
    if (!questionText.trim()) return;

    const newQuestion = {
      question: questionText.trim(),
      text: questionText.trim(),
      priority,
      isReviewerAdded: true,
      field: `reviewer_override_${Date.now()}`,
      criticality: priority === 'URGENT' ? 'CRITICAL' : priority === 'HIGH' ? 'HIGH' : 'MEDIUM'
    };

    setAddedQuestions([...addedQuestions, newQuestion]);

    // Callback to parent
    if (onAddQuestion) {
      onAddQuestion(newQuestion);
    }

    // Reset form
    setQuestionText('');
    setPriority('NORMAL');
  };

  const handleRemove = (index) => {
    const removed = addedQuestions.filter((_, i) => i !== index);
    setAddedQuestions(removed);
  };

  const priorityColors = {
    URGENT: 'bg-red-50 border-red-300 text-red-800',
    HIGH: 'bg-orange-50 border-orange-300 text-orange-800',
    NORMAL: 'bg-blue-50 border-blue-300 text-blue-800',
  };

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200 p-4 mt-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xl">✍️</span>
        <h3 className="text-lg font-semibold text-gray-900">Human Override Questions</h3>
      </div>
      <p className="text-xs text-gray-500 mb-4">
        Add your own follow-up questions directly. These will be included in the combined package along with AI-generated questions.
      </p>

      {/* Added Questions List */}
      {addedQuestions.length > 0 && (
        <div className="mb-4 space-y-2">
          <p className="text-sm font-medium text-gray-700">Your Questions ({addedQuestions.length}):</p>
          {addedQuestions.map((q, idx) => (
            <div
              key={idx}
              className={`flex items-start justify-between p-3 rounded-lg border ${priorityColors[q.priority] || priorityColors.NORMAL}`}
            >
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">{q.question}</p>
                <p className="text-xs text-gray-600 mt-1">Priority: {q.priority}</p>
              </div>
              <button
                onClick={() => handleRemove(idx)}
                className="text-red-500 hover:text-red-700 text-sm font-bold ml-2"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Add Question Form */}
      <div className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Override Question
          </label>
          <textarea
            value={questionText}
            onChange={(e) => setQuestionText(e.target.value)}
            placeholder="e.g., What concomitant medications was the patient taking? Please provide exact therapy duration from start to end date."
            rows={3}
            className="w-full px-3 py-2 border border-blue-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-700">Priority:</label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="border border-gray-300 rounded-lg px-2 py-1 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="NORMAL">Normal</option>
              <option value="HIGH">High</option>
              <option value="URGENT">Urgent</option>
            </select>
          </div>

          <button
            onClick={handleAdd}
            disabled={!questionText.trim()}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            + Add Question
          </button>
        </div>
      </div>
    </div>
  );
};

export default {
  DeadlineIndicator,
  ResumedBanner,
  AnsweredFieldsBadge,
  DuplicateQuestionLabel,
  RLOptimizationTooltip,
  ManualOverrideBadge,
  ReviewerNotesPanel,
  ReviewerOverridePanel,
  ReviewerQuestionsPanel,
  CriticalQuestionWarning,
  Feature3StatusHeader
};
