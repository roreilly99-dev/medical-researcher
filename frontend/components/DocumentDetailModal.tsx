'use client';

import { useState } from 'react';
import { X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Document, ExtractedData } from '@/lib/types';

interface Props {
  document: Document;
  onClose: () => void;
}

type ModalTab = 'extracted' | 'document';

const FIELD_LABELS: Record<keyof ExtractedData, string> = {
  title:            'Title',
  authors:          'Authors',
  abstract:         'Abstract',
  study_type:       'Study Type',
  methods:          'Methods',
  results:          'Results',
  conclusions:      'Conclusions',
  keywords:         'Keywords',
  sample_size:      'Sample Size',
  key_findings:     'Key Findings',
  limitations:      'Limitations',
  publication_year: 'Publication Year',
  journal:          'Journal',
};

function renderValue(value: unknown): string {
  if (value == null) return '—';
  if (Array.isArray(value)) return value.join(', ') || '—';
  return String(value);
}

export default function DocumentDetailModal({ document: doc, onClose }: Props) {
  const [activeTab, setActiveTab] = useState<ModalTab>('extracted');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between px-6 pt-5 pb-4 border-b border-gray-100">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-gray-900 truncate">
              {doc.extracted_data?.title ?? doc.original_filename}
            </h2>
            <p className="text-sm text-gray-400 mt-0.5 truncate">{doc.original_filename}</p>
          </div>
          <button
            onClick={onClose}
            className="ml-4 text-gray-400 hover:text-gray-700 shrink-0"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Sub-tabs */}
        <div className="flex gap-1 px-6 pt-3 border-b border-gray-100">
          {(['extracted', 'document'] as ModalTab[]).map((t) => (
            <button
              key={t}
              onClick={() => setActiveTab(t)}
              className={`px-4 py-2 text-sm font-medium rounded-t transition-colors ${
                activeTab === t
                  ? 'text-blue-700 border-b-2 border-blue-600'
                  : 'text-gray-500 hover:text-blue-600'
              }`}
            >
              {t === 'extracted' ? 'Extracted Data' : 'Document View'}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 px-6 py-5">
          {activeTab === 'extracted' && (
            <div className="space-y-3">
              {doc.extracted_data ? (
                Object.entries(FIELD_LABELS).map(([key, label]) => {
                  const value = doc.extracted_data?.[key as keyof ExtractedData];
                  return (
                    <div key={key} className="grid grid-cols-3 gap-4 py-2 border-b border-gray-50 last:border-0">
                      <dt className="text-sm font-medium text-gray-500">{label}</dt>
                      <dd className="col-span-2 text-sm text-gray-800">{renderValue(value)}</dd>
                    </div>
                  );
                })
              ) : (
                <p className="text-gray-400 text-sm">No extracted data available.</p>
              )}
            </div>
          )}

          {activeTab === 'document' && (
            <div>
              {doc.images && doc.images.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">
                    Figures ({doc.images.length})
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    {doc.images.slice(0, 8).map((img, i) => (
                      <img
                        key={i}
                        src={`data:image/png;base64,${img}`}
                        alt={`Figure ${i + 1}`}
                        className="rounded-lg border border-gray-200 w-full object-contain max-h-64"
                      />
                    ))}
                  </div>
                </div>
              )}

              {doc.markdown_content ? (
                <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-a:text-blue-600">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {doc.markdown_content}
                  </ReactMarkdown>
                </div>
              ) : (
                <p className="text-gray-400 text-sm">No markdown content available.</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
