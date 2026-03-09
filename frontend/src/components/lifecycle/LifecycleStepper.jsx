import React from 'react';

/**
 * Lifecycle Stepper Component
 * Horizontal progress indicator showing lifecycle stages
 * 
 * Stages:
 * [Case Created] → [Follow-up Sent] → [Reminder] → [Escalated] → [Closed]
 * 
 * Uses backend-provided flags only - no business logic computed in frontend
 */
const LifecycleStepper = ({ lifecycle }) => {
  if (!lifecycle) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Lifecycle Progress</h3>
        <p className="text-gray-500">No lifecycle data available</p>
      </div>
    );
  }

  // Extract state from backend data
  const attemptCount = lifecycle.attempt_count ?? 0;
  const escalationStatus = lifecycle.escalation_status || 'none';
  const deadCaseFlag = lifecycle.dead_case_flag ?? false;
  const responseStatus = lifecycle.response_status || 'pending';
  const lifecycleStatus = lifecycle.lifecycle_status || 'active';

  // Determine active stages based on backend state
  const stages = [
    {
      id: 'created',
      label: 'Case Created',
      // Always completed if lifecycle exists
      completed: true,
      active: attemptCount === 0 && lifecycleStatus === 'active'
    },
    {
      id: 'followup_sent',
      label: 'Follow-up Sent',
      // Completed if at least one attempt sent
      completed: attemptCount >= 1,
      active: attemptCount >= 1 && escalationStatus === 'none' && !deadCaseFlag && responseStatus !== 'complete'
    },
    {
      id: 'reminder',
      label: 'Reminder',
      // Completed if more than one attempt (reminders sent)
      completed: attemptCount > 1,
      active: attemptCount > 1 && escalationStatus === 'none' && !deadCaseFlag && responseStatus !== 'complete'
    },
    {
      id: 'escalated',
      label: 'Escalated',
      // Completed if escalation status is not none
      completed: escalationStatus !== 'none',
      active: escalationStatus !== 'none' && !deadCaseFlag && responseStatus !== 'complete' && lifecycleStatus !== 'closed'
    },
    {
      id: 'closed',
      label: 'Closed',
      // Completed if dead case or response complete or status is closed/completed
      completed: deadCaseFlag || responseStatus === 'complete' || lifecycleStatus === 'closed' || lifecycleStatus === 'completed' || lifecycleStatus === 'dead_case',
      active: deadCaseFlag || responseStatus === 'complete' || lifecycleStatus === 'closed' || lifecycleStatus === 'completed' || lifecycleStatus === 'dead_case'
    }
  ];

  // Find current active stage index
  const activeIndex = stages.findIndex(s => s.active);

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-6">Lifecycle Progress</h3>
      
      {/* Stepper Container */}
      <div className="relative">
        {/* Progress Line */}
        <div className="absolute top-5 left-0 right-0 h-0.5 bg-gray-200" />
        <div 
          className="absolute top-5 left-0 h-0.5 bg-blue-600 transition-all duration-300"
          style={{ 
            width: `${Math.max(0, (activeIndex / (stages.length - 1)) * 100)}%` 
          }}
        />

        {/* Steps */}
        <div className="relative flex justify-between">
          {stages.map((stage, index) => {
            const isCompleted = stage.completed;
            const isActive = stage.active;
            const isCurrent = index === activeIndex;

            return (
              <div key={stage.id} className="flex flex-col items-center w-1/5">
                {/* Step Circle */}
                <div
                  className={`
                    w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium
                    border-2 transition-all duration-200
                    ${isCompleted
                      ? 'bg-blue-600 border-blue-600 text-white'
                      : isCurrent
                        ? 'bg-white border-blue-600 text-blue-600'
                        : 'bg-white border-gray-300 text-gray-400'
                    }
                    ${stage.id === 'closed' && deadCaseFlag
                      ? 'bg-red-600 border-red-600 text-white'
                      : ''
                    }
                    ${stage.id === 'closed' && responseStatus === 'complete'
                      ? 'bg-green-600 border-green-600 text-white'
                      : ''
                    }
                  `}
                >
                  {isCompleted ? (
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    index + 1
                  )}
                </div>

                {/* Step Label */}
                <span
                  className={`
                    mt-2 text-xs font-medium text-center
                    ${isActive ? 'text-blue-600' : isCompleted ? 'text-gray-700' : 'text-gray-400'}
                  `}
                >
                  {stage.label}
                </span>

                {/* Status Indicator */}
                {isActive && !isCompleted && (
                  <span className="mt-1 text-xs text-blue-500">Current</span>
                )}
                {stage.id === 'closed' && deadCaseFlag && (
                  <span className="mt-1 text-xs text-red-500">Dead Case</span>
                )}
                {stage.id === 'closed' && responseStatus === 'complete' && !deadCaseFlag && (
                  <span className="mt-1 text-xs text-green-500">Complete</span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="mt-8 pt-4 border-t border-gray-100 flex items-center justify-center gap-6 text-xs text-gray-500">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-blue-600" />
          <span>Completed</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full border-2 border-blue-600 bg-white" />
          <span>Current</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full border-2 border-gray-300 bg-white" />
          <span>Pending</span>
        </div>
      </div>
    </div>
  );
};

export default LifecycleStepper;
