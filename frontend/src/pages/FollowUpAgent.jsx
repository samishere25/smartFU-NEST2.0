// Follow-Up Agent Page (Public - Email/WhatsApp)
// Same UI as internal FollowUp, but uses token-based auth (no login needed)

import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

const API_BASE = '';

export default function FollowUpAgent() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const [state, setState] = useState('loading');
  const [language, setLanguage] = useState('');
  const [caseContext, setCaseContext] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [progress, setProgress] = useState(null);
  const [answer, setAnswer] = useState('');
  const [completionMessage, setCompletionMessage] = useState('');
  const [error, setError] = useState('');
  const [conversationHistory, setConversationHistory] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [validationError, setValidationError] = useState('');
  const [languageOptions, setLanguageOptions] = useState([]);
  const [langSearch, setLangSearch] = useState('');
  const [uiStrings, setUiStrings] = useState({
    submit_button: 'Submit & Continue',
    submitting: 'Submitting...',
    enter_number: 'Enter a number...',
    type_answer: 'Type your answer...',
    select_date: 'Select a date',
    completion_title: 'Follow-up information complete.',
    completion_message: 'Thank you for providing this information. It helps protect patient safety and meet regulatory compliance requirements.',
    your_responses: 'Your Responses',
    questions_answered: 'questions answered',
    close_window: 'You may now close this window.',
    loading: 'Loading follow-up information...',
    encrypted: 'Encrypted & audit-logged',
    data_completeness: 'Data Completeness',
    verified: 'Verified',
    select_language: 'Select your preferred language',
    language_subtitle: 'Thank you for helping us ensure patient safety. We have a few questions about the reported case.',
    retry: 'Retry',
    error_title: 'Error Loading Follow-Up',
  });

  const fieldCriticality = {
    event_date: 'CRITICAL',
    event_outcome: 'CRITICAL',
    patient_age: 'HIGH',
    patient_sex: 'MEDIUM',
    drug_route: 'MEDIUM',
    reporter_type: 'HIGH',
    drug_dose: 'MEDIUM',
  };

  const fieldWhyItMatters = {
    event_date: 'Temporal relationship between drug exposure and event onset is essential for causality assessment and regulatory timelines.',
    event_outcome: 'Outcome determines seriousness classification (death, hospitalization, disability) and triggers mandatory expedited reporting.',
    patient_age: 'Age is critical for pediatric/geriatric risk assessment and dose-response analysis.',
    patient_sex: 'Sex-specific adverse event patterns help identify at-risk populations.',
    drug_route: 'Route of administration affects drug bioavailability and adverse event profile.',
    reporter_type: 'Reporter qualification (HCP vs consumer) affects case validity and reporting requirements.',
    drug_dose: 'Dose information helps establish dose-response relationships and identify overdose cases.',
  };

  // Step 1: Initialize session
  useEffect(() => {
    if (!token) {
      setError('Invalid link. No token provided.');
      setState('error');
      return;
    }

    fetch(`${API_BASE}/api/followup-agent/${token}/start`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'completed') {
          setCompletionMessage(data.message?.en || data.message || 'Already completed');
          setState('complete');
        } else if (data.status === 'ready') {
          setCaseContext(data.case_context);
          setLanguageOptions(data.language_options || []);
          setState('language_select');
        } else {
          setError(data.detail || 'Failed to start session');
          setState('error');
        }
      })
      .catch(() => {
        setError('Network error. Please check your connection and try again.');
        setState('error');
      });
  }, [token]);

  // Step 2: Language selection
  const selectLanguage = async (lang) => {
    setLanguage(lang);
    setState('loading');
    try {
      const res = await fetch(`${API_BASE}/api/followup-agent/${token}/set-language`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: lang })
      });
      const data = await res.json();
      if (data.status === 'active') {
        setCurrentQuestion(data.question);
        setProgress(data.progress);
        if (data.ui_strings) setUiStrings(data.ui_strings);
        setState('active');
      } else if (data.status === 'complete') {
        setCompletionMessage(typeof data.message === 'object' ? data.message[lang] || data.message.en : data.message);
        setState('complete');
      } else {
        setError(data.detail || 'Failed to load questions');
        setState('error');
      }
    } catch {
      setError('Network error');
      setState('error');
    }
  };

  // Validation
  const validateAnswer = (value, type) => {
    if (type === 'number') {
      if (!/^\d+$/.test(value)) return 'Please enter numbers only';
      const num = parseInt(value, 10);
      if (num < 0 || num > 150) return 'Please enter a valid age (0-150)';
    }
    if (type === 'date' && !value) return 'Please select a date';
    return '';
  };

  const handleNumberInput = (e) => {
    const val = e.target.value.replace(/[^0-9]/g, '');
    setAnswer(val);
    if (validationError) setValidationError('');
  };

  // Step 3: Submit answer
  const submitAnswer = async () => {
    if (!answer.trim()) return;
    const err = validateAnswer(answer, currentQuestion?.type);
    if (err) { setValidationError(err); return; }
    setValidationError('');

    setConversationHistory(prev => [...prev, {
      question: currentQuestion.text,
      answer: answer
    }]);
    setSubmitting(true);

    try {
      const res = await fetch(`${API_BASE}/api/followup-agent/${token}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_index: currentQuestion.index,
          field_name: currentQuestion.field_name,
          answer: answer,
          language: language
        })
      });
      const data = await res.json();
      if (data.status === 'complete') {
        setCompletionMessage(typeof data.message === 'object' ? data.message[language] || data.message.en : data.message);
        setState('complete');
      } else if (data.status === 'active') {
        setCurrentQuestion(data.question);
        setProgress(data.progress);
        setAnswer('');
      } else {
        setError(data.detail || 'Failed to process answer');
        setState('error');
      }
    } catch {
      setError('Network error');
      setState('error');
    } finally {
      setSubmitting(false);
    }
  };

  const progressPercent = progress ? progress.percentage : 0;

  // ═══════════════════════════════════════════════
  // RENDER: Loading
  // ═══════════════════════════════════════════════
  if (state === 'loading') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading follow-up information...</p>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════
  // RENDER: Error
  // ═══════════════════════════════════════════════
  if (state === 'error') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6">
          <div className="text-red-600 text-center">
            <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <h3 className="mt-4 text-lg font-semibold">Error Loading Follow-Up</h3>
            <p className="mt-2 text-sm text-gray-600">{error}</p>
            <button onClick={() => window.location.reload()} className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════
  // RENDER: Language Selection (Multilingual Dropdown)
  // ═══════════════════════════════════════════════
  if (state === 'language_select') {
    const filteredLangs = languageOptions.filter(l =>
      l.name.toLowerCase().includes(langSearch.toLowerCase()) ||
      l.native.toLowerCase().includes(langSearch.toLowerCase()) ||
      l.code.toLowerCase().includes(langSearch.toLowerCase())
    );

    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-2xl mx-auto px-4">
          {/* Trust Header */}
          <div className="bg-white rounded-xl shadow-md border border-blue-100 p-5 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-bold text-gray-900">SmartFU Safety Follow-Up</h1>
                {caseContext && (
                  <p className="text-sm text-gray-500 mt-1">
                    Regarding: <span className="font-medium text-gray-700">{caseContext.drug}</span> • {caseContext.event}
                  </p>
                )}
              </div>
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                <svg className="mr-1 h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                Verified
              </span>
            </div>
          </div>

          {/* Language Selection Card */}
          <div className="bg-white rounded-xl shadow-lg border-2 border-blue-100 p-6">
            <div className="text-center mb-5">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-blue-100 mb-3">
                <span className="text-2xl">🌐</span>
              </div>
              <h2 className="text-lg font-semibold text-gray-900">Select your preferred language</h2>
              <p className="text-sm text-gray-500 mt-1">
                Thank you for helping us ensure patient safety. We have a few questions about the reported case.
              </p>
            </div>

            {/* Search box */}
            <div className="relative mb-4">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                value={langSearch}
                onChange={(e) => setLangSearch(e.target.value)}
                placeholder="Search language..."
                className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm"
              />
            </div>

            {/* Language grid */}
            <div className="max-h-80 overflow-y-auto rounded-lg border border-gray-200">
              <div className="grid grid-cols-2 gap-0">
                {filteredLangs.map((lang) => (
                  <button
                    key={lang.code}
                    onClick={() => selectLanguage(lang.code)}
                    className="text-left py-3 px-4 text-sm border-b border-r border-gray-100 bg-white hover:bg-blue-50 hover:border-blue-200 transition-all flex items-center gap-2.5 group"
                  >
                    <span className="text-lg flex-shrink-0">{lang.flag}</span>
                    <div className="min-w-0">
                      <div className="font-medium text-gray-800 group-hover:text-blue-700 truncate">{lang.native}</div>
                      <div className="text-xs text-gray-400 truncate">{lang.name}</div>
                    </div>
                  </button>
                ))}
              </div>
              {filteredLangs.length === 0 && (
                <div className="text-center py-6 text-sm text-gray-400">No languages match your search</div>
              )}
            </div>
          </div>

          {/* Trust Footer */}
          <div className="flex items-center justify-center gap-2 text-xs text-gray-400 mt-4">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <span>Encrypted & audit-logged</span>
          </div>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════
  // RENDER: Completion
  // ═══════════════════════════════════════════════
  if (state === 'complete') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="max-w-lg w-full bg-white rounded-2xl shadow-lg p-8">
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-green-100">
              <svg className="h-10 w-10 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h3 className="mt-4 text-2xl font-bold text-gray-900">
              {uiStrings.completion_title}
            </h3>
            <p className="mt-3 text-gray-600">
              {completionMessage || uiStrings.completion_message}
            </p>
            <div className="mt-4 text-sm text-gray-500">
              {conversationHistory.length} question{conversationHistory.length !== 1 ? 's' : ''} answered
            </div>
          </div>

          {/* Summary of answered questions */}
          {conversationHistory.length > 0 && (
            <div className="mt-6 bg-gray-50 rounded-lg p-4 border border-gray-200">
              <h4 className="text-sm font-semibold text-gray-700 mb-3">
                {uiStrings.your_responses}
              </h4>
              <div className="space-y-3">
                {conversationHistory.map((item, i) => (
                  <div key={i} className="pb-3 border-b border-gray-200 last:border-0 last:pb-0">
                    <p className="text-xs text-gray-500">{item.question}</p>
                    <p className="text-sm font-medium text-gray-900 mt-0.5">{item.answer}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="mt-6 text-center">
            <p className="text-xs text-gray-400">🏥 SmartFU - Patient Safety Follow-Up System</p>
            <p className="text-xs text-gray-400 mt-1">You may now close this window.</p>
          </div>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════
  // RENDER: Active Question Flow
  // ═══════════════════════════════════════════════
  const criticality = fieldCriticality[currentQuestion?.field_name] || null;
  const whyItMatters = fieldWhyItMatters[currentQuestion?.field_name] || null;

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-2xl mx-auto px-4">

        {/* Trust Header */}
        <div className="bg-white rounded-xl shadow-md border border-blue-100 p-5 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900">SmartFU Safety Follow-Up</h1>
              {caseContext && (
                <p className="text-sm text-gray-500 mt-1">
                  Case: <span className="font-mono">{caseContext.case_id}</span>
                </p>
              )}
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
            <span className="text-sm font-medium text-gray-700">{uiStrings.data_completeness}</span>
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
          {conversationHistory.length > 0 && (
            <p className="text-xs text-gray-400 mt-2">
              {conversationHistory.length} question{conversationHistory.length !== 1 ? 's' : ''} answered
            </p>
          )}
        </div>

        {/* Previous Answers (last 2) */}
        {conversationHistory.length > 0 && (
          <div className="mb-4 space-y-2">
            {conversationHistory.slice(-2).map((item, i) => (
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
                {currentQuestion.text}
              </h2>
              {criticality && (
                <span className={`ml-3 flex-shrink-0 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                  criticality === 'CRITICAL' ? 'bg-red-100 text-red-800' :
                  criticality === 'HIGH' ? 'bg-orange-100 text-orange-800' :
                  criticality === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {criticality}
                </span>
              )}
            </div>

            {/* Why it matters */}
            {whyItMatters && (
              <p className="text-xs text-gray-500 mb-4 mt-1">{whyItMatters}</p>
            )}

            {/* Answer Input - by type */}
            <div className="mt-4">
              {/* SELECT: Card-style options */}
              {currentQuestion.type === 'select' && currentQuestion.options && currentQuestion.options.length > 0 && (
                <div className="space-y-2">
                  {currentQuestion.options.map((option, i) => {
                    const optValue = typeof option === 'string' ? option : option.value;
                    const optLabel = typeof option === 'string' ? option : option.label;
                    return (
                      <button
                        key={i}
                        onClick={() => { setAnswer(optValue); setValidationError(''); }}
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

              {/* NUMBER */}
              {currentQuestion.type === 'number' && (
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  value={answer}
                  onChange={handleNumberInput}
                  placeholder={uiStrings.enter_number}
                  className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm ${
                    validationError ? 'border-red-400' : 'border-gray-300'
                  }`}
                />
              )}

              {/* DATE */}
              {currentQuestion.type === 'date' && (
                <input
                  type="date"
                  value={answer}
                  onChange={(e) => { setAnswer(e.target.value); setValidationError(''); }}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm"
                />
              )}

              {/* TEXT / fallback */}
              {(currentQuestion.type === 'text' || (!['select', 'number', 'date'].includes(currentQuestion.type))) && (
                <textarea
                  value={answer}
                  onChange={(e) => { setAnswer(e.target.value); setValidationError(''); }}
                  placeholder={uiStrings.type_answer}
                  rows={3}
                  className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm resize-none ${
                    validationError ? 'border-red-400' : 'border-gray-300'
                  }`}
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

            {/* Submit Button */}
            <button
              onClick={submitAnswer}
              disabled={submitting || !!validationError || !answer.toString().trim()}
              className="mt-3 w-full py-3 px-4 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors text-sm"
            >
              {submitting ? (
                <span className="flex items-center justify-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  {uiStrings.submitting}
                </span>
              ) : (
                uiStrings.submit_button
              )}
            </button>
          </div>
        )}

        {/* Privacy Footer */}
        <div className="space-y-2">
          <div className="flex items-center justify-center gap-2 text-xs text-gray-400">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <span>Encrypted & audit-logged</span>
          </div>
          <p className="text-[9px] text-gray-300 text-center leading-snug max-w-sm mx-auto">
            This is a secure, time-bound follow-up link. Your responses are encrypted and audit-logged for patient safety compliance.
          </p>
        </div>
      </div>
    </div>
  );
}