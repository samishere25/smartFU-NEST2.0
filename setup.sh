#!/bin/bash
# SmartFU Complete Setup Script for Mac
# This script will generate ALL project files and set up the complete system

set -e  # Exit on error

echo "🚀 SmartFU Complete Setup Starting..."
echo "======================================"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're on Mac
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "⚠️  Warning: This script is optimized for macOS"
fi

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 is required but not installed. Aborting." >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed. Aborting." >&2; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js is required but not installed. Aborting." >&2; exit 1; }

echo -e "${GREEN}✅ Prerequisites check passed${NC}"

# Create project structure
echo -e "${BLUE}Creating project structure...${NC}"
python3 backend/scripts/generate_project.py

# Setup backend
echo -e "${BLUE}Setting up backend...${NC}"
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
echo -e "${BLUE}Installing Python dependencies...${NC}"
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt

echo -e "${GREEN}✅ Python dependencies installed${NC}"

# Start Docker services
echo -e "${BLUE}Starting Docker services (PostgreSQL & Redis)...${NC}"
cd ..
docker-compose up -d postgres redis

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
sleep 10

# Run database migrations
echo -e "${BLUE}Running database migrations...${NC}"
cd backend
source venv/bin/activate
alembic upgrade head

echo -e "${GREEN}✅ Database migrations completed${NC}"

# Load FAERS dataset
if [ -f "/mnt/user-data/uploads/cioms_faers_combined.csv" ]; then
    echo -e "${BLUE}Loading FAERS dataset...${NC}"
    python scripts/load_data.py
    echo -e "${GREEN}✅ Data loaded${NC}"
else
    echo -e "${YELLOW}⚠️  FAERS CSV file not found. Skipping data loading.${NC}"
    echo -e "${YELLOW}   Place cioms_faers_combined.csv in backend/data/ and run: python scripts/load_data.py${NC}"
fi

# Train ML models
echo -e "${BLUE}Training ML models...${NC}"
python scripts/train_models.py
echo -e "${GREEN}✅ ML models trained${NC}"

# Setup frontend
echo -e "${BLUE}Setting up frontend...${NC}"
cd ../frontend
npm install

echo -e "${GREEN}✅ Frontend dependencies installed${NC}"

# Done
echo ""
echo -e "${GREEN}======================================"
echo "🎉 SmartFU Setup Complete!"
echo -e "======================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Start Backend (Terminal 1):"
echo -e "   ${BLUE}cd backend && source venv/bin/activate && uvicorn app.main:app --reload${NC}"
echo ""
echo "2. Start Frontend (Terminal 2):"
echo -e "   ${BLUE}cd frontend && npm run dev${NC}"
echo ""
echo "3. Open browser:"
echo -e "   ${BLUE}http://localhost:3000${NC} (Frontend)"
echo -e "   ${BLUE}http://localhost:8000/docs${NC} (API Docs)"
echo ""
echo "Default credentials:"
echo -e "   Email: ${BLUE}admin@smartfu.com${NC}"
echo -e "   Password: ${BLUE}admin123${NC}"
echo ""
echo -e "${GREEN}Happy coding! 🚀${NC}"
