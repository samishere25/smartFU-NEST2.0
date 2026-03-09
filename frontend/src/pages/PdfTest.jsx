import React, { useState, useEffect } from 'react';

/*  ──────────────────────────────────────────────
    PDF Ingestion Page
    Upload PDF → View Case → Analyze → Lifecycle
    + List of all previously uploaded PDFs
    ────────────────────────────────────────────── */

const API = '';

const authHeaders = () => {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export default function PdfTest() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [primaryid, setPrimaryid] = useState(null);
  const [caseId, setCaseId] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);
  const [caseData, setCaseData] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [lifecycleData, setLifecycleData] = useState(null);
  const [loading, setLoading] = useState('');
  const [error, setError] = useState('');

  // Uploaded PDFs list
  const [pdfUploads, setPdfUploads] = useState([]);
  const [uploadsLoading, setUploadsLoading] = useState(false);

  // Fetch uploaded PDFs on mount and after upload
  const fetchPdfUploads = async () => {
    setUploadsLoading(true);
    try {
      const res = await fetch(`${API}/api/cases/pdf-uploads`, {
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      });
      if (res.ok) {
        const data = await res.json();
        setPdfUploads(data.uploads || []);
      }
    } catch (e) {
      console.error('Failed to fetch PDF uploads:', e);
    } finally {
      setUploadsLoading(false);
    }
  };

  useEffect(() => {
    fetchPdfUploads();
  }, []);

  // ── 1. Upload PDF ──
  const handleUpload = async () => {
    if (!selectedFile) return;
    setError('');
    setLoading('Uploading PDF…');
    setCaseData(null);
    setAnalysisResult(null);
    setLifecycleData(null);

    try {
      const form = new FormData();
      form.append('file', selectedFile);
      const res = await fetch(`${API}/api/cases/upload-pdf`, {
        method: 'POST',
        headers: authHeaders(),
        body: form,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setUploadResult(data);
      setPrimaryid(data.primaryid);
      setCaseId(data.case_id);
      // Refresh the uploads list
      fetchPdfUploads();
    } catch (e) {
      setError('Upload failed: ' + e.message);
    } finally {
      setLoading('');
    }
  };

  // ── 2. Fetch Case ──
  const fetchCase = async () => {
    if (!primaryid) return;
    setError('');
    setLoading('Fetching case…');
    try {
      const res = await fetch(`${API}/api/cases/by-primaryid/${primaryid}`, {
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setCaseData(await res.json());
    } catch (e) {
      setError('Fetch case failed: ' + e.message);
    } finally {
      setLoading('');
    }
  };

  // ── 3. Run Analysis ──
  const runAnalysis = async () => {
    if (!primaryid) return;
    setError('');
    setLoading('Running SmartFU analysis… (may take 15-30s)');
    try {
      const res = await fetch(`${API}/api/cases/by-primaryid/${primaryid}/analyze`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setAnalysisResult(await res.json());
    } catch (e) {
      setError('Analysis failed: ' + e.message);
    } finally {
      setLoading('');
    }
  };

  // ── 4. Fetch Lifecycle ──
  const fetchLifecycle = async () => {
    if (!caseId) return;
    setError('');
    setLoading('Fetching lifecycle…');
    try {
      const res = await fetch(`${API}/api/lifecycle/${caseId}`, {
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setLifecycleData(await res.json());
    } catch (e) {
      setError('Lifecycle fetch failed: ' + e.message);
    } finally {
      setLoading('');
    }
  };

  // ── Select a previously uploaded PDF case ──
  const selectPdfCase = async (upload) => {
    setError('');
    setPrimaryid(upload.primaryid);
    setCaseId(upload.case_id);
    setUploadResult({
      case_id: upload.case_id,
      primaryid: upload.primaryid,
      filename: upload.filename,
      data_completeness_score: upload.data_completeness_score,
      case_status: upload.case_status,
    });
    setCaseData(null);
    setAnalysisResult(null);
    setLifecycleData(null);

    // Auto-fetch case data
    setLoading('Fetching case…');
    try {
      const res = await fetch(`${API}/api/cases/by-primaryid/${upload.primaryid}`, {
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      });
      if (res.ok) {
        setCaseData(await res.json());
      }
    } catch (e) {
      console.error('Failed to auto-fetch case:', e);
    } finally {
      setLoading('');
    }
  };

  // ── helpers ──
  const KV = ({ data, keys }) => (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
      <tbody>
        {keys.map((k) => (
          <tr key={k} style={{ borderBottom: '1px solid #f3f4f6' }}>
            <td style={{ padding: '6px 8px', fontWeight: 600, width: '40%', color: '#374151' }}>{k}</td>
            <td style={{ padding: '6px 8px', color: '#111827' }}>
              {data[k] == null ? <span style={{ color: '#9ca3af' }}>—</span> : String(data[k])}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );

  const Section = ({ title, children }) => (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, marginBottom: 16 }}>
      <h2 style={{ margin: '0 0 12px', fontSize: 18, fontWeight: 700 }}>{title}</h2>
      {children}
    </div>
  );

  const Btn = ({ onClick, disabled, color, children }) => (
    <button
      onClick={onClick}
      disabled={disabled || !!loading}
      style={{
        background: !disabled && !loading ? color : '#9ca3af',
        color: '#fff',
        border: 'none',
        borderRadius: 6,
        padding: '8px 20px',
        cursor: !disabled && !loading ? 'pointer' : 'not-allowed',
        fontWeight: 600,
        fontSize: 14,
      }}
    >
      {children}
    </button>
  );

  return (
    <div style={{ maxWidth: 1200, margin: '32px auto', padding: '0 16px', fontFamily: 'Inter, system-ui, sans-serif' }}>
      {/* Page Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#111827' }}>PDF Case Ingestion</h1>
        <p style={{ color: '#6b7280', margin: '4px 0 0', fontSize: 13 }}>
          Upload pharmacovigilance PDFs to create cases. Click any uploaded file to view details.
        </p>
      </div>

      {/* STATUS BAR */}
      {loading && (
        <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 6, padding: '8px 12px', marginBottom: 12, fontSize: 13, color: '#1d4ed8' }}>
          ⏳ {loading}
        </div>
      )}
      {error && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 6, padding: '8px 12px', marginBottom: 12, fontSize: 13, color: '#dc2626' }}>
          {error}
        </div>
      )}

      {/* Two-column layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: 20, alignItems: 'start' }}>

        {/* LEFT: Upload + Files List */}
        <div>
          {/* Upload Card */}
          <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, marginBottom: 16, background: '#fff' }}>
            <h2 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 600, color: '#374151' }}>Upload New PDF</h2>
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              style={{ width: '100%', fontSize: 13, marginBottom: 10 }}
            />
            <Btn onClick={handleUpload} disabled={!selectedFile} color="#2563eb">
              Upload PDF
            </Btn>
          </div>

          {/* Uploaded Files List */}
          <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, background: '#fff' }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: '#374151' }}>
                Uploaded PDFs
                <span style={{ fontWeight: 400, color: '#9ca3af', marginLeft: 6, fontSize: 12 }}>({pdfUploads.length})</span>
              </h2>
              <button
                onClick={fetchPdfUploads}
                disabled={uploadsLoading}
                style={{ background: 'none', border: 'none', color: '#2563eb', cursor: 'pointer', fontSize: 12, fontWeight: 500 }}
              >
                {uploadsLoading ? '...' : 'Refresh'}
              </button>
            </div>

            <div style={{ maxHeight: 480, overflowY: 'auto' }}>
              {pdfUploads.length === 0 && !uploadsLoading && (
                <div style={{ padding: 24, textAlign: 'center', color: '#9ca3af', fontSize: 13 }}>
                  No PDFs uploaded yet
                </div>
              )}
              {uploadsLoading && pdfUploads.length === 0 && (
                <div style={{ padding: 24, textAlign: 'center', color: '#6b7280', fontSize: 13 }}>
                  Loading…
                </div>
              )}
              {pdfUploads.map((u) => {
                const isSelected = caseId === u.case_id;
                return (
                  <div
                    key={u.case_id}
                    onClick={() => selectPdfCase(u)}
                    style={{
                      padding: '10px 16px',
                      borderBottom: '1px solid #f3f4f6',
                      cursor: 'pointer',
                      background: isSelected ? '#eff6ff' : '#fff',
                      borderLeft: isSelected ? '3px solid #2563eb' : '3px solid transparent',
                      transition: 'background 0.15s',
                    }}
                    onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = '#f9fafb'; }}
                    onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = '#fff'; }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
                      <span style={{ fontSize: 14 }}>📄</span>
                      <span style={{ fontSize: 13, fontWeight: 600, color: '#111827', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                        {u.filename}
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: 8, fontSize: 11, color: '#6b7280', paddingLeft: 22 }}>
                      <span>ID: {u.primaryid}</span>
                      <span>•</span>
                      <span>{u.suspect_drug || '—'}</span>
                    </div>
                    <div style={{ display: 'flex', gap: 8, fontSize: 11, paddingLeft: 22, marginTop: 2 }}>
                      <span style={{ color: u.data_completeness_score >= 0.8 ? '#059669' : u.data_completeness_score >= 0.5 ? '#d97706' : '#dc2626' }}>
                        {Math.round((u.data_completeness_score || 0) * 100)}% complete
                      </span>
                      {u.is_serious && <span style={{ color: '#dc2626', fontWeight: 600 }}>● Serious</span>}
                      <span style={{ color: '#9ca3af' }}>
                        {u.created_at ? new Date(u.created_at).toLocaleDateString() : ''}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* RIGHT: Case Details Pipeline */}
        <div>

          {/* Upload Result */}
          {uploadResult && (
            <Section title="Upload Result">
              <KV
                data={uploadResult}
                keys={Object.keys(uploadResult).filter(k => uploadResult[k] != null && typeof uploadResult[k] !== 'object')}
              />
              {uploadResult.missing_criteria?.length > 0 && (
                <p style={{ color: '#dc2626', fontSize: 13, marginTop: 6 }}>
                  Missing: {uploadResult.missing_criteria.join(', ')}
                </p>
              )}
            </Section>
          )}

          {/* No case selected placeholder */}
          {!primaryid && !uploadResult && (
            <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 40, textAlign: 'center', background: '#fafafa' }}>
              <div style={{ fontSize: 40, marginBottom: 12, opacity: 0.3 }}>📄</div>
              <p style={{ color: '#9ca3af', fontSize: 14, margin: 0 }}>
                Upload a new PDF or select an existing one from the list
              </p>
            </div>
          )}

          {/* 2: CASE INFO */}
      {primaryid && (
        <Section title="2. Case Info">
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 10 }}>
            <span style={{ fontSize: 14, color: '#6b7280' }}>primaryid: <b>{primaryid}</b></span>
            <Btn onClick={fetchCase} color="#059669">Fetch Case</Btn>
          </div>
          {caseData && (
            <KV
              data={caseData}
              keys={[
                'suspect_drug', 'adverse_event', 'patient_age', 'patient_sex',
                'is_serious', 'reporter_type', 'event_date', 'event_outcome',
                'drug_dose', 'drug_route', 'reporter_country', 'data_completeness_score',
              ]}
            />
          )}
        </Section>
      )}

      {/* 3: ANALYSIS */}
      {primaryid && (
        <Section title="3. SmartFU Analysis">
          <Btn onClick={runAnalysis} color="#7c3aed">Run SmartFU Analysis</Btn>

          {analysisResult && (
            <div style={{ marginTop: 12 }}>
              <KV
                data={{
                  risk_score: analysisResult.analysis?.risk_score,
                  risk_level: analysisResult.analysis?.risk_level,
                  completeness_score: analysisResult.analysis?.completeness_score,
                  decision: analysisResult.analysis?.decision,
                  followup_required: analysisResult.analysis?.followup_required,
                  questions_count: analysisResult.analysis?.questions?.length ?? 0,
                  confidence: analysisResult.confidence,
                }}
                keys={[
                  'risk_score', 'risk_level', 'completeness_score',
                  'decision', 'followup_required', 'questions_count', 'confidence',
                ]}
              />

              {/* Questions */}
              {analysisResult.analysis?.questions?.length > 0 && (
                <div style={{ marginTop: 10 }}>
                  <h4 style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>Generated Questions:</h4>
                  <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13, color: '#4b5563' }}>
                    {analysisResult.analysis.questions.map((q, i) => (
                      <li key={i} style={{ marginBottom: 2 }}>
                        <b>{q.field || q.field_name}</b>: {q.question}
                        {q.criticality && <span style={{ color: '#9ca3af' }}> [{q.criticality}]</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Follow-up channels */}
              {analysisResult.automated_followup?.successful_channels && (
                <div style={{ marginTop: 10 }}>
                  <h4 style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>Follow-up Channels:</h4>
                  <KV
                    data={analysisResult.automated_followup}
                    keys={['successful_channels', 'failed_channels', 'decision_id', 'message']}
                  />
                </div>
              )}
            </div>
          )}
        </Section>
      )}

      {/* 4: LIFECYCLE */}
      {caseId && (
        <Section title="4. Lifecycle Tracking">
          <Btn onClick={fetchLifecycle} color="#d97706">Fetch Lifecycle</Btn>

          {lifecycleData && (
            <div style={{ marginTop: 12 }}>
              <KV
                data={lifecycleData}
                keys={Object.keys(lifecycleData).filter(
                  (k) => typeof lifecycleData[k] !== 'object' || lifecycleData[k] === null
                )}
              />
            </div>
          )}
        </Section>
      )}

      {/* PIPELINE STATUS */}
      <div style={{ marginTop: 16, padding: '10px 16px', background: '#f9fafb', borderRadius: 8, fontSize: 12, color: '#6b7280' }}>
        <b>Pipeline:</b>{' '}
        {!uploadResult && '⬜ Waiting for PDF'}
        {uploadResult && !caseData && '✅ Uploaded → ⬜ Fetch Case'}
        {caseData && !analysisResult && '✅ Uploaded → ✅ Case → ⬜ Analysis'}
        {analysisResult && !lifecycleData && '✅ Uploaded → ✅ Case → ✅ Analyzed → ⬜ Lifecycle'}
        {lifecycleData && '✅ Complete Pipeline'}
      </div>

        </div>
      </div>
    </div>
  );
}
