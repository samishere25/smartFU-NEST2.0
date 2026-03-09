import React, { useState, useEffect, useCallback } from 'react';

const DOCUMENT_TYPES = [
  { value: 'CIOMS', label: 'CIOMS Form' },
  { value: 'TAFU', label: 'TAFU Checklist' },
  { value: 'PREGNANCY', label: 'Pregnancy Form' },
  { value: 'REVIEWER_NOTE', label: 'Reviewer Note' },
  { value: 'RESPONSE', label: 'Response Document' },
];

const TYPE_COLORS = {
  CIOMS: 'bg-blue-50 text-blue-700 ring-1 ring-blue-600/20',
  TAFU: 'bg-amber-50 text-amber-700 ring-1 ring-amber-600/20',
  PREGNANCY: 'bg-pink-50 text-pink-700 ring-1 ring-pink-600/20',
  REVIEWER_NOTE: 'bg-purple-50 text-purple-700 ring-1 ring-purple-600/20',
  RESPONSE: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20',
};

const DocumentsTab = ({ caseId }) => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedType, setSelectedType] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState(null);
  const [followup, setFollowup] = useState(null);
  const [buildingFollowup, setBuildingFollowup] = useState(false);
  const [sendingFollowup, setSendingFollowup] = useState(false);
  const [sendResult, setSendResult] = useState(null);

  const token = localStorage.getItem('access_token');

  const fetchDocuments = useCallback(async () => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/cases/${caseId}/documents`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Failed to load documents (${res.status})`);
      const data = await res.json();
      setDocuments(data.documents || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [caseId, token]);

  useEffect(() => { fetchDocuments(); }, [fetchDocuments]);

  const handleUpload = async () => {
    if (!selectedType) { setError('Please select a document type.'); return; }
    if (!selectedFile) { setError('Please select a file.'); return; }

    setUploading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', selectedFile);
      form.append('document_type', selectedType);

      const res = await fetch(`/api/cases/${caseId}/documents`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Upload failed (${res.status})`);
      }
      setSelectedType('');
      setSelectedFile(null);
      fetchDocuments();
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId) => {
    if (!window.confirm('Deactivate this document?')) return;
    try {
      const res = await fetch(`/api/cases/${caseId}/documents/${docId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Delete failed');
      fetchDocuments();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleBuildFollowup = async () => {
    setBuildingFollowup(true);
    setError(null);
    setFollowup(null);
    setSendResult(null);
    try {
      // Build via the documents endpoint (gets AI questions + doc-based questions + attachments)
      const res = await fetch(`/api/cases/${caseId}/build-combined-followup`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Build failed (${res.status})`);
      }
      const data = await res.json();
      setFollowup(data);

      // Also register with the reviewer build-combined endpoint so send-followup works
      await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/review/${caseId}/build-combined`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ reviewer_questions: [] }),
      }).catch(() => {}); // best-effort
    } catch (e) {
      setError(e.message);
    } finally {
      setBuildingFollowup(false);
    }
  };

  const handleSendFollowup = async () => {
    setSendingFollowup(true);
    setSendResult(null);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/review/${caseId}/send-followup`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Send failed (${res.status})`);
      }
      const data = await res.json();
      setSendResult({ success: true, ...data });
    } catch (e) {
      setSendResult({ success: false, message: e.message });
    } finally {
      setSendingFollowup(false);
    }
  };

  // Group documents by type
  const grouped = {};
  documents.forEach((doc) => {
    const t = doc.document_type;
    if (!grouped[t]) grouped[t] = [];
    grouped[t].push(doc);
  });

  return (
    <div className="space-y-5">
      {/* Upload Section */}
      <div className="bg-white rounded-xl border shadow-sm p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Upload Document</h3>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[180px]">
            <label className="block text-xs text-gray-500 mb-1">Document Type *</label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Select type...</option>
              {DOCUMENT_TYPES.map((dt) => (
                <option key={dt.value} value={dt.value}>{dt.label}</option>
              ))}
            </select>
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs text-gray-500 mb-1">File</label>
            <input
              type="file"
              onChange={(e) => setSelectedFile(e.target.files[0] || null)}
              className="w-full text-sm text-gray-700 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
          </div>
          <button
            onClick={handleUpload}
            disabled={uploading || !selectedType || !selectedFile}
            className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
        </div>
        {error && (
          <div className="mt-3 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</div>
        )}
      </div>

      {/* Document List (grouped by type) */}
      <div className="bg-white rounded-xl border shadow-sm p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-900">
            Documents <span className="text-gray-400 font-normal">({documents.length})</span>
          </h3>
          <button
            onClick={fetchDocuments}
            disabled={loading}
            className="text-xs text-blue-600 hover:text-blue-800 font-medium"
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>

        {documents.length === 0 && !loading && (
          <p className="text-sm text-gray-400 text-center py-6">No documents uploaded yet.</p>
        )}

        {Object.keys(grouped).length > 0 && (
          <div className="space-y-4">
            {Object.entries(grouped).map(([type, docs]) => (
              <div key={type}>
                <div className="flex items-center gap-2 mb-2">
                  <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide ${TYPE_COLORS[type] || 'bg-gray-100 text-gray-600'}`}>
                    {type.replace('_', ' ')}
                  </span>
                  <span className="text-xs text-gray-400">({docs.length})</span>
                </div>
                <div className="space-y-2 pl-1">
                  {docs.map((doc) => (
                    <div key={doc.id} className="flex items-center justify-between border rounded-lg px-3 py-2 hover:bg-gray-50 transition-colors">
                      <div className="flex items-center gap-3 min-w-0">
                        <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                        </svg>
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-gray-800 truncate">{doc.file_name}</p>
                          <p className="text-[10px] text-gray-400">
                            {doc.uploaded_by && `by ${doc.uploaded_by} · `}
                            {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleString() : ''}
                            {doc.extracted_json && !doc.extracted_json.error && (
                              <span className="ml-2 text-emerald-600 font-medium">
                                Extracted ({doc.extracted_json.fields_extracted || 0} fields)
                              </span>
                            )}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => handleDelete(doc.id)}
                        className="text-gray-300 hover:text-red-500 transition-colors flex-shrink-0 ml-2"
                        title="Deactivate"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Build Combined Follow-Up */}
      <div className="bg-white rounded-xl border shadow-sm p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-900">Combined Follow-Up</h3>
          <button
            onClick={handleBuildFollowup}
            disabled={buildingFollowup}
            className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {buildingFollowup ? 'Building...' : 'Build Combined Follow-Up'}
          </button>
        </div>

        {followup && (
          <div className="space-y-4 mt-2">
            {/* Missing Questions */}
            {followup.missing_questions?.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">
                  AI-Generated Questions ({followup.missing_questions.length})
                </h4>
                <div className="space-y-2">
                  {followup.missing_questions.map((q, i) => (
                    <div key={i} className="border rounded-lg px-3 py-2">
                      <div className="flex items-start gap-2">
                        <span className="text-blue-500 mt-0.5 flex-shrink-0">
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        </span>
                        <div className="min-w-0">
                          <p className="text-sm text-gray-800">{q.question}</p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-[10px] text-gray-400">Field: {q.field_name}</span>
                            {q.is_required && (
                              <span className="text-[10px] text-red-500 font-medium">Required</span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Reviewer Questions */}
            {followup.reviewer_questions?.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">
                  Reviewer Notes ({followup.reviewer_questions.length})
                </h4>
                <div className="space-y-2">
                  {followup.reviewer_questions.map((q, i) => (
                    <div key={i} className="border rounded-lg px-3 py-2 bg-purple-50/30">
                      <p className="text-sm text-gray-800">{q.question || q.note || 'See attached file'}</p>
                      <p className="text-[10px] text-gray-400 mt-1">
                        {q.file_name} {q.uploaded_by && `· ${q.uploaded_by}`}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Attachments */}
            {followup.attachments?.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">
                  Attachments ({followup.attachments.length})
                </h4>
                <div className="space-y-2">
                  {followup.attachments.map((a, i) => (
                    <div key={i} className="flex items-center gap-2 border rounded-lg px-3 py-2">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${TYPE_COLORS[a.document_type] || 'bg-gray-100 text-gray-600'}`}>
                        {a.document_type}
                      </span>
                      <span className="text-sm text-gray-700 truncate">{a.file_name}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {followup.missing_questions?.length === 0 && followup.reviewer_questions?.length === 0 && followup.attachments?.length === 0 && (
              <p className="text-sm text-gray-400 text-center py-4">No follow-up items found for this case.</p>
            )}

            {/* ── Send Combined Follow-Up Button ── */}
            {(followup.missing_questions?.length > 0 || followup.reviewer_questions?.length > 0) && (
              <div className="border-t pt-4 mt-4">
                <button
                  onClick={handleSendFollowup}
                  disabled={sendingFollowup}
                  className={`w-full px-5 py-3 rounded-lg text-sm font-bold text-white transition-colors flex items-center justify-center gap-2 ${
                    sendingFollowup ? 'bg-gray-400' : 'bg-blue-600 hover:bg-blue-700'
                  }`}
                >
                  {sendingFollowup ? (
                    <>
                      <span className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                      Sending via Email + Phone + WhatsApp...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
                      Send Combined Follow-Up ({(followup.missing_questions?.length || 0) + (followup.reviewer_questions?.length || 0)} questions)
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Send result feedback */}
            {sendResult && (
              <div className={`mt-3 rounded-lg px-4 py-3 border ${sendResult.success ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
                <p className={`text-sm font-semibold ${sendResult.success ? 'text-emerald-800' : 'text-red-800'}`}>
                  {sendResult.success
                    ? `✅ Follow-up sent! ${sendResult.questions_sent} questions via ${sendResult.successful_channels?.join(', ')}`
                    : `❌ ${sendResult.message}`}
                </p>
                {sendResult.success && sendResult.failed_channels?.length > 0 && (
                  <p className="text-xs text-amber-700 mt-1">⚠️ Failed: {sendResult.failed_channels.join(', ')}</p>
                )}
              </div>
            )}
          </div>
        )}

        {!followup && !buildingFollowup && (
          <p className="text-xs text-gray-400">Click &quot;Build Combined Follow-Up&quot; to aggregate missing questions, reviewer notes, and checklists.</p>
        )}
      </div>
    </div>
  );
};

export default DocumentsTab;
