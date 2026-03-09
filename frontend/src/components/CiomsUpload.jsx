import React, { useState, useRef } from 'react';
import { api } from '../utils/api';

const CiomsUpload = ({ onUploadSuccess }) => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileSelect = (selectedFile) => {
    setError(null);
    if (!selectedFile) return;

    if (!selectedFile.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are allowed.');
      return;
    }
    if (selectedFile.size > 20 * 1024 * 1024) {
      setError('File size must be under 20 MB.');
      return;
    }
    setFile(selectedFile);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) handleFileSelect(droppedFile);
  };

  const handleUpload = async () => {
    if (!file) return;
    try {
      setUploading(true);
      setError(null);
      const result = await api.uploadCiomsPdf(file);
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      if (onUploadSuccess) onUploadSuccess(result);
    } catch (err) {
      setError(err.message || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleRemoveFile = () => {
    setFile(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="bg-white rounded-xl border shadow-sm p-6">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-lg bg-purple-50 flex items-center justify-center">
          <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-900">CIOMS Form-I Upload</h3>
          <p className="text-xs text-gray-500">Upload a CIOMS adverse event report PDF</p>
        </div>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !file && fileInputRef.current?.click()}
        className={`
          border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer
          ${dragOver ? 'border-purple-400 bg-purple-50' : file ? 'border-emerald-300 bg-emerald-50' : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={(e) => handleFileSelect(e.target.files?.[0])}
        />

        {file ? (
          <div className="flex flex-col items-center gap-2">
            <div className="w-10 h-10 rounded-lg bg-emerald-100 flex items-center justify-center">
              <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-sm font-medium text-gray-900">{file.name}</p>
            <p className="text-xs text-gray-500">{(file.size / 1024).toFixed(1)} KB</p>
            <button
              onClick={(e) => { e.stopPropagation(); handleRemoveFile(); }}
              className="text-xs text-red-600 hover:text-red-700 font-medium mt-1"
            >
              Remove file
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-sm text-gray-600">
              <span className="font-medium text-purple-600">Click to upload</span> or drag and drop
            </p>
            <p className="text-xs text-gray-400">PDF files only, up to 20 MB</p>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2">
          <svg className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-xs text-red-700">{error}</p>
        </div>
      )}

      {/* Upload button */}
      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        className={`
          w-full mt-4 px-4 py-2.5 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-colors
          ${!file || uploading
            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
            : 'bg-purple-600 text-white hover:bg-purple-700'
          }
        `}
      >
        {uploading ? (
          <>
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
            Processing PDF...
          </>
        ) : (
          <>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Upload & Extract
          </>
        )}
      </button>
    </div>
  );
};

export default CiomsUpload;
