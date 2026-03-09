/**
 * Global Case Event Context
 * 
 * Provides a global event bus for case-related updates.
 * When ANY case is analyzed, updated, or completed, ALL dependent
 * features (Dashboard, Signals, CaseAnalysis) are notified to re-fetch data.
 * 
 * This is the single source of truth for case-driven updates.
 */

import React, { createContext, useContext, useCallback, useRef } from 'react';

const CaseEventContext = createContext(null);

export const CaseEventProvider = ({ children }) => {
  const listeners = useRef(new Set());

  /**
   * Register a listener for case update events
   * Returns an unsubscribe function
   */
  const subscribe = useCallback((callback) => {
    listeners.current.add(callback);
    return () => listeners.current.delete(callback);
  }, []);

  /**
   * Emit a case update event
   * @param {Object} event - Event details
   * @param {string} event.type - Event type: 'CASE_ANALYZED' | 'CASE_UPDATED' | 'CASE_COMPLETED' | 'FOLLOWUP_SUBMITTED' | 'FOLLOWUP_COMPLETED'
   * @param {string} event.caseId - The case ID that was updated
   * @param {Object} event.metadata - Additional event metadata
   */
  const emitCaseUpdate = useCallback((event) => {
    console.log('🔔 Case Event:', event.type, 'for case:', event.caseId);
    
    // Notify all subscribers
    listeners.current.forEach((callback) => {
      try {
        callback(event);
      } catch (error) {
        console.error('Error in case event listener:', error);
      }
    });
  }, []);

  const value = {
    subscribe,
    emitCaseUpdate
  };

  return (
    <CaseEventContext.Provider value={value}>
      {children}
    </CaseEventContext.Provider>
  );
};

/**
 * Hook to access case event system
 */
export const useCaseEvents = () => {
  const context = useContext(CaseEventContext);
  if (!context) {
    throw new Error('useCaseEvents must be used within CaseEventProvider');
  }
  return context;
};

/**
 * Hook to automatically re-fetch data when case events occur
 * @param {Function} refreshCallback - Function to call when a case event occurs
 * @param {Array} deps - Dependencies array (like useEffect)
 */
export const useCaseEventListener = (refreshCallback, deps = []) => {
  const { subscribe } = useCaseEvents();
  const callbackRef = useRef(refreshCallback);

  // Keep callback ref updated
  React.useEffect(() => {
    callbackRef.current = refreshCallback;
  }, [refreshCallback, ...deps]);

  React.useEffect(() => {
    const unsubscribe = subscribe((event) => {
      if (callbackRef.current) {
        callbackRef.current(event);
      }
    });

    return unsubscribe;
  }, [subscribe]);
};
