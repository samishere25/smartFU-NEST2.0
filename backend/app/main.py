"""
SmartFU - Intelligent Pharmacovigilance Follow-Up System







































































































































































































































































































































export default DocumentsTab;};  );    </div>      </div>        )}          <p className="text-xs text-gray-400">Click "Build Combined Follow-Up" to aggregate missing questions, reviewer notes, and checklists.</p>        {!followup && !buildingFollowup && (        )}          </div>            )}              <p className="text-sm text-gray-400 text-center py-4">No follow-up items found for this case.</p>            {followup.missing_questions?.length === 0 && followup.reviewer_questions?.length === 0 && followup.attachments?.length === 0 && (            )}              </div>                </div>                  ))}                    </div>                      <span className="text-sm text-gray-700 truncate">{a.file_name}</span>                      </span>                        {a.document_type}                      <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${TYPE_COLORS[a.document_type] || 'bg-gray-100 text-gray-600'}`}>                    <div key={i} className="flex items-center gap-2 border rounded-lg px-3 py-2">                  {followup.attachments.map((a, i) => (                <div className="space-y-2">                </h4>                  Attachments ({followup.attachments.length})                <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">              <div>            {followup.attachments?.length > 0 && (            {/* Attachments */}            )}              </div>                </div>                  ))}                    </div>                      </p>                        {q.file_name} {q.uploaded_by && `· ${q.uploaded_by}`}                      <p className="text-[10px] text-gray-400 mt-1">                      <p className="text-sm text-gray-800">{q.question || q.note || 'See attached file'}</p>                    <div key={i} className="border rounded-lg px-3 py-2 bg-purple-50/30">                  {followup.reviewer_questions.map((q, i) => (                <div className="space-y-2">                </h4>                  Reviewer Notes ({followup.reviewer_questions.length})                <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">              <div>            {followup.reviewer_questions?.length > 0 && (            {/* Reviewer Questions */}            )}              </div>                </div>                  ))}                    </div>                      </div>                        </div>                          </div>                            )}                              <span className="text-[10px] text-red-500 font-medium">Required</span>                            {q.is_required && (                            <span className="text-[10px] text-gray-400">Field: {q.field_name}</span>                          <div className="flex items-center gap-2 mt-1">                          <p className="text-sm text-gray-800">{q.question}</p>                        <div className="min-w-0">                        </span>                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>                        <span className="text-blue-500 mt-0.5 flex-shrink-0">                      <div className="flex items-start gap-2">                    <div key={i} className="border rounded-lg px-3 py-2">                  {followup.missing_questions.map((q, i) => (                <div className="space-y-2">                </h4>                  AI-Generated Questions ({followup.missing_questions.length})                <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">              <div>            {followup.missing_questions?.length > 0 && (            {/* Missing Questions */}          <div className="space-y-4 mt-2">        {followup && (        </div>          </button>            {buildingFollowup ? 'Building...' : 'Build Combined Follow-Up'}          >            className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"            disabled={buildingFollowup}            onClick={handleBuildFollowup}          <button          <h3 className="text-sm font-semibold text-gray-900">Combined Follow-Up</h3>        <div className="flex items-center justify-between mb-4">      <div className="bg-white rounded-xl border shadow-sm p-5">      {/* ── Build Combined Follow-Up ── */}      </div>        )}          </div>            ))}              </div>                </div>                  ))}                    </div>                      </button>                        </svg>                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">                      >                        title="Deactivate"                        className="text-gray-300 hover:text-red-500 transition-colors flex-shrink-0 ml-2"                        onClick={() => handleDelete(doc.id)}                      <button                      </div>                        </div>                          </p>                            )}                              </span>                                Extracted ({doc.extracted_json.fields_extracted || 0} fields)                              <span className="ml-2 text-emerald-600 font-medium">                            {doc.extracted_json && !doc.extracted_json.error && (                            {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleString() : ''}                            {doc.uploaded_by && `by ${doc.uploaded_by} · `}                          <p className="text-[10px] text-gray-400">                          <p className="text-sm font-medium text-gray-800 truncate">{doc.file_name}</p>                        <div className="min-w-0">                        </svg>                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />                        <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">                      <div className="flex items-center gap-3 min-w-0">                    <div key={doc.id} className="flex items-center justify-between border rounded-lg px-3 py-2 hover:bg-gray-50 transition-colors">                  {docs.map((doc) => (                <div className="space-y-2 pl-1">                </div>                  <span className="text-xs text-gray-400">({docs.length})</span>                  </span>                    {type.replace('_', ' ')}                  <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide ${TYPE_COLORS[type] || 'bg-gray-100 text-gray-600'}`}>                <div className="flex items-center gap-2 mb-2">              <div key={type}>            {Object.entries(grouped).map(([type, docs]) => (          <div className="space-y-4">        {Object.keys(grouped).length > 0 && (        )}          <p className="text-sm text-gray-400 text-center py-6">No documents uploaded yet.</p>        {documents.length === 0 && !loading && (        </div>          </button>            {loading ? 'Loading...' : 'Refresh'}          >            className="text-xs text-blue-600 hover:text-blue-800 font-medium"            disabled={loading}            onClick={fetchDocuments}          <button          </h3>            Documents <span className="text-gray-400 font-normal">({documents.length})</span>          <h3 className="text-sm font-semibold text-gray-900">        <div className="flex items-center justify-between mb-4">      <div className="bg-white rounded-xl border shadow-sm p-5">      {/* ── Document List (grouped by type) ── */}      </div>        )}          <div className="mt-3 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</div>        {error && (        </div>          </button>            {uploading ? 'Uploading...' : 'Upload'}          >            className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"            disabled={uploading || !selectedType || !selectedFile}            onClick={handleUpload}          <button          </div>            />              className="w-full text-sm text-gray-700 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"              onChange={(e) => setSelectedFile(e.target.files[0] || null)}              type="file"            <input            <label className="block text-xs text-gray-500 mb-1">File</label>          <div className="flex-1 min-w-[200px]">          </div>            </select>              ))}                <option key={dt.value} value={dt.value}>{dt.label}</option>              {DOCUMENT_TYPES.map((dt) => (              <option value="">Select type...</option>            >              className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"              onChange={(e) => setSelectedType(e.target.value)}              value={selectedType}            <select            <label className="block text-xs text-gray-500 mb-1">Document Type *</label>          <div className="flex-1 min-w-[180px]">        <div className="flex flex-wrap items-end gap-3">        <h3 className="text-sm font-semibold text-gray-900 mb-4">Upload Document</h3>      <div className="bg-white rounded-xl border shadow-sm p-5">      {/* ── Upload Section ── */}    <div className="space-y-5">  return (  });    grouped[t].push(doc);    if (!grouped[t]) grouped[t] = [];    const t = doc.document_type;  documents.forEach((doc) => {  const grouped = {};  // Group documents by type  };    }      setBuildingFollowup(false);    } finally {      setError(e.message);    } catch (e) {      setFollowup(data);      const data = await res.json();      }        throw new Error(err.detail || `Build failed (${res.status})`);        const err = await res.json().catch(() => ({}));      if (!res.ok) {      });        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },        method: 'POST',      const res = await fetch(`/api/cases/${caseId}/build-combined-followup`, {    try {    setFollowup(null);    setError(null);    setBuildingFollowup(true);  const handleBuildFollowup = async () => {  };    }      setError(e.message);    } catch (e) {      fetchDocuments();      if (!res.ok) throw new Error('Delete failed');      });        headers: { Authorization: `Bearer ${token}` },        method: 'DELETE',      const res = await fetch(`/api/cases/${caseId}/documents/${docId}`, {    try {    if (!window.confirm('Deactivate this document?')) return;  const handleDelete = async (docId) => {  };    }      setUploading(false);    } finally {      setError(e.message);    } catch (e) {      fetchDocuments();      setSelectedFile(null);      setSelectedType('');      }        throw new Error(err.detail || `Upload failed (${res.status})`);        const err = await res.json().catch(() => ({}));      if (!res.ok) {      });        body: form,        headers: { Authorization: `Bearer ${token}` },        method: 'POST',      const res = await fetch(`/api/cases/${caseId}/documents`, {      form.append('document_type', selectedType);      form.append('file', selectedFile);      const form = new FormData();    try {    setError(null);    setUploading(true);    if (!selectedFile) { setError('Please select a file.'); return; }    if (!selectedType) { setError('Please select a document type.'); return; }  const handleUpload = async () => {  useEffect(() => { fetchDocuments(); }, [fetchDocuments]);  }, [caseId, token]);    }      setLoading(false);    } finally {      setError(e.message);    } catch (e) {      setDocuments(data.documents || []);      const data = await res.json();      if (!res.ok) throw new Error(`Failed to load documents (${res.status})`);      });        headers: { Authorization: `Bearer ${token}` },      const res = await fetch(`/api/cases/${caseId}/documents`, {    try {    setError(null);    setLoading(true);    if (!caseId) return;  const fetchDocuments = useCallback(async () => {  const token = localStorage.getItem('access_token');  const [buildingFollowup, setBuildingFollowup] = useState(false);  const [followup, setFollowup] = useState(null);  const [error, setError] = useState(null);  const [selectedFile, setSelectedFile] = useState(null);  const [selectedType, setSelectedType] = useState('');  const [uploading, setUploading] = useState(false);  const [loading, setLoading] = useState(false);  const [documents, setDocuments] = useState([]);const DocumentsTab = ({ caseId }) => {};  RESPONSE: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20',  REVIEWER_NOTE: 'bg-purple-50 text-purple-700 ring-1 ring-purple-600/20',  PREGNANCY: 'bg-pink-50 text-pink-700 ring-1 ring-pink-600/20',  TAFU: 'bg-amber-50 text-amber-700 ring-1 ring-amber-600/20',  CIOMS: 'bg-blue-50 text-blue-700 ring-1 ring-blue-600/20',const TYPE_COLORS = {];  { value: 'RESPONSE', label: 'Response Document' },  { value: 'REVIEWER_NOTE', label: 'Reviewer Note' },  { value: 'PREGNANCY', label: 'Pregnancy Form' },  { value: 'TAFU', label: 'TAFU Checklist' },  { value: 'CIOMS', label: 'CIOMS Form' },const DOCUMENT_TYPES = [Main FastAPI Application
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response
from contextlib import asynccontextmanager
import time
import logging

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    _HAS_SLOWAPI = True
except ImportError:
    _HAS_SLOWAPI = False

from app.core.config import settings
from app.db.session import engine
from app.db.base import Base
from app.api.routes import auth, cases, followups, analytics, admin, reporter_portal, signals, governance
from app.api.routes import lifecycle  # Feature-4: Lifecycle Tracking
from app.api.routes import regulatory  # Regulatory workflow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ── Rate Limiter (slowapi) ──────────────────────────────────────────
if _HAS_SLOWAPI:
    limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
else:
    limiter = None
    logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("🚀 Starting SmartFU API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    
    # Create tables (if not using Alembic)
    # Base.metadata.create_all(bind=engine)
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down SmartFU API...")


# Create FastAPI app
app = FastAPI(
    title="SmartFU API",
    description="Intelligent Pharmacovigilance Follow-Up System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Attach rate limiter state
if _HAS_SLOWAPI and limiter:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
else:
    logging.getLogger(__name__).warning("⚠️  slowapi not installed — rate limiting disabled. Run: pip install slowapi")


# CORS Middleware — restrict methods/headers to what the frontend actually uses
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)


# ── Security Headers Middleware ─────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    # Prevent MIME-type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    # XSS protection (legacy, still useful for older browsers)
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Referrer policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Content Security Policy — allow self + inline for API docs
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self' data:"
    )
    # Permissions policy — restrict sensitive browser features
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )
    return response


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handlers — never leak stack traces in production
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring
    """
    return {
        "status": "healthy",
        "service": "SmartFU",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }


# API Health check endpoint (with /api prefix)
@app.get("/api/health", tags=["Health"])
async def api_health_check():
    """
    API health check endpoint for monitoring
    """
    return {
        "status": "healthy",
        "service": "SmartFU API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information
    """
    return {
        "message": "SmartFU - Intelligent Pharmacovigilance Follow-Up System",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }


# Include routers
app.include_router(
    auth.router,
    prefix="/api/auth",
    tags=["Authentication"]
)

# PDF Upload (must be before cases router — avoids /{case_id} catch-all on /pdf-uploads)
from app.api.routes import pdf_upload
app.include_router(
    pdf_upload.router,
    prefix="/api/cases",
    tags=["PDF Upload"]
)

# Case Documents (multiple documents per case — before cases router for same reason)
from app.api.routes import case_documents
app.include_router(
    case_documents.router,
    prefix="/api/cases",
    tags=["Case Documents"]
)

# CIOMS Combined Send (before cases router to avoid /{case_id} catch-all)
from app.api.routes import cioms_combined
app.include_router(
    cioms_combined.router,
    prefix="/api/cases",
    tags=["CIOMS Combined Send"]
)

# Global Document Repository
from app.api.routes import repo_documents
app.include_router(
    repo_documents.router,
    prefix="/api/repo-documents",
    tags=["Global Document Repository"]
)

app.include_router(
    cases.router,
    prefix="/api/cases",
    tags=["Cases"]
)

app.include_router(
    followups.router,
    prefix="/api/followups",
    tags=["Follow-Ups"]
)

app.include_router(
    reporter_portal.router,
    prefix="/api/reporter-portal",
    tags=["Reporter Portal"]
)

app.include_router(
    signals.router,
    prefix="/api/signals",
    tags=["Safety Signals"]
)

app.include_router(
    analytics.router,
    prefix="/api/analytics",
    tags=["Analytics"]
)

app.include_router(
    admin.router,
    prefix="/api/admin",
    tags=["Admin"]
)

app.include_router(
    governance.router,
    prefix="/api/governance",
    tags=["Governance & Human Oversight"]
)

# Feature-4: Lifecycle Tracking
app.include_router(
    lifecycle.router,
    prefix="/api",
    tags=["Lifecycle Tracking"]
)

# Regulatory Workflow
app.include_router(
    regulatory.router,
    prefix="/api/regulatory",
    tags=["Regulatory Workflow"]
)

# PV Audit Trail (immutable compliance logging)
from app.api.routes import pv_audit
app.include_router(
    pv_audit.router,
    prefix="/api/audit",
    tags=["PV Audit Trail"]
)


# Twilio Webhooks (for automated follow-ups)
from app.api.routes import twilio_webhooks, email_webhooks, followup_agent, voice, whatsapp
app.include_router(
    twilio_webhooks.router,
    prefix="/api",
    tags=["Twilio Webhooks"]
)

# Voice (Phone) Webhooks
app.include_router(
    voice.router,
    prefix="/api/voice",
    tags=["Voice Webhooks"]
)

# WhatsApp Webhooks
app.include_router(
    whatsapp.router,
    prefix="/api/whatsapp",
    tags=["WhatsApp Webhooks"]
)

# Email Response Webhooks
app.include_router(
    email_webhooks.router,
    prefix="/api",
    tags=["Email Response Webhooks"]
)

# Follow-Up Agent (Conversational Experience - Public, No Auth)
app.include_router(
    followup_agent.router,
    prefix="/api",
    tags=["Follow-Up Agent"]
)

# Reviewer Dashboard (case review + decisions)
from app.api.routes import reviewer
app.include_router(
    reviewer.router,
    prefix="/api/review",
    tags=["Reviewer Dashboard"]
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
