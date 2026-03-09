/**
 * Follow-Up Optimization - Deterministic Logic
 * Uses backend analysis data to recommend timing and communication channel
 * NO hardcoded values - all based on real backend fields
 */

/**
 * Get response probability confidence level
 * @param {number} probability - Response probability (0.0 to 1.0)
 * @returns {string} Confidence level: LOW, MEDIUM, or HIGH
 */
export const getResponseConfidence = (probability) => {
  if (probability < 0.40) return 'LOW';
  if (probability < 0.70) return 'MEDIUM';
  return 'HIGH';
};

/**
 * Get timing recommendation based on backend decision, reporter type, and risk
 * @param {object} analysis - Backend analysis object
 * @returns {object} { timing: string, reasoning: string }
 */
export const getTimingRecommendation = (analysis) => {
  const decision = analysis?.decision;
  const reporterType = analysis?.case_data?.reporter_type || 'UNKNOWN';
  const riskScore = analysis?.risk_score || 0;

  // Priority 1: Decision-based timing
  if (decision === 'ESCALATE') {
    return {
      timing: 'Immediate (within 4 hours)',
      reasoning: 'High-risk case requiring urgent escalation',
      urgency: 'CRITICAL'
    };
  }

  if (decision === 'SKIP') {
    return {
      timing: 'No follow-up needed',
      reasoning: 'Case complete or low response probability',
      urgency: 'NONE'
    };
  }

  if (decision === 'DEFER') {
    return {
      timing: 'Wait 48-72 hours',
      reasoning: 'Case needs review before initiating follow-up',
      urgency: 'LOW'
    };
  }

  // Priority 2: Reporter type-based timing (for PROCEED decision)
  const isHealthcareProfessional = ['MD', 'HP', 'PH', 'RN'].includes(reporterType);
  
  if (isHealthcareProfessional) {
    return {
      timing: 'Next working day (9 AM - 5 PM)',
      reasoning: 'Healthcare professionals prefer business hours contact',
      urgency: 'MEDIUM'
    };
  }

  // Patient/Consumer reporters
  if (['CN', 'PT', 'OTHER'].includes(reporterType)) {
    return {
      timing: 'Evening or Weekend (6 PM - 9 PM)',
      reasoning: 'Patients typically more available outside work hours',
      urgency: 'MEDIUM'
    };
  }

  // Default for unknown reporter type
  return {
    timing: 'Within 24-48 hours',
    reasoning: 'Standard follow-up window for unknown reporter type',
    urgency: 'MEDIUM'
  };
};

/**
 * Get communication channel recommendation
 * @param {object} analysis - Backend analysis object
 * @returns {object} { channel: string, reasoning: string, alternatives: string[] }
 */
export const getChannelRecommendation = (analysis) => {
  const reporterType = analysis?.case_data?.reporter_type || 'UNKNOWN';
  const riskScore = analysis?.risk_score || 0;

  // Priority 1: High-risk cases require phone contact
  if (riskScore >= 0.8) {
    return {
      channel: 'Phone',
      reasoning: 'High-risk cases require immediate verbal communication',
      alternatives: ['Email (as backup confirmation)'],
      icon: '📞',
      color: 'red'
    };
  }

  // Priority 2: Reporter type-based channel selection
  const isHealthcareProfessional = ['MD', 'HP', 'PH', 'RN'].includes(reporterType);
  
  if (isHealthcareProfessional) {
    return {
      channel: 'Email',
      reasoning: 'Healthcare professionals prefer documented email communication',
      alternatives: ['Phone (if urgent)', 'Secure Portal'],
      icon: '📧',
      color: 'blue'
    };
  }

  // Patient/Consumer reporters - prefer accessible channels
  if (['CN', 'PT', 'OTHER'].includes(reporterType)) {
    return {
      channel: 'SMS or Patient Portal',
      reasoning: 'Patients prefer convenient, mobile-friendly contact methods',
      alternatives: ['Phone (if no response)', 'Email'],
      icon: '💬',
      color: 'green'
    };
  }

  // Lawyer/Legal reporters
  if (reporterType === 'LW') {
    return {
      channel: 'Email (certified)',
      reasoning: 'Legal representatives require documented communication',
      alternatives: ['Certified Mail'],
      icon: '⚖️',
      color: 'purple'
    };
  }

  // Default for unknown reporter type
  return {
    channel: 'Email',
    reasoning: 'Default communication method with audit trail',
    alternatives: ['Phone', 'SMS'],
    icon: '📧',
    color: 'gray'
  };
};

/**
 * Get reporter type display name
 * @param {string} code - Reporter type code
 * @returns {string} Full name
 */
export const getReporterTypeLabel = (code) => {
  const labels = {
    'MD': 'Physician',
    'HP': 'Healthcare Professional',
    'PH': 'Pharmacist',
    'RN': 'Nurse',
    'CN': 'Consumer',
    'PT': 'Patient',
    'LW': 'Lawyer',
    'OTHER': 'Other'
  };
  return labels[code] || code || 'Unknown';
};

/**
 * Get color class for response confidence badge
 * @param {string} confidence - Confidence level
 * @returns {string} Tailwind color classes
 */
export const getConfidenceColor = (confidence) => {
  const colors = {
    'HIGH': 'bg-green-100 text-green-800 border-green-300',
    'MEDIUM': 'bg-yellow-100 text-yellow-800 border-yellow-300',
    'LOW': 'bg-red-100 text-red-800 border-red-300'
  };
  return colors[confidence] || 'bg-gray-100 text-gray-800 border-gray-300';
};

/**
 * Format response probability as percentage
 * @param {number} probability - Probability value (0.0 to 1.0)
 * @returns {string} Formatted percentage
 */
export const formatProbability = (probability) => {
  if (probability === null || probability === undefined) return 'N/A';
  return `${Math.round(probability * 100)}%`;
};
