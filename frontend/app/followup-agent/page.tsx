// Follow-Up Agent Page (Conversational Experience)
// Completely isolated from admin UI
// No authentication, no sidebar, public access

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'react-router-dom';

type SessionState = 'loading' | 'language_select' | 'active' | 'complete' | 'error';

interface Question {
  index: number;
  total: number;
  field_name: string;
  text: string;
  type: 'text' | 'date' | 'select';
  options?: Array<{ value: string; label: string }>;
}

interface Progress {
  current: number;
  total: number;
  percentage: number;
}

function FollowUpAgentContent() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  
  const [state, setState] = useState<SessionState>('loading');
  const [language, setLanguage] = useState<string>('');
  const [caseContext, setCaseContext] = useState<any>(null);
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [answer, setAnswer] = useState<string>('');
  const [completionMessage, setCompletionMessage] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [conversationHistory, setConversationHistory] = useState<Array<{
    question: string;
    answer: string;
  }>>([]);

  // Step 1: Initialize session
  useEffect(() => {
    if (!token) {
      setError('Invalid link. No token provided.');
      setState('error');
      return;
    }

    fetch(`http://localhost:8000/api/followup-agent/${token}/start`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'completed') {
          setCompletionMessage(data.message);
          setState('complete');
        } else if (data.status === 'ready') {
          setCaseContext(data.case_context);
          setState('language_select');
        } else {
          setError('Failed to start session');
          setState('error');
        }
      })
      .catch(err => {
        setError('Network error. Please try again.');
        setState('error');
      });
  }, [token]);

  // Step 2: Language selection
  const selectLanguage = async (lang: string) => {
    setLanguage(lang);
    setState('loading');

    try {
      const res = await fetch(`http://localhost:8000/api/followup-agent/${token}/set-language`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: lang })
      });
      
      const data = await res.json();
      
      if (data.status === 'active') {
        setCurrentQuestion(data.question);
        setProgress(data.progress);
        setState('active');
      } else if (data.status === 'complete') {
        setCompletionMessage(data.message);
        setState('complete');
      } else {
        setError('Failed to load questions');
        setState('error');
      }
    } catch (err) {
      setError('Network error');
      setState('error');
    }
  };

  // Step 3: Submit answer
  const submitAnswer = async () => {
    if (!answer.trim()) {
      alert(language === 'hi' ? 'कृपया एक उत्तर दें' : 'Please provide an answer');
      return;
    }

    setState('loading');

    // Add to conversation history
    setConversationHistory(prev => [
      ...prev,
      {
        question: currentQuestion?.text || '',
        answer: answer
      }
    ]);

    try {
      const res = await fetch(`http://localhost:8000/api/followup-agent/${token}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_index: currentQuestion?.index,
          field_name: currentQuestion?.field_name,
          answer: answer,
          language: language
        })
      });
      
      const data = await res.json();
      
      if (data.status === 'active') {
        // Next question
        setCurrentQuestion(data.question);
        setProgress(data.progress);
        setAnswer('');
        setState('active');
      } else if (data.status === 'complete') {
        setCompletionMessage(data.message);
        setState('complete');
      } else {
        setError('Failed to process answer');
        setState('error');
      }
    } catch (err) {
      setError('Network error');
      setState('error');
    }
  };

  // Render: Loading
  if (state === 'loading') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Render: Error
  if (state === 'error') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-pink-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-gray-800 mb-4">Oops!</h1>
          <p className="text-gray-600 mb-6">{error}</p>
          <p className="text-sm text-gray-500">Please contact support if this issue persists.</p>
        </div>
      </div>
    );
  }

  // Render: Language Selection
  if (state === 'language_select') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-3xl shadow-2xl p-8 md:p-12 max-w-2xl w-full">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="text-5xl mb-4">🏥</div>
            <h1 className="text-3xl font-bold text-gray-800 mb-2">SmartFU</h1>
            <p className="text-gray-600">Patient Safety Follow-Up System</p>
          </div>

          {/* Case Context */}
          {caseContext && (
            <div className="bg-blue-50 rounded-xl p-6 mb-8">
              <p className="text-sm text-gray-600 mb-2">Follow-up regarding:</p>
              <p className="text-lg font-semibold text-gray-800">
                {caseContext.drug} • {caseContext.event}
              </p>
            </div>
          )}

          {/* Language Selection */}
          <div className="mb-8">
            <h2 className="text-xl font-semibold text-gray-800 mb-4 text-center">
              Please select your preferred language
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <button
                onClick={() => selectLanguage('en')}
                className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-xl p-6 hover:from-blue-600 hover:to-indigo-700 transition-all transform hover:scale-105 shadow-lg"
              >
                <div className="text-4xl mb-2">🇬🇧</div>
                <div className="text-xl font-bold">English</div>
              </button>
              <button
                onClick={() => selectLanguage('hi')}
                className="bg-gradient-to-r from-orange-500 to-pink-600 text-white rounded-xl p-6 hover:from-orange-600 hover:to-pink-700 transition-all transform hover:scale-105 shadow-lg"
              >
                <div className="text-4xl mb-2">🇮🇳</div>
                <div className="text-xl font-bold">हिंदी (Hindi)</div>
              </button>
            </div>
          </div>

          {/* Trust Message */}
          <div className="text-center text-sm text-gray-500">
            <p>🔒 Your information helps ensure patient safety</p>
            <p className="mt-1">All responses are confidential and secure</p>
          </div>
        </div>
      </div>
    );
  }

  // Render: Completion
  if (state === 'complete') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-3xl shadow-2xl p-8 md:p-12 max-w-2xl w-full text-center">
          <div className="text-7xl mb-6">✅</div>
          <h1 className="text-3xl font-bold text-gray-800 mb-4">
            {language === 'hi' ? 'धन्यवाद!' : 'Thank You!'}
          </h1>
          <p className="text-lg text-gray-600 mb-8">{completionMessage}</p>
          
          {/* Conversation Summary */}
          {conversationHistory.length > 0 && (
            <div className="bg-gray-50 rounded-xl p-6 mb-6 text-left max-h-96 overflow-y-auto">
              <h3 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
                {language === 'hi' ? 'आपके उत्तर' : 'Your Responses'}
              </h3>
              {conversationHistory.map((item, idx) => (
                <div key={idx} className="mb-4 pb-4 border-b border-gray-200 last:border-0">
                  <p className="text-sm text-gray-500 mb-1">Q: {item.question}</p>
                  <p className="text-base font-medium text-gray-800">A: {item.answer}</p>
                </div>
              ))}
            </div>
          )}

          <div className="text-sm text-gray-500">
            <p>🏥 SmartFU - Patient Safety Follow-Up System</p>
            <p className="mt-1">You may now close this window</p>
          </div>
        </div>
      </div>
    );
  }

  // Render: Active Conversation
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl shadow-2xl p-8 md:p-12 max-w-3xl w-full">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">SmartFU</h1>
            <p className="text-sm text-gray-500">Patient Safety Follow-Up</p>
          </div>
          <div className="text-right">
            <div className="text-sm font-semibold text-indigo-600">
              Question {progress?.current} of {progress?.total}
            </div>
            <div className="text-xs text-gray-500">{progress?.percentage}% complete</div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-indigo-600 transition-all duration-500"
              style={{ width: `${progress?.percentage || 0}%` }}
            ></div>
          </div>
        </div>

        {/* Conversation History */}
        {conversationHistory.length > 0 && (
          <div className="mb-6 max-h-48 overflow-y-auto bg-gray-50 rounded-xl p-4">
            {conversationHistory.slice(-3).map((item, idx) => (
              <div key={idx} className="mb-3 pb-3 border-b border-gray-200 last:border-0">
                <p className="text-xs text-gray-500 mb-1">Q: {item.question}</p>
                <p className="text-sm font-medium text-gray-700">A: {item.answer}</p>
              </div>
            ))}
          </div>
        )}

        {/* Current Question */}
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-2xl p-6 mb-6">
          <div className="flex items-start">
            <div className="text-3xl mr-4">🤖</div>
            <div className="flex-1">
              <p className="text-lg font-semibold text-gray-800 mb-4">
                {currentQuestion?.text}
              </p>
              
              {/* Answer Input */}
              {currentQuestion?.type === 'select' && currentQuestion.options ? (
                <select
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  className="w-full p-4 border-2 border-gray-300 rounded-xl focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none text-gray-800"
                >
                  <option value="">-- {language === 'hi' ? 'चुनें' : 'Select'} --</option>
                  {currentQuestion.options.map((opt, idx) => (
                    <option key={idx} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              ) : currentQuestion?.type === 'date' ? (
                <input
                  type="date"
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  className="w-full p-4 border-2 border-gray-300 rounded-xl focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none text-gray-800"
                />
              ) : (
                <textarea
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder={language === 'hi' ? 'अपना उत्तर यहाँ लिखें...' : 'Type your answer here...'}
                  rows={3}
                  className="w-full p-4 border-2 border-gray-300 rounded-xl focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none resize-none text-gray-800"
                />
              )}
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <button
          onClick={submitAnswer}
          disabled={!answer.trim()}
          className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white py-4 px-6 rounded-xl font-semibold hover:from-blue-600 hover:to-indigo-700 transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none shadow-lg"
        >
          {language === 'hi' ? 'जमा करें' : 'Submit Answer'} →
        </button>

        {/* Trust Badge */}
        <div className="mt-6 text-center text-xs text-gray-500">
          <p>🔒 All responses are confidential and help ensure patient safety</p>
        </div>
      </div>
    </div>
  );
}
export default function FollowUpAgentPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    }>
      <FollowUpAgentContent />
    </Suspense>
  );
}