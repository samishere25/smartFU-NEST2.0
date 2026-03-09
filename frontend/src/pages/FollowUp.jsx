import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../utils/api';
import { useCaseEvents } from '../context/CaseEventContext';

const FollowUp = () => {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const { emitCaseUpdate } = useCaseEvents();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [followUpData, setFollowUpData] = useState(null);
  const [showDeclineModal, setShowDeclineModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Micro-question flow state
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [answer, setAnswer] = useState('');
  const [multiSelectAnswers, setMultiSelectAnswers] = useState([]);
  const [completenessScore, setCompletenessScore] = useState(0);
  const [answeredQuestions, setAnsweredQuestions] = useState([]);
  const [isComplete, setIsComplete] = useState(false);
  const [validationError, setValidationError] = useState('');

  useEffect(() => {
    loadFollowUpData();
  }, [caseId]);

  const loadFollowUpData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Try loading context data (non-blocking — used only for header info)
      try {
        const data = await api.getFollowUpQuestions(caseId);
        setFollowUpData(data);
      } catch {
        // Context load is optional — proceed to micro-question flow anyway
        setFollowUpData({ case_id: caseId });
      }

      // Always fetch the first question
      await fetchNextQuestion();
    } catch (err) {
      setError(err.message || 'Failed to load follow-up information');
    } finally {
      setLoading(false);
    }
  };

  const fetchNextQuestion = async () => {
    try {
      const data = await api.getNextQuestion(caseId);

      if (!data || !data.next_question) {
        // No more questions - follow-up is complete
        setIsComplete(true);
        setCurrentQuestion(null);
        setCompletenessScore(data?.completeness_score ?? 1.0);
        return;
      }

      setCurrentQuestion(data.next_question);
      setCompletenessScore(data.completeness_score ?? completenessScore);
      setAnswer('');
      setMultiSelectAnswers([]);
      setValidationError('');
    } catch (err) {
      // If the endpoint returns no question, treat as complete
      if (err.message?.includes('No more questions') || err.message?.includes('complete')) {
        setIsComplete(true);
        setCurrentQuestion(null);
      } else {
        setError(err.message || 'Failed to load next question');
      }
    }
  };

  // Input validation based on question_type
  const validateAnswer = (value, questionType) => {
    if (questionType === 'number') {
      if (!/^\d+$/.test(value)) return 'Please enter numbers only';
      const num = parseInt(value, 10);
      if (num < 0 || num > 150) return 'Please enter a valid age (0-150)';
    }
    if (questionType === 'text' || questionType === 'textarea') {
      if (/^\d+$/.test(value.trim())) return 'Please enter a description, not just a number';
    }
    if (questionType === 'date') {
      if (!value) return 'Please select a date';
    }
    return '';
  };

  const handleAnswerChange = (value) => {
    setAnswer(value);
    if (validationError) {
      const err = validateAnswer(value, currentQuestion?.question_type);
      setValidationError(err);
    }
  };

  const handleNumberInput = (e) => {
    // Only allow digits
    const val = e.target.value.replace(/[^0-9]/g, '');
    setAnswer(val);
    if (validationError) setValidationError('');
  };

  const handleSubmitAnswer = async () => {
    if (!currentQuestion) return;

    const finalAnswer = currentQuestion.question_type === 'multi_select'
      ? multiSelectAnswers
      : answer;

    if (
      (typeof finalAnswer === 'string' && !finalAnswer.trim()) ||
      (Array.isArray(finalAnswer) && finalAnswer.length === 0)
    ) return;

    // Validate before submitting
    if (typeof finalAnswer === 'string') {
      const err = validateAnswer(finalAnswer, currentQuestion.question_type);
      if (err) {
        setValidationError(err);
        return;
      }
    }
    setValidationError('');

    try {
      setSubmitting(true);

      const result = await api.submitFollowUpAnswer(
        caseId,
        currentQuestion.field_name,
        finalAnswer
      );

      // Track answered question
      setAnsweredQuestions(prev => [...prev, {
        question: currentQuestion.question_text || currentQuestion.text,
        field_name: currentQuestion.field_name,
        answer: Array.isArray(finalAnswer) ? finalAnswer.join(', ') : finalAnswer
      }]);

      // Update completeness from response
      if (result?.completeness_score !== undefined) {
        setCompletenessScore(result.completeness_score);
      }

      // Check if complete
      if (result?.is_complete || result?.completeness_score >= 0.85) {
        setIsComplete(true);
        setCurrentQuestion(null);
        setCompletenessScore(result.completeness_score ?? 1.0);

        emitCaseUpdate({
          type: 'FOLLOWUP_SUBMITTED',
          caseId: caseId,
          metadata: { answeredCount: answeredQuestions.length + 1 }
        });
      } else {
        // Fetch next question
        await fetchNextQuestion();
      }
    } catch (err) {
      setError(err.message || 'Failed to submit answer');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDecline = async () => {
    try {
      setSubmitting(true);
      await api.declineFollowUp(caseId);

      emitCaseUpdate({
        type: 'FOLLOWUP_DECLINED',
        caseId: caseId,
        metadata: {}
      });

      setShowDeclineModal(false);
      navigate(`/cases/${caseId}`);
    } catch (err) {
      setError(err.message || 'Failed to decline follow-up');
      setSubmitting(false);
    }
  };

  const handleMultiSelectToggle = (value) => {
    setMultiSelectAnswers(prev =>
      prev.includes(value)
        ? prev.filter(v => v !== value)
        : [...prev, value]
    );
  };

  const progressPercent = Math.round(completenessScore * 100);

  // --- RENDER: Loading ---
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading follow-up information...</p>
        </div>
      </div>
    );
  }

  // --- RENDER: Error ---
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6">
          <div className="text-red-600 text-center">
            <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <h3 className="mt-4 text-lg font-semibold">Error Loading Follow-Up</h3>
            <p className="mt-2 text-sm text-gray-600">{error}</p>
            <div className="mt-4 flex gap-3 justify-center">
              <button
                onClick={() => { setError(null); loadFollowUpData(); }}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Retry
              </button>
              <button
                onClick={() => navigate('/cases')}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Return to Cases
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // --- RENDER: Complete ---
  if (isComplete) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="max-w-lg w-full bg-white rounded-2xl shadow-lg p-8">
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-green-100">
              <svg className="h-10 w-10 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h3 className="mt-4 text-2xl font-bold text-gray-900">Follow-up information complete.</h3>
            <p className="mt-3 text-gray-600">
              Thank you for providing this information. It helps protect patient safety and meet regulatory compliance requirements.
            </p>
            <div className="mt-4 text-sm text-gray-500">
              {answeredQuestions.length} question{answeredQuestions.length !== 1 ? 's' : ''} answered
            </div>
          </div>

          {/* Summary of answered questions */}
          {answeredQuestions.length > 0 && (
            <div className="mt-6 bg-gray-50 rounded-lg p-4 border border-gray-200">
              <h4 className="text-sm font-semibold text-gray-700 mb-3">Your Responses</h4>
              <div className="space-y-3">
                {answeredQuestions.map((item, i) => (
                  <div key={i} className="pb-3 border-b border-gray-200 last:border-0 last:pb-0">
                    <p className="text-xs text-gray-500">{item.question}</p>
                    <p className="text-sm font-medium text-gray-900 mt-0.5">{item.answer}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="mt-6 space-y-2">
            <button
              onClick={() => navigate(`/cases/${caseId}`)}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              View Case Details
            </button>
            <button
              onClick={() => navigate('/dashboard')}
              className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
            >
              Return to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  // --- RENDER: Interactive Micro-Question Flow ---
  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-2xl mx-auto px-4">

        {/* Trust Header */}
        <div className="bg-white rounded-xl shadow-md border border-blue-100 p-5 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                SmartFU Safety Follow-Up
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                Case: <span className="font-mono">{followUpData?.case_id || caseId}</span>
              </p>
            </div>
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
              <svg className="mr-1 h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              Verified
            </span>
          </div>
        </div>

        {/* Progress Indicator */}
        <div className="bg-white rounded-xl shadow-md p-5 mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Data Completeness</span>
            <span className="text-sm font-bold text-blue-600">{progressPercent}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className={`h-2.5 rounded-full transition-all duration-500 ${
                progressPercent >= 85 ? 'bg-green-500' :
                progressPercent >= 50 ? 'bg-blue-500' :
                'bg-amber-500'
              }`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          {answeredQuestions.length > 0 && (
            <p className="text-xs text-gray-400 mt-2">
              {answeredQuestions.length} question{answeredQuestions.length !== 1 ? 's' : ''} answered
            </p>
          )}
        </div>

        {/* Previous Answers (last 2) */}
        {answeredQuestions.length > 0 && (
          <div className="mb-4 space-y-2">
            {answeredQuestions.slice(-2).map((item, i) => (
              <div key={i} className="bg-white rounded-lg border border-gray-200 p-3 opacity-60">
                <p className="text-xs text-gray-500">{item.question}</p>
                <p className="text-sm text-gray-800 mt-0.5 flex items-center gap-1">
                  <svg className="h-3.5 w-3.5 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  {item.answer}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Question Card */}
        {currentQuestion && (
          <div className="bg-white rounded-xl shadow-lg border-2 border-blue-100 p-6 mb-6">
            {/* Question Header */}
            <div className="flex items-start justify-between mb-1">
              <h2 className="text-lg font-semibold text-gray-900 flex-1 leading-snug">
                {currentQuestion.question_text || currentQuestion.text}
              </h2>
              {currentQuestion.criticality && (
                <span className={`ml-3 flex-shrink-0 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                  currentQuestion.criticality === 'CRITICAL' ? 'bg-red-100 text-red-800' :
                  currentQuestion.criticality === 'HIGH' ? 'bg-orange-100 text-orange-800' :
                  currentQuestion.criticality === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {currentQuestion.criticality}
                </span>
              )}
            </div>

            {/* Why it matters */}
            {currentQuestion.why_it_matters && (
              <p className="text-xs text-gray-500 mb-4 mt-1">{currentQuestion.why_it_matters}</p>
            )}

            {/* Answer Input - rendered by question_type */}
            <div className="mt-4">

              {/* BOOLEAN: Yes / No buttons */}
              {currentQuestion.question_type === 'boolean' && (
                <div className="flex gap-3">
                  <button
                    onClick={() => setAnswer('Yes')}
                    className={`flex-1 py-3 px-4 rounded-lg text-sm font-semibold border-2 transition-all ${
                      answer === 'Yes'
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    Yes
                  </button>
                  <button
                    onClick={() => setAnswer('No')}
                    className={`flex-1 py-3 px-4 rounded-lg text-sm font-semibold border-2 transition-all ${
                      answer === 'No'
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    No
                  </button>
                </div>
              )}

              {/* NUMBER: Numeric input — digits only */}
              {currentQuestion.question_type === 'number' && (
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  value={answer}
                  onChange={handleNumberInput}
                  placeholder="Enter a number..."
                  className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm ${
                    validationError ? 'border-red-400' : 'border-gray-300'
                  }`}
                />
              )}

              {/* TEXT: Text input — no pure-number answers */}
              {(currentQuestion.question_type === 'text' || currentQuestion.question_type === 'textarea' || !currentQuestion.question_type) && (
                <textarea
                  value={answer}
                  onChange={(e) => handleAnswerChange(e.target.value)}
                  placeholder="Type your answer..."
                  rows={3}
                  className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm resize-none ${
                    validationError ? 'border-red-400' : 'border-gray-300'
                  }`}
                />
              )}

              {/* SELECT: Dropdown */}
              {currentQuestion.question_type === 'select' && currentQuestion.options && (
                <div className="space-y-2">
                  {currentQuestion.options.map((option, i) => {
                    const optValue = typeof option === 'string' ? option : option.value;
                    const optLabel = typeof option === 'string' ? option : option.label;
                    return (
                      <button
                        key={i}
                        onClick={() => setAnswer(optValue)}
                        className={`w-full text-left py-3 px-4 rounded-lg text-sm border-2 transition-all ${
                          answer === optValue
                            ? 'border-blue-500 bg-blue-50 text-blue-700 font-medium'
                            : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        {optLabel}
                      </button>
                    );
                  })}
                </div>
              )}

              {/* MULTI_SELECT: Checkbox list */}
              {currentQuestion.question_type === 'multi_select' && currentQuestion.options && (
                <div className="space-y-2">
                  {currentQuestion.options.map((option, i) => {
                    const optValue = typeof option === 'string' ? option : option.value;
                    const optLabel = typeof option === 'string' ? option : option.label;
                    const isChecked = multiSelectAnswers.includes(optValue);
                    return (
                      <button
                        key={i}
                        onClick={() => handleMultiSelectToggle(optValue)}
                        className={`w-full text-left py-3 px-4 rounded-lg text-sm border-2 transition-all flex items-center gap-3 ${
                          isChecked
                            ? 'border-blue-500 bg-blue-50 text-blue-700 font-medium'
                            : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        <div className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 ${
                          isChecked ? 'bg-blue-500 border-blue-500' : 'border-gray-300'
                        }`}>
                          {isChecked && (
                            <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                          )}
                        </div>
                        {optLabel}
                      </button>
                    );
                  })}
                </div>
              )}

              {/* DATE: Date picker */}
              {currentQuestion.question_type === 'date' && (
                <input
                  type="date"
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm"
                />
              )}
            </div>

            {/* Validation Error */}
            {validationError && (
              <p className="mt-2 text-sm text-red-600 flex items-center gap-1">
                <svg className="h-4 w-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
                {validationError}
              </p>
            )}

            {/* Submit Answer Button */}
            <button
              onClick={handleSubmitAnswer}
              disabled={
                submitting || !!validationError ||
                (currentQuestion.question_type === 'multi_select' ? multiSelectAnswers.length === 0 : !answer.toString().trim())
              }
              className="mt-3 w-full py-3 px-4 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors text-sm"
            >
              {submitting ? (
                <span className="flex items-center justify-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Submitting...
                </span>
              ) : (
                'Submit & Continue'
              )}
            </button>
          </div>
        )}

        {/* Privacy & Decline row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <span>Encrypted & audit-logged</span>
          </div>
          <button
            onClick={() => setShowDeclineModal(true)}
            disabled={submitting}
            className="text-xs text-gray-400 hover:text-gray-600 underline"
          >
            Decline Follow-Up
          </button>
        </div>

      </div>

      {/* Decline Confirmation Modal */}
      {showDeclineModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-3">Decline Follow-Up?</h3>
            <p className="text-sm text-gray-600 mb-6">
              Are you sure you want to decline this follow-up request? This may impact our ability to assess patient safety for this case.
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleDecline}
                disabled={submitting}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-red-400"
              >
                {submitting ? 'Processing...' : 'Yes, Decline'}
              </button>
              <button
                onClick={() => setShowDeclineModal(false)}
                disabled={submitting}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FollowUp;
