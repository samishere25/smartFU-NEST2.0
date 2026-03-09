import React from 'react';

const ErrorState = ({ message, onRetry }) => {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50 p-4">
      <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full">
        <div className="text-red-500 text-5xl mb-4 text-center">⚠️</div>
        <h2 className="text-xl font-bold text-gray-900 mb-2 text-center">
          Error
        </h2>
        <p className="text-gray-600 text-center mb-6">{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        )}
      </div>
    </div>
  );
};

export default ErrorState;
