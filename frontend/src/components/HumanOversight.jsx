import React from 'react';

const HumanOversight = () => {
  return (
    <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Human Oversight
      </h3>
      
      <div className="mb-4">
        <p className="text-sm text-gray-600 mb-3">
          ✓ Human-in-the-loop enabled
        </p>
      </div>
      
      <div className="space-y-3">
        <button className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          Add Human Review Note
        </button>
        
        <button className="w-full px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors">
          Override AI Decision
        </button>
      </div>
    </div>
  );
};

export default HumanOversight;
