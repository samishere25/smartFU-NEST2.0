import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import CiomsUpload from '../components/CiomsUpload';
import MissingFieldsPanel from '../components/MissingFieldsPanel';
import CiomsDetailsSection from '../components/CiomsDetailsSection';
import { api } from '../utils/api';

const CiomsUploadPage = () => {
  const navigate = useNavigate();
  const [uploadResult, setUploadResult] = useState(null);
  const [recentUploads, setRecentUploads] = useState([]);
  const [loadingRecent, setLoadingRecent] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisReady, setAnalysisReady] = useState(false);
  const [analysisError, setAnalysisError] = useState(null);

  /* ── Reviewer mode (plug-in / plug-out) ───────────── */
  const [includeReviewer, setIncludeReviewer] = useState(() => localStorage.getItem('reviewerMode') === 'true');

  /* ── Repo Document Repository state ─────────────────── */
  const [repoDocs, setRepoDocs] = useState([]);
  const [selectedRepoIds, setSelectedRepoIds] = useState([]);

  /* ── XML Upload state ────────────────────────────────── */
  const [xmlFile, setXmlFile] = useState(null);
  const [xmlUploading, setXmlUploading] = useState(false);
  const [xmlResult, setXmlResult] = useState(null);
  const [xmlError, setXmlError] = useState(null);

  /* ── Repo upload inline state ─────────────────────────── */
  const [repoUploadFile, setRepoUploadFile] = useState(null);
  const [repoUploadName, setRepoUploadName] = useState('');
  const [repoUploadType, setRepoUploadType] = useState('CUSTOM');
  const [repoUploading, setRepoUploading] = useState(false);
  const [repoUploadError, setRepoUploadError] = useState(null);
  const [showRepoUpload, setShowRepoUpload] = useState(false);

  useEffect(() => {
    fetchRecentUploads();
    fetchRepoDocs();
  }, []);

  const fetchRepoDocs = async () => {
    try {
      const data = await api.listRepoDocuments();
      setRepoDocs((data.documents || []).filter(d => d.is_active));
    } catch (err) {
      console.error('Failed to load repo documents:', err);
    }
  };

  const fetchRecentUploads = async () => {
    try {
      setLoadingRecent(true);
      const data = await api.listPdfUploads(0, 10);
      setRecentUploads(data.uploads || []);
    } catch (err) {
      console.error('Failed to load recent uploads:', err);
    } finally {
      setLoadingRecent(false);
    }
  };

  const handleUploadSuccess = async (result) => {
    setUploadResult(result);
    setAnalysisReady(false);
    setAnalysisError(null);
    fetchRecentUploads();

    // Persist selected repo docs to the case BEFORE clearing selection
    if (result.case_id && selectedRepoIds.length > 0) {
      try {
        await api.attachRepoDocs(result.case_id, selectedRepoIds);
        console.log(`📎 Attached ${selectedRepoIds.length} repo docs to case ${result.case_id}`);
      } catch (err) {
        console.error('Failed to attach repo docs:', err);
      }
    }
    setSelectedRepoIds([]);

    // Trigger AI analysis only in AUTO mode (reviewer off)
    if (result.primaryid && !includeReviewer) {
      setAnalyzing(true);
      try {
        await api.analyzeCase(result.primaryid);
        setAnalysisReady(true);
      } catch (err) {
        console.error('AI analysis failed:', err);
        setAnalysisError('AI analysis failed. You can still view the case and run analysis manually.');
      } finally {
        setAnalyzing(false);
      }
    }
    // In PLUG-IN mode, skip auto-analysis — reviewer adds questions on Case page first
  };

  const toggleRepoDoc = (id) => {
    setSelectedRepoIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  /* ── upload a new repo document inline ───────────────── */
  const handleRepoUpload = async () => {
    if (!repoUploadFile || !repoUploadName.trim()) return;
    setRepoUploading(true);
    setRepoUploadError(null);
    try {
      const res = await api.uploadRepoDocument(repoUploadFile, repoUploadName.trim(), repoUploadType);
      // Auto-select the newly uploaded doc
      if (res && res.id) {
        setSelectedRepoIds(prev => [...prev, res.id]);
      }
      // Refresh repo list
      await fetchRepoDocs();
      // Reset form
      setRepoUploadFile(null);
      setRepoUploadName('');
      setRepoUploadType('CUSTOM');
      setShowRepoUpload(false);
    } catch (err) {
      console.error('Repo upload failed:', err);
      setRepoUploadError(err.message || 'Upload failed');
    } finally {
      setRepoUploading(false);
    }
  };

  const handleXmlUpload = async () => {
    if (!xmlFile) return;
    setXmlUploading(true); setXmlError(null); setXmlResult(null);
    try {
      const result = await api.uploadXml(xmlFile);
      setXmlResult(result);
      fetchRecentUploads();
    } catch (e) { setXmlError(e.message); } finally { setXmlUploading(false); }
  };

  const pct = (v) => Math.round((v || 0) * 100);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-[1400px] mx-auto px-6 py-8 space-y-6">

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 tracking-tight">CIOMS PDF Upload</h1>
              <p className="text-sm text-gray-500 mt-0.5">Upload CIOMS Form-I adverse event reports for automated extraction and case creation</p>
            </div>
            {/* Automation Status Badge */}
            <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-bold tracking-wide ${
              includeReviewer
                ? 'bg-blue-50 text-blue-700 border border-blue-200'
                : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
            }`}>
              {includeReviewer ? (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                  REVIEWER MODE
                </>
              ) : (
                <>
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  AUTO MODE ENABLED
                </>
              )}
            </span>
          </div>
          <button
            onClick={() => navigate('/case-analysis')}
            className="self-start sm:self-auto px-4 py-2 bg-white border rounded-lg text-sm text-gray-600 hover:bg-gray-50 shadow-sm flex items-center gap-1.5"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
            </svg>
            View All Cases
          </button>
        </div>

        {/* Main layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Left column: Upload + Result */}
          <div className="lg:col-span-2 space-y-6">

            {/* ═══ REPO FORMS SECTION — shown BEFORE upload so user selects first ═══ */}
            <div className="bg-white rounded-xl border shadow-sm p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                    <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                    {uploadResult ? 'Attach Repository Forms' : 'Step 1: Select Repository Forms'}
                  </h3>
                  <p className="text-[10px] text-gray-400 mt-0.5">{uploadResult ? 'Select forms to attach to this case' : 'Select forms first, then upload CIOMS PDF below'}</p>
                </div>
                <button
                  onClick={() => setShowRepoUpload(v => !v)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-indigo-600 text-white hover:bg-indigo-700 flex items-center gap-1.5 transition-colors"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                  {showRepoUpload ? 'Cancel' : 'Upload New'}
                </button>
              </div>

              {/* ── Inline repo upload form ─────────────── */}
              {showRepoUpload && (
                <div className="bg-indigo-50/50 border border-indigo-200 rounded-lg p-4 space-y-3">
                  <p className="text-xs font-semibold text-indigo-800">Upload a new repository form (e.g. Pregnancy, Paediatric)</p>

                  {/* File picker */}
                  <label className="block">
                    <span className="text-[10px] text-gray-500 font-medium">PDF File</span>
                    <input
                      type="file"
                      accept=".pdf"
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        setRepoUploadFile(f || null);
                        if (f && !repoUploadName) setRepoUploadName(f.name.replace(/\.pdf$/i, ''));
                      }}
                      className="mt-1 block w-full text-xs text-gray-700 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-indigo-100 file:text-indigo-700 hover:file:bg-indigo-200"
                    />
                  </label>

                  {/* Display name */}
                  <label className="block">
                    <span className="text-[10px] text-gray-500 font-medium">Display Name</span>
                    <input
                      type="text"
                      value={repoUploadName}
                      onChange={(e) => setRepoUploadName(e.target.value)}
                      placeholder="e.g. Pregnancy Follow-Up Form"
                      className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-1.5 text-xs text-gray-800 placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    />
                  </label>

                  {/* Form type */}
                  <label className="block">
                    <span className="text-[10px] text-gray-500 font-medium">Form Type</span>
                    <select
                      value={repoUploadType}
                      onChange={(e) => setRepoUploadType(e.target.value)}
                      className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-1.5 text-xs text-gray-800 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
                    >
                      <option value="CUSTOM">Custom</option>
                      <option value="CIOMS">CIOMS</option>
                      <option value="MEDWATCH">MedWatch</option>
                      <option value="PREGNANCY">Pregnancy</option>
                      <option value="PAEDIATRIC">Paediatric</option>
                      <option value="VACCINE">Vaccine</option>
                      <option value="DEVICE">Device</option>
                    </select>
                  </label>

                  {repoUploadError && (
                    <p className="text-[10px] text-red-600">{repoUploadError}</p>
                  )}

                  <button
                    onClick={handleRepoUpload}
                    disabled={repoUploading || !repoUploadFile || !repoUploadName.trim()}
                    className={`w-full px-4 py-2 rounded-lg text-xs font-medium transition-colors ${
                      repoUploading ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                      : (!repoUploadFile || !repoUploadName.trim()) ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                      : 'bg-indigo-600 text-white hover:bg-indigo-700'
                    }`}
                  >
                    {repoUploading ? (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" /></svg>
                        Uploading & Extracting Questions…
                      </span>
                    ) : 'Upload to Repository'}
                  </button>
                </div>
              )}

              {/* ── Existing repo docs list ────────────── */}
              {repoDocs.length > 0 ? (
                <div className="space-y-1.5 max-h-[180px] overflow-y-auto border border-gray-200 rounded-lg p-2">
                  {repoDocs.map(doc => (
                    <label key={doc.id} className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-colors ${selectedRepoIds.includes(doc.id) ? 'bg-blue-50 border border-blue-200' : 'hover:bg-gray-50 border border-transparent'}`}>
                      <input
                        type="checkbox"
                        checked={selectedRepoIds.includes(doc.id)}
                        onChange={() => toggleRepoDoc(doc.id)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-gray-800 truncate">{doc.display_name}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">{doc.form_type}</span>
                          <span className="text-[10px] text-gray-400">{doc.questions_count ?? 0} questions</span>
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4 border border-dashed border-gray-200 rounded-lg">
                  <p className="text-xs text-gray-400">No repository forms yet. Click <strong>Upload New</strong> to add one.</p>
                </div>
              )}
              {selectedRepoIds.length > 0 && (
                <p className="text-[10px] text-emerald-600 font-medium">{selectedRepoIds.length} form(s) selected — will be attached to case & follow-up email</p>
              )}
            </div>

            {/* Upload component */}
            <div className="bg-white rounded-xl border shadow-sm p-5 space-y-4">
              {/* Reviewer Mode Toggle */}
              <div className="flex items-center justify-between border-b border-gray-100 pb-4">
                <div className="flex items-center gap-3">
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeReviewer}
                      onChange={(e) => { setIncludeReviewer(e.target.checked); localStorage.setItem('reviewerMode', e.target.checked); }}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:bg-blue-600 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-full peer-checked:after:border-white" />
                  </label>
                  <div>
                    <p className="text-sm font-semibold text-gray-800">Reviewer Mode</p>
                    <p className="text-[10px] text-gray-400">When ON, reviewer can add questions before AI triggers follow-up</p>
                  </div>
                </div>
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold ${includeReviewer ? 'bg-blue-50 text-blue-700 border border-blue-200' : 'bg-gray-100 text-gray-500 border border-gray-200'}`}>
                  {includeReviewer ? (
                    <>
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                      PLUG-IN
                    </>
                  ) : (
                    <>
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                      AUTO MODE
                    </>
                  )}
                </span>
              </div>
              <CiomsUpload onUploadSuccess={handleUploadSuccess} />
            </div>

            {/* ═══ XML BULK UPLOAD SECTION ═══ */}
            <div className="bg-white rounded-xl border shadow-sm p-5 space-y-4">
              <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
                <svg className="w-4 h-4 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                <div>
                  <h3 className="text-sm font-semibold text-gray-900">XML Bulk Upload</h3>
                  <p className="text-[10px] text-gray-400">ICH E2B (R2/R3) or generic flat XML — multiple cases at once</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2.5">
                  <input
                    type="file"
                    accept=".xml"
                    onChange={(e) => { setXmlFile(e.target.files[0] || null); setXmlResult(null); setXmlError(null); }}
                    className="block w-full text-xs text-gray-500 file:mr-2 file:py-1.5 file:px-3 file:rounded-lg file:border file:border-orange-200 file:bg-orange-50 file:text-orange-700 file:text-xs file:font-medium hover:file:bg-orange-100 file:cursor-pointer"
                  />
                  {xmlFile && (
                    <p className="text-[10px] text-gray-500 truncate">
                      <span className="font-medium">{xmlFile.name}</span> — {(xmlFile.size / 1024).toFixed(1)} KB
                    </p>
                  )}
                  <button
                    onClick={handleXmlUpload}
                    disabled={!xmlFile || xmlUploading}
                    className="w-full px-3 py-2 bg-orange-500 text-white rounded-lg text-xs font-medium hover:bg-orange-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    {xmlUploading ? (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                        </svg>
                        Processing XML...
                      </span>
                    ) : 'Upload XML & Create Cases'}
                  </button>
                  <p className="text-[9px] text-gray-400">Supports ICH E2B R2/R3 and generic flat XML formats</p>
                </div>

                <div>
                  {xmlError && (
                    <p className="text-red-600 text-[10px] bg-red-50 border border-red-200 rounded-lg p-2">{xmlError}</p>
                  )}
                  {xmlResult ? (
                    <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-[10px] space-y-1">
                      <div className="flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        <span className="font-semibold text-emerald-800">XML Processed</span>
                      </div>
                      <p><span className="text-gray-500">File:</span> <span className="font-medium text-gray-800">{xmlResult.filename}</span></p>
                      <p><span className="text-gray-500">Total records:</span> <span className="font-semibold text-gray-800">{xmlResult.total}</span></p>
                      <p><span className="text-gray-500">Created:</span> <span className="font-semibold text-emerald-700">{xmlResult.created}</span></p>
                      {xmlResult.failed > 0 && (
                        <p><span className="text-gray-500">Failed:</span> <span className="font-semibold text-red-600">{xmlResult.failed}</span></p>
                      )}
                    </div>
                  ) : (
                    <div className="h-full flex items-center justify-center text-gray-300 text-[10px] border border-dashed border-gray-200 rounded-lg">
                      Upload an XML file to bulk-create cases
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Upload Result */}
            {uploadResult && (
              <>
                {/* Success banner */}
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center flex-shrink-0">
                    <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-emerald-800">Case Created Successfully</p>
                    <div className="flex flex-wrap items-center gap-3 mt-1.5 text-xs text-emerald-700">
                      <span>Case ID: <span className="font-mono font-semibold">{uploadResult.primaryid}</span></span>
                      <span className="text-emerald-400">|</span>
                      <span>Template: <span className="font-semibold">{uploadResult.template_detected}</span></span>
                      <span className="text-emerald-400">|</span>
                      <span>Confidence: <span className="font-semibold">{pct(uploadResult.extraction_confidence)}%</span></span>
                      {uploadResult.cioms_fields_extracted != null && (
                        <>
                          <span className="text-emerald-400">|</span>
                          <span>Fields Extracted: <span className="font-semibold">{uploadResult.cioms_fields_extracted}</span></span>
                        </>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-3">
                      <button
                        onClick={() => navigate(`/cases/${uploadResult.primaryid}`)}
                        disabled={analyzing}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium ${analyzing ? 'bg-gray-300 text-gray-500 cursor-not-allowed' : 'bg-emerald-600 text-white hover:bg-emerald-700'}`}
                      >
                        View Case
                      </button>
                      <button
                        onClick={() => { setUploadResult(null); setAnalysisReady(false); setAnalysisError(null); }}
                        className="px-3 py-1.5 bg-white border text-gray-600 rounded-lg hover:bg-gray-50 text-xs font-medium"
                      >
                        Upload Another
                      </button>
                    </div>

                    {/* AI Analysis status */}
                    {analyzing && (
                      <div className="flex items-center gap-2 mt-2 text-xs text-blue-700">
                        <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                        </svg>
                        Running AI analysis... generating follow-up questions
                      </div>
                    )}
                    {analysisReady && (
                      <p className="mt-2 text-xs text-emerald-700 font-medium">AI analysis complete — questions ready for review on case page.</p>
                    )}
                    {analysisError && (
                      <p className="mt-2 text-xs text-amber-700">{analysisError}</p>
                    )}
                  </div>
                </div>

                {/* Missing fields from CIOMS extraction */}
                {uploadResult.cioms_missing_fields && uploadResult.cioms_missing_fields.length > 0 && (
                  <MissingFieldsPanel
                    missingFields={uploadResult.cioms_missing_fields.map(f => ({
                      field_name: f,
                      field_display: f.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
                      criticality: ['patient_initials', 'reaction_description', 'suspect_drug_name', 'report_source'].includes(f) ? 'CRITICAL' : 'MEDIUM',
                    }))}
                    completenessScore={uploadResult.data_completeness_score}
                    totalExtracted={uploadResult.cioms_fields_extracted}
                  />
                )}

                {/* Missing criteria from standard validation */}
                {!uploadResult.is_complete && uploadResult.missing_criteria && uploadResult.missing_criteria.length > 0 && (
                  <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                    <div className="flex items-start gap-2">
                      <svg className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                      </svg>
                      <div>
                        <p className="text-sm font-semibold text-amber-800">Incomplete Case Data</p>
                        <p className="text-xs text-amber-700 mt-1">
                          Missing ICH criteria: {uploadResult.missing_criteria.join(', ')}
                        </p>
                        <p className="text-xs text-amber-600 mt-1">
                          The AI analysis pipeline will generate follow-up questions for these fields.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Right column: Recent Uploads + Info */}
          <div className="space-y-6">
            {/* How it works */}
            <div className="bg-white rounded-xl border shadow-sm p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">How It Works</h3>
              <div className="space-y-3">
                {[
                  { step: '1', title: 'Upload PDF', desc: 'Upload a CIOMS Form-I adverse event report' },
                  { step: '2', title: 'Auto-Extract', desc: 'System extracts 24+ fields using rule-based parsing' },
                  { step: '3', title: 'Detect Gaps', desc: 'Missing fields are identified with criticality levels' },
                  { step: '4', title: 'AI Analysis', desc: 'Run full SmartFU pipeline with AI-generated follow-up questions' },
                ].map(({ step, title, desc }) => (
                  <div key={step} className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold flex-shrink-0">
                      {step}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-800">{title}</p>
                      <p className="text-xs text-gray-500">{desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent PDF Uploads */}
            <div className="bg-white rounded-xl border shadow-sm p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">
                Recent PDF Uploads
                {recentUploads.length > 0 && (
                  <span className="ml-1 text-xs font-normal text-gray-500">({recentUploads.length})</span>
                )}
              </h3>

              {loadingRecent ? (
                <div className="flex items-center justify-center py-6">
                  <div className="animate-spin rounded-full h-5 w-5 border-2 border-blue-600 border-t-transparent" />
                </div>
              ) : recentUploads.length === 0 ? (
                <div className="text-center py-6">
                  <p className="text-xs text-gray-400">No PDF uploads yet</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-[400px] overflow-y-auto">
                  {recentUploads.map((u) => (
                    <button
                      key={u.case_id}
                      onClick={() => navigate(`/cases/${u.primaryid}`)}
                      className="w-full text-left p-3 rounded-lg hover:bg-gray-50 transition-colors border border-transparent hover:border-gray-200"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-semibold text-gray-900">{u.primaryid}</span>
                        <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                          u.is_serious
                            ? 'bg-red-50 text-red-700 ring-1 ring-red-600/20'
                            : 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20'
                        }`}>
                          {u.is_serious ? 'Serious' : 'Non-Serious'}
                        </span>
                      </div>
                      <p className="text-xs text-gray-600 mt-1 truncate">{u.suspect_drug} — {u.adverse_event}</p>
                      <div className="flex items-center gap-3 mt-1.5">
                        <div className="flex-1 bg-gray-100 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${pct(u.data_completeness_score) >= 80 ? 'bg-emerald-500' : pct(u.data_completeness_score) >= 60 ? 'bg-blue-500' : 'bg-red-400'}`}
                            style={{ width: `${pct(u.data_completeness_score)}%` }}
                          />
                        </div>
                        <span className="text-[10px] text-gray-500 tabular-nums">{pct(u.data_completeness_score)}%</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CiomsUploadPage;
