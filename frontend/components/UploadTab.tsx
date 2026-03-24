'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, FileText, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { uploadDocuments } from '@/lib/api';

interface Props {
  onUploaded: () => void;
}

type UploadState = 'idle' | 'uploading' | 'success' | 'error';

export default function UploadTab({ onUploaded }: Props) {
  const [files, setFiles] = useState<File[]>([]);
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  const onDrop = useCallback((accepted: File[]) => {
    setFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name));
      return [...prev, ...accepted.filter((f) => !existing.has(f.name))];
    });
    setUploadState('idle');
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: true,
  });

  const removeFile = (name: string) =>
    setFiles((prev) => prev.filter((f) => f.name !== name));

  const handleUpload = async () => {
    if (!files.length) return;
    setUploadState('uploading');
    setErrorMsg('');
    try {
      await uploadDocuments(files);
      setUploadState('success');
      setFiles([]);
      setTimeout(() => {
        setUploadState('idle');
        onUploaded();
      }, 1500);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed';
      setErrorMsg(msg);
      setUploadState('error');
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-1">Upload Research Papers</h2>
        <p className="text-sm text-gray-500 mb-5">
          Upload one or more PDF files to extract key medical information and enable AI-powered search.
        </p>

        {/* Drop zone */}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
            isDragActive
              ? 'border-blue-400 bg-blue-50'
              : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
          }`}
        >
          <input {...getInputProps()} />
          <UploadCloud className="mx-auto mb-3 w-12 h-12 text-blue-400" />
          {isDragActive ? (
            <p className="text-blue-600 font-medium">Drop the files here…</p>
          ) : (
            <>
              <p className="font-medium text-gray-700">Drag &amp; drop PDF files here</p>
              <p className="text-sm text-gray-400 mt-1">or click to browse</p>
            </>
          )}
        </div>

        {/* File list */}
        {files.length > 0 && (
          <ul className="mt-4 space-y-2">
            {files.map((file) => (
              <li
                key={file.name}
                className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <FileText className="w-4 h-4 text-blue-500 shrink-0" />
                  <span className="text-sm text-gray-700 truncate">{file.name}</span>
                  <span className="text-xs text-gray-400 shrink-0">
                    ({(file.size / 1024).toFixed(0)} KB)
                  </span>
                </div>
                <button
                  onClick={() => removeFile(file.name)}
                  className="ml-2 text-gray-400 hover:text-red-500 shrink-0"
                  aria-label="Remove file"
                >
                  <X className="w-4 h-4" />
                </button>
              </li>
            ))}
          </ul>
        )}

        {/* Status feedback */}
        {uploadState === 'success' && (
          <div className="mt-4 flex items-center gap-2 text-green-600 bg-green-50 rounded-lg px-4 py-3">
            <CheckCircle className="w-5 h-5" />
            <span className="text-sm font-medium">
              Upload successful! Redirecting to Documents…
            </span>
          </div>
        )}
        {uploadState === 'error' && (
          <div className="mt-4 flex items-center gap-2 text-red-600 bg-red-50 rounded-lg px-4 py-3">
            <AlertCircle className="w-5 h-5" />
            <span className="text-sm">{errorMsg}</span>
          </div>
        )}

        <button
          onClick={handleUpload}
          disabled={!files.length || uploadState === 'uploading'}
          className="btn-primary mt-5 w-full flex items-center justify-center gap-2"
        >
          {uploadState === 'uploading' ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Uploading…
            </>
          ) : (
            <>
              <UploadCloud className="w-4 h-4" />
              Upload {files.length > 0 ? `${files.length} file${files.length > 1 ? 's' : ''}` : 'Files'}
            </>
          )}
        </button>
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">What happens after upload?</h3>
        <ol className="space-y-2 text-sm text-gray-600">
          {[
            'PDF is converted to structured markdown using Docling',
            'GPT-4o-mini extracts key medical metadata (title, authors, methods, etc.)',
            'Text is chunked and embedded for semantic search',
            'You can then query your documents via the Chat tab',
          ].map((step, i) => (
            <li key={i} className="flex gap-2">
              <span className="flex-shrink-0 w-5 h-5 bg-blue-100 text-blue-700 rounded-full text-xs flex items-center justify-center font-medium">
                {i + 1}
              </span>
              {step}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
