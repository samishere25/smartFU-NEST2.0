# SmartFU NEST 2.0

AI-powered Follow-Up management system for legal case management with intelligent risk assessment, adaptive questioning, and multi-channel communication.

## Features

- 🎯 AI-Powered Case Risk Assessment
- 🤖 Multi-Agent Pipeline for Intelligent Follow-ups
- 💬 Adaptive Question Generation
- 📱 Multi-Channel Communication (Email, SMS, WhatsApp)
- 📊 Case Lifecycle Management
- 🔍 Signal Detection & Early Warning System
- 📋 Compliance & Audit Trail
- 🧠 Explainable AI Governance

## Tech Stack

**Backend:** Python, FastAPI, PostgreSQL, pgvector, LangChain  
**Frontend:** React, Vite, TailwindCSS  
**AI/ML:** OpenAI, Sentence Transformers, Scikit-learn

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL with pgvector extension

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/samishere25/smartFU-NEST2.0.git
cd smartFU-NEST2.0
```

2. **Set up environment variables**
```bash
# Backend - Create .env file in backend/
cp backend/.env.example backend/.env
# Add your OpenAI API key and other configurations
```

3. **Run with Docker**
```bash
docker-compose up -d
```

Or run manually:

4. **Start Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. **Start Frontend**
```bash
cd frontend
npm install
npm run dev
```

6. **Initialize Database**
```bash
cd backend/scripts
python load_data.py
```

## Access

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## Project Structure

```
├── backend/          # FastAPI backend
│   ├── app/         # Main application
│   ├── scripts/     # Utility scripts
│   └── tests/       # Test suite
├── frontend/        # React frontend
├── docs/            # Documentation
└── docker-compose.yml
```

## Documentation

See the `docs/` folder for detailed documentation:
- [Project Overview](docs/PROJECT_OVERVIEW.md)
- [Technical Architecture](docs/TECHNICAL_ARCHITECTURE.md)
- [Business Pitch](docs/BUSINESS_PITCH.md)

## License

All rights reserved.
