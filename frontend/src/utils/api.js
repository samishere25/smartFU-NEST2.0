// API utility for backend communication
// Use relative path in dev (Vite proxy forwards /api → localhost:8000)
const API_BASE_URL = '';

const getAuthToken = () => {
  return localStorage.getItem('access_token');
};

const handleResponse = async (response) => {
  if (response.status === 401) {
    localStorage.removeItem('access_token');
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const detail = error.detail;
    const message = Array.isArray(detail)
      ? detail.map(d => d.msg || JSON.stringify(d)).join('; ')
      : (typeof detail === 'string' ? detail : JSON.stringify(detail) || 'API request failed');
    throw new Error(message);
  }
  
  return response.json();
};

export const api = {
  // Get dashboard metrics from backend
  getDashboardMetrics: async () => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/analytics/dashboard`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Get cached analysis for a case (no AI re-run)
  getCaseAnalysis: async (caseId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/cases/by-primaryid/${caseId}/analysis`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Analyze case with AI agents (using primaryid) — full pipeline re-run
  analyzeCase: async (caseId, options = {}) => {
    const token = getAuthToken();
    const bodyPayload = {};
    if (options.repo_doc_ids && options.repo_doc_ids.length > 0) {
      bodyPayload.repo_doc_ids = options.repo_doc_ids;
    }
    if (options.reviewer_notes) {
      bodyPayload.reviewer_notes = options.reviewer_notes;
    }
    if (options.language) {
      bodyPayload.language = options.language;
    }
    const response = await fetch(`${API_BASE_URL}/api/cases/by-primaryid/${caseId}/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(bodyPayload),
    });
    return handleResponse(response);
  },

  // Get case details by primaryid (FAERS case ID)
  getCaseByPrimaryId: async (primaryId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/cases/by-primaryid/${primaryId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Get stored analysis for a case (read-only, no re-analysis)
  getCaseAnalysis: async (primaryId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/cases/by-primaryid/${primaryId}/analysis`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Submit reviewer-override questions and trigger follow-up email
  submitOverrideQuestions: async (caseId, questions) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/followups/${caseId}/override-questions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ questions })
    });
    return handleResponse(response);
  },

  // Save reviewer questions (no follow-up trigger)
  saveReviewerQuestions: async (caseId, questions) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/cases/${caseId}/save-reviewer-questions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ questions })
    });
    return handleResponse(response);
  },

  // Analyze & send: merge 4 sources → freeze → send follow-up
  analyzeAndSend: async (caseId, options = {}) => {
    const token = getAuthToken();
    const bodyPayload = {};
    if (options.repo_doc_ids && options.repo_doc_ids.length > 0) {
      bodyPayload.repo_doc_ids = options.repo_doc_ids;
    }
    if (options.language) {
      bodyPayload.language = options.language;
    }
    const response = await fetch(`${API_BASE_URL}/api/cases/${caseId}/analyze-and-send`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(bodyPayload),
    });
    return handleResponse(response);
  },

  // Get case details by UUID
  getCase: async (caseId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/cases/${caseId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Get latest AI decision and confidence for a case
  getCaseDecision: async (caseId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/cases/${caseId}/decision`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Login
  login: async (email, password) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData
    });
    
    const data = await handleResponse(response);
    if (data.access_token) {
      localStorage.setItem('access_token', data.access_token);
    }
    return data;
  },

  // Get follow-up information
  getFollowUp: async (caseId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/followups/${caseId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Get follow-up questions for a case
  getFollowUpQuestions: async (caseId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/followups/${caseId}/questions`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Submit follow-up responses
  submitFollowUp: async (caseId, responses) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/followups/${caseId}/submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ responses })
    });
    return handleResponse(response);
  },

  // Get next follow-up question for interactive micro-question flow
  getNextQuestion: async (caseId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/followups/next-question?case_id=${caseId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Submit a single follow-up answer
  submitFollowUpAnswer: async (caseId, fieldName, answer) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/followups/answer`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        case_id: caseId,
        field_name: fieldName,
        answer: answer
      })
    });
    return handleResponse(response);
  },

  // Decline follow-up
  declineFollowUp: async (caseId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/followups/${caseId}/decline`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Get active signals
  getActiveSignals: async () => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/signals/active`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Escalate signal
  escalateSignal: async (signalId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/signals/${signalId}/escalate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // ===== FEATURE 7: Trust, Privacy & AI Governance =====
  
  // Get AI confidence and trust metrics for a case
  getCaseTrust: async (caseId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/cases/${caseId}/trust`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Get privacy and data minimization info for a case
  getCasePrivacy: async (caseId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/cases/${caseId}/privacy`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Get human oversight status for a case
  getCaseOversight: async (caseId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/cases/${caseId}/oversight`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Submit human oversight action (approve/override)
  submitOversightAction: async (caseId, action, reason) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/cases/${caseId}/oversight/action`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ action, reason })
    });
    return handleResponse(response);
  },

  // Get audit log for a case
  getCaseAuditLog: async (caseId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/governance/${caseId}/audit-log`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Get system-wide trust metrics
  getSystemTrustMetrics: async () => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/system/trust-metrics`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Get reporter trust message from config
  getReporterTrustMessage: async () => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/config/reporter-trust-message`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // ===== FEATURE 4: Lifecycle Tracking =====

  // Initialize lifecycle for a case
  initLifecycle: async (caseId, reporterType, seriousnessLevel, initialCompleteness = 0.0) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/lifecycle/init`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        case_id: caseId,
        reporter_type: reporterType,
        seriousness_level: seriousnessLevel,
        initial_completeness: initialCompleteness
      })
    });
    return handleResponse(response);
  },

  // Get lifecycle status for a case
  getLifecycleStatus: async (caseId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/lifecycle/${caseId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Record follow-up sent
  recordFollowupSent: async (caseId, questionsSent, channel, sentTo = null) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/lifecycle/${caseId}/followup-sent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        questions_sent: questionsSent,
        channel: channel,
        sent_to: sentTo
      })
    });
    return handleResponse(response);
  },

  // Record response received
  recordResponseReceived: async (caseId, questionsAnswered, completenessScore, safetyConfidence, isComplete = false) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/lifecycle/${caseId}/response`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        questions_answered: questionsAnswered,
        completeness_score: completenessScore,
        safety_confidence: safetyConfidence,
        is_complete: isComplete
      })
    });
    return handleResponse(response);
  },

  // Check if reminder is due
  checkReminderDue: async (caseId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/lifecycle/${caseId}/check-reminder`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Check if escalation is needed
  checkEscalationNeeded: async (caseId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/lifecycle/${caseId}/check-escalation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Trigger escalation
  triggerEscalation: async (caseId, reason, escalateTo = 'supervisor') => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/lifecycle/${caseId}/escalate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        reason: reason,
        escalate_to: escalateTo
      })
    });
    return handleResponse(response);
  },

  // Check if case should be marked as dead
  checkDeadCase: async (caseId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/lifecycle/${caseId}/check-dead-case`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Mark case as dead
  markDeadCase: async (caseId, reason, closedBy = 'system') => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/lifecycle/${caseId}/dead-case`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        reason: reason,
        closed_by: closedBy
      })
    });
    return handleResponse(response);
  },

  // Get lifecycle audit log
  getLifecycleAuditLog: async (caseId, limit = 50) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/lifecycle/${caseId}/audit?limit=${limit}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Get lifecycle policies
  getLifecyclePolicies: async () => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/lifecycle/policies/list`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Get lifecycle stats overview
  getLifecycleStats: async () => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/lifecycle/stats/overview`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // ===== CIOMS PDF Upload =====

  // Upload CIOMS PDF for case creation
  uploadCiomsPdf: async (file) => {
    const token = getAuthToken();
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/api/cases/upload-pdf`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    });
    return handleResponse(response);
  },

  // XML bulk upload
  uploadXml: async (file) => {
    const token = getAuthToken();
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_BASE_URL}/api/cases/upload-xml`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    });
    return handleResponse(response);
  },

  // List PDF uploads
  listPdfUploads: async (skip = 0, limit = 50) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/cases/pdf-uploads?skip=${skip}&limit=${limit}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // ===== Reviewer Dashboard =====

  // Get full case review data
  getReviewCase: async (caseId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/review/${caseId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    return handleResponse(response);
  },

  // Submit reviewer decision
  submitReviewerDecision: async (caseId, decision, reviewerComment = null) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/review/${caseId}/decision`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ decision, reviewer_comment: reviewerComment })
    });
    return handleResponse(response);
  },

  // ===== PV Audit Trail =====

  // Get global audit trail with optional filters
  getAuditTrail: async (actionType = null, actorType = null, limit = 200, offset = 0) => {
    const token = getAuthToken();
    const params = new URLSearchParams({ limit, offset });
    if (actionType) params.append('action_type', actionType);
    if (actorType) params.append('actor_type', actorType);
    const response = await fetch(`${API_BASE_URL}/api/audit/trail?${params}`, {
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
    });
    return handleResponse(response);
  },

  // Get audit trail for a specific case
  getCaseAuditTrailPV: async (caseId, actionType = null, limit = 200) => {
    const token = getAuthToken();
    const params = new URLSearchParams({ limit });
    if (actionType) params.append('action_type', actionType);
    const response = await fetch(`${API_BASE_URL}/api/audit/trail/case/${caseId}?${params}`, {
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
    });
    return handleResponse(response);
  },

  // Get audit trail for a signal
  getSignalAuditTrail: async (signalId, limit = 100) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/audit/trail/signal/${signalId}?limit=${limit}`, {
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
    });
    return handleResponse(response);
  },

  // Get audit statistics
  getAuditStats: async () => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/audit/trail/stats`, {
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
    });
    return handleResponse(response);
  },

  // Get supported action types for filter UI
  getAuditActionTypes: async () => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/audit/trail/action-types`, {
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
    });
    return handleResponse(response);
  },

  // ===== Signal Human Oversight =====

  // Submit signal review action (DOWNGRADE/ESCALATE/FALSE_POSITIVE/NOTE)
  reviewSignal: async (signalId, action, note, newPriority = null) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/signals/${signalId}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ action, note, new_priority: newPriority })
    });
    return handleResponse(response);
  },

  // Get cases linked to a signal
  getSignalCases: async (signalId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/signals/${signalId}/cases`, {
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
    });
    return handleResponse(response);
  },

  // Get signal detection thresholds
  getSignalThresholds: async () => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/signals/thresholds`, {
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
    });
    return handleResponse(response);
  },

  // ===== Global Document Repository =====

  listRepoDocuments: async (formType = null) => {
    const token = getAuthToken();
    const params = formType ? `?form_type=${formType}` : '';
    const response = await fetch(`${API_BASE_URL}/api/repo-documents/${params}`, {
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
    });
    return handleResponse(response);
  },

  uploadRepoDocument: async (file, displayName, formType, description = '') => {
    const token = getAuthToken();
    const fd = new FormData();
    fd.append('file', file);
    fd.append('display_name', displayName);
    fd.append('form_type', formType);
    fd.append('description', description);
    const response = await fetch(`${API_BASE_URL}/api/repo-documents/upload`, {
      method: 'POST',
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: fd
    });
    return handleResponse(response);
  },

  getRepoDocumentQuestions: async (docId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/repo-documents/${docId}/questions`, {
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
    });
    return handleResponse(response);
  },

  deleteRepoDocument: async (docId) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/repo-documents/${docId}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
    });
    return handleResponse(response);
  },

  ciomsCombinedSend: async (caseId, body) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/cases/${caseId}/cioms-combined-send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({
        repo_doc_ids: body.repo_doc_ids || [],
        reviewer_notes: body.reviewer_notes || '',
        cioms_missing_fields: body.cioms_missing_fields || [],
      })
    });
    return handleResponse(response);
  },

  attachRepoDocs: async (caseId, repoDocIds) => {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/api/cases/${caseId}/attach-repo-docs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ repo_doc_ids: repoDocIds }),
    });
    return handleResponse(response);
  },
};
