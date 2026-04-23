'use client';

import { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, FileText, X, CheckCircle, AlertCircle, Loader2, BookOpen, Brain, Database } from 'lucide-react';
import { uploadDocuments, connectToDocumentProcessing } from '@/lib/api';
import type { Document, ProcessingUpdate, ProcessingStage } from '@/lib/types';

interface Props {
  onUploaded: () => void;
}

interface ProcessingDocument extends Document {
  currentStage?: ProcessingStage;
  stageData?: any;
}

type UploadState = 'idle' | 'uploading' | 'success' | 'error';

export default function UploadTab({ onUploaded }: Props) {
  const [files, setFiles] = useState<File[]>([]);
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [processingDocuments, setProcessingDocuments] = useState<ProcessingDocument[]>([]);
  const [websocketCleanups, setWebsocketCleanups] = useState<Map<string, () => void>>(new Map());

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

  // Cleanup WebSocket connections on unmount
  useEffect(() => {
    return () => {
      websocketCleanups.forEach(cleanup => cleanup());
    };
  }, [websocketCleanups]);

  const handleUpload = async () => {
    if (!files.length) return;
    setUploadState('uploading');
    setErrorMsg('');
    try {
      const uploadedDocs = await uploadDocuments(files);
      
      // Set up WebSocket connections for each document
      const cleanups = new Map<string, () => void>();
      const processingDocs = uploadedDocs.map(doc => ({ ...doc }));

      for (const doc of processingDocs) {
        const cleanup = connectToDocumentProcessing(
          doc.id,
          (update: ProcessingUpdate) => {
            setProcessingDocuments(prev => 
              prev.map(d => 
                d.id === update.document_id 
                  ? { ...d, currentStage: update.stage, stageData: update.data }
                  : d
              )
            );
          },
          (error) => {
            console.error('WebSocket error for document', doc.id, error);
          }
        );
        cleanups.set(doc.id, cleanup);
      }

      setWebsocketCleanups(cleanups);
      setProcessingDocuments(processingDocs);
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

        {/* Processing documents */}
        {processingDocuments.length > 0 && (
          <div className="mt-6 space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">Processing Documents</h3>
            {processingDocuments.map((doc) => (
              <ProcessingDocumentCard key={doc.id} document={doc} />
            ))}
          </div>
        )}

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

function ProcessingDocumentCard({ document }: { document: ProcessingDocument }) {
  const getStageInfo = (stage?: ProcessingStage) => {
    switch (stage) {
      case 'docling_started':
        return { label: 'Converting PDF with Docling...', icon: BookOpen, color: 'text-blue-600' };
      case 'docling_completed':
        return { label: 'PDF converted to Markdown', icon: CheckCircle, color: 'text-green-600' };
      case 'llm_extraction_started':
        return { label: 'Extracting medical metadata...', icon: Brain, color: 'text-blue-600' };
      case 'llm_extraction_completed':
        return { label: 'Medical metadata extracted', icon: CheckCircle, color: 'text-green-600' };
      case 'embedding_started':
        return { label: 'Creating embeddings...', icon: Database, color: 'text-blue-600' };
      case 'embedding_completed':
        return { label: 'Document embedded in vector DB', icon: CheckCircle, color: 'text-green-600' };
      case 'processing_completed':
        return { label: 'Processing completed!', icon: CheckCircle, color: 'text-green-600' };
      case 'processing_failed':
        return { label: 'Processing failed', icon: AlertCircle, color: 'text-red-600' };
      default:
        return { label: 'Waiting to process...', icon: Loader2, color: 'text-gray-500' };
    }
  };

  const stageInfo = getStageInfo(document.currentStage);
  const Icon = stageInfo.icon;

  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-white">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-medium text-gray-900 truncate">{document.original_filename}</h4>
        <div className={`flex items-center gap-2 ${stageInfo.color}`}>
          <Icon className="w-4 h-4" />
          <span className="text-sm font-medium">{stageInfo.label}</span>
        </div>
      </div>

      {/* Show markdown preview if available */}
      {document.markdown_content && (
        <div className="mt-3">
          <h5 className="text-sm font-medium text-gray-700 mb-2">Markdown Preview:</h5>
          <div className="bg-gray-50 rounded p-3 max-h-32 overflow-y-auto">
            <pre className="text-xs text-gray-600 whitespace-pre-wrap">
              {document.markdown_content.substring(0, 500)}
              {document.markdown_content.length > 500 && '...'}
            </pre>
          </div>
        </div>
      )}

      {/* Show extracted data if available */}
      {document.extracted_data && (
        <div className="mt-3 grid grid-cols-2 gap-4">
          <div>
            <h5 className="text-sm font-medium text-gray-700 mb-1">Title</h5>
            <p className="text-sm text-gray-600">{document.extracted_data.title || 'Not extracted'}</p>
          </div>
          <div>
            <h5 className="text-sm font-medium text-gray-700 mb-1">Authors</h5>
            <p className="text-sm text-gray-600">
              {document.extracted_data.authors?.join(', ') || 'Not extracted'}
            </p>
          </div>
          <div>
            <h5 className="text-sm font-medium text-gray-700 mb-1">Study Type</h5>
            <p className="text-sm text-gray-600">{document.extracted_data.study_type || 'Not extracted'}</p>
          </div>
          <div>
            <h5 className="text-sm font-medium text-gray-700 mb-1">Publication Year</h5>
            <p className="text-sm text-gray-600">{document.extracted_data.publication_year || 'Not extracted'}</p>
          </div>
        </div>
      )}

      {/* Show error if failed */}
      {document.status === 'failed' && document.error_message && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded">
          <p className="text-sm text-red-700">{document.error_message}</p>
        </div>
      )}
    </div>
  );
}
