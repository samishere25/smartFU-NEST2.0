import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../utils/api';

const FORM_TYPES = ['TAFU', 'PREGNANCY', 'CUSTOM'];

const TYPE_BADGE = {
  TAFU: 'bg-blue-50 text-blue-700 border-blue-200',
  PREGNANCY: 'bg-pink-50 text-pink-700 border-pink-200',
  CUSTOM: 'bg-gray-50 text-gray-600 border-gray-200',
};

const RepoDocumentsBlock = () => {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Upload state
  const [file, setFile] = useState(null);
  const [displayName, setDisplayName] = useState('');
  const [formType, setFormType] = useState('TAFU');
  const [description, setDescription] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  // Preview state
  const [expandedId, setExpandedId] = useState(null);
  const [previewQuestions, setPreviewQuestions] = useState({});

  const fetchDocs = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.listRepoDocuments();
      setDocs(data.documents || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchDocs(); }, [fetchDocs]);

  const handleUpload = async () => {
    if (!file || !displayName.trim()) return;
    setUploading(true);
    setUploadError(null);
    try {
      await api.uploadRepoDocument(file, displayName.trim(), formType, description.trim());
      setFile(null);
      setDisplayName('');
      setDescription('');
      fetchDocs();
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId, name) => {
    if (!window.confirm(`Delete "${name}" from repository?`)) return;
    try {
      await api.deleteRepoDocument(docId);
      fetchDocs();
    } catch (err) {
      alert('Delete failed: ' + err.message);
    }
  };

  const togglePreview = async (docId) => {
    if (expandedId === docId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(docId);
    if (!previewQuestions[docId]) {
      try {
        const data = await api.getRepoDocumentQuestions(docId);
        setPreviewQuestions(prev => ({ ...prev, [docId]: data.extracted_questions || [] }));
      } catch (err) {
        setPreviewQuestions(prev => ({ ...prev, [docId]: [] }));
      }
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-gray-900">Global Form Repository</h3>
          {docs.length > 0 && (
            <span className="px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-700 text-[10px] font-semibold border border-blue-200">
              {docs.length}
            </span>
          )}
        </div>
        <button onClick={fetchDocs} className="text-[10px] text-[#2563EB] hover:underline font-medium">Refresh</button>
      </div>

      {/* Upload Panel */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-4">
        <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider mb-2">Upload New Form</p>
        <div className="grid grid-cols-2 gap-2 mb-2">
          <select
            value={formType}
            onChange={(e) => setFormType(e.target.value)}
            className="px-2 py-1.5 border border-gray-200 rounded text-xs bg-white"
          >
            {FORM_TYPES.map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Display name (e.g. TAFU Form v2.1)"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="px-2 py-1.5 border border-gray-200 rounded text-xs"
          />
        </div>
        <input
          type="text"
          placeholder="Description (optional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full px-2 py-1.5 border border-gray-200 rounded text-xs mb-2"
        />
        <div className="flex items-center gap-2">
          <input
            type="file"
            accept=".pdf"
            onChange={(e) => setFile(e.target.files[0])}
            className="flex-1 text-[10px] text-gray-500 file:mr-2 file:py-1 file:px-2 file:rounded file:border file:border-gray-200 file:bg-white file:text-gray-700 file:text-[10px] file:font-medium hover:file:bg-gray-50 file:cursor-pointer"
          />
          <button
            onClick={handleUpload}
            disabled={!file || !displayName.trim() || uploading}
            className="px-3 py-1.5 bg-[#2563EB] text-white rounded text-xs font-medium hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed whitespace-nowrap"
          >
            {uploading ? 'Uploading...' : 'Upload & Extract'}
          </button>
        </div>
        {uploadError && <p className="text-red-600 text-[10px] mt-1.5">{uploadError}</p>}
      </div>

      {/* Document List */}
      {loading ? (
        <div className="flex items-center justify-center py-6">
          <div className="animate-spin rounded-full h-5 w-5 border-2 border-blue-600 border-t-transparent" />
        </div>
      ) : error ? (
        <p className="text-red-600 text-xs text-center py-4">{error}</p>
      ) : docs.length === 0 ? (
        <p className="text-gray-400 text-xs text-center py-6">No forms uploaded yet. Upload a PDF above to get started.</p>
      ) : (
        <div className="divide-y divide-gray-100 max-h-[300px] overflow-y-auto">
          {docs.map((doc) => (
            <div key={doc.id} className="py-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-semibold border ${TYPE_BADGE[doc.form_type] || TYPE_BADGE.CUSTOM}`}>
                    {doc.form_type}
                  </span>
                  <span className="text-xs font-medium text-gray-800 truncate">{doc.display_name}</span>
                  <span className="text-[10px] text-gray-400 flex-shrink-0">
                    {doc.questions_count} questions
                  </span>
                  {doc.extraction_status === 'FAILED' && (
                    <span className="px-1 py-0.5 rounded text-[8px] font-semibold bg-red-50 text-red-600 border border-red-200">FAILED</span>
                  )}
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <button
                    onClick={() => togglePreview(doc.id)}
                    className="px-2 py-1 text-[10px] text-[#2563EB] hover:bg-blue-50 rounded font-medium"
                  >
                    {expandedId === doc.id ? 'Hide' : 'Preview'}
                  </button>
                  <button
                    onClick={() => handleDelete(doc.id, doc.display_name)}
                    className="px-2 py-1 text-[10px] text-red-500 hover:bg-red-50 rounded font-medium"
                  >
                    Delete
                  </button>
                </div>
              </div>

              {/* Question Preview */}
              {expandedId === doc.id && (
                <div className="mt-2 ml-6 bg-gray-50 border border-gray-200 rounded p-2 max-h-[200px] overflow-y-auto">
                  {(previewQuestions[doc.id] || []).length > 0 ? (
                    <div className="space-y-1">
                      {previewQuestions[doc.id].map((q, i) => (
                        <div key={i} className="flex items-start gap-1.5 text-[10px]">
                          <span className="text-gray-400 font-mono flex-shrink-0">{i + 1}.</span>
                          <span className="text-gray-700">{q.question || q.field_name || JSON.stringify(q)}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-400 text-[10px] text-center py-2">No questions extracted</p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default RepoDocumentsBlock;
