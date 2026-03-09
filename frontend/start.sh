#!/bin/bash

# SmartFU Frontend - Quick Start Script

echo "🚀 Starting SmartFU Frontend (Feature 1)"
echo "========================================"
echo ""

# Check if in frontend directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Run this script from the frontend directory"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo ""
fi

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "⚙️  Creating .env.local..."
    echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
    echo "✅ Environment file created"
    echo ""
fi

echo "✅ Setup complete!"
echo ""
echo "📝 Make sure the backend is running on http://localhost:8000"
echo ""
echo "🌐 Starting development server..."
echo "   Frontend will be available at: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

npm run dev
