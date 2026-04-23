'use client';

import { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Trash2, Eye, FileText, AlertCircle } from 'lucide-react';
import { getDocuments, deleteDocument } from '@/lib/api';
import type { Document } from '@/lib/types';
import DocumentDetailModal from './DocumentDetailModal';

const STATUS_STYLES: Record<string, string> = {
  pending:    'bg-gray-100 text-gray-600',
  processing: 'bg-yellow-100 text-yellow-700',
  completed:  'bg-green-100 text-green-700',
  failed:     'bg-red-100 text-red-600',
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`status-badge ${STATUS_STYLES[status] ?? 'bg-gray-100 text-gray-600'}`}>
      {status === 'processing' && (
        <svg className="w-3 h-3 animate-spin" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 100 16v-4l-3 3 3 3v-4a8 8 0 01-8-8z" />
        </svg>
      )}
      {status}
    </span>
  );
}

interface Props {
  refreshTrigger?: number;
}

export default function DocumentsTab({ refreshTrigger }: Props) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);

  const fetchDocuments = useCallback(async () => {
    try {
      const docs = await getDocuments();
      setDocuments(docs);
      setError('');
    } catch {
      setError('Failed to load documents. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments, refreshTrigger]);

  // Poll while any document is pending or processing
  useEffect(() => {
    const hasPending = documents.some(
      (d) => d.status === 'pending' || d.status === 'processing'
    );
    if (!hasPending) return;
    const interval = setInterval(fetchDocuments, 3000);
    return () => clearInterval(interval);
  }, [documents, fetchDocuments]);

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this document?')) return;
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch {
      alert('Failed to delete document.');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-gray-400">
        <RefreshCw className="w-6 h-6 animate-spin mr-2" />
        Loading documents…
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          Documents{' '}
          <span className="ml-1 text-sm font-normal text-gray-400">({documents.length})</span>
        </h2>
        <button
          onClick={fetchDocuments}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-blue-600 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-red-600 bg-red-50 rounded-lg px-4 py-3">
          <AlertCircle className="w-5 h-5" />
          <span className="text-sm">{error}</span>
        </div>
      )}

      {documents.length === 0 && !error ? (
        <div className="card p-12 text-center text-gray-400">
          <FileText className="mx-auto w-10 h-10 mb-3 opacity-40" />
          <p>No documents yet. Upload some PDFs to get started.</p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left px-4 py-3 font-medium text-gray-600">File</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600 hidden md:table-cell">Uploaded</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600 hidden lg:table-cell">Title</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {documents.map((doc) => (
                <tr
                  key={doc.id}
                  onClick={() => doc.status === 'completed' && setSelectedDoc(doc)}
                  className={`transition-colors ${
                    doc.status === 'completed'
                      ? 'hover:bg-blue-50 cursor-pointer'
                      : 'hover:bg-gray-50'
                  }`}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-blue-400 shrink-0" />
                      <span className="font-medium text-gray-800 truncate max-w-[180px]">
                        {doc.original_filename}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-500 hidden md:table-cell">
                    {new Date(doc.upload_date).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={doc.status} />
                    {doc.status === 'failed' && doc.error_message && (
                      <p className="text-xs text-red-500 mt-0.5 max-w-[200px] truncate" title={doc.error_message}>
                        {doc.error_message}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500 hidden lg:table-cell truncate max-w-[250px]">
                    {doc.extracted_data?.title ?? '—'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      {doc.status === 'completed' && (
                        <Eye className="w-4 h-4 text-blue-300" aria-hidden />
                      )}
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDelete(doc.id); }}
                        className="text-gray-400 hover:text-red-500 transition-colors"
                        aria-label="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedDoc && (
        <DocumentDetailModal
          document={selectedDoc}
          onClose={() => setSelectedDoc(null)}
        />
      )}
    </div>
  );
}
