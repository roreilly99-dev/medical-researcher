'use client';

import { useState } from 'react';
import {
  X, BookOpen, Users, Calendar, FlaskConical, BarChart2,
  Lightbulb, AlertTriangle, Tag, FileText,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Document, ExtractedData } from '@/lib/types';

interface Props {
  document: Document;
  onClose: () => void;
}

type ModalTab = 'summary' | 'extracted' | 'document';

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

// ── Summary helpers ──────────────────────────────────────────────────────────

function MetaPill({ icon, text }: { icon: React.ReactNode; text: string }) {
  if (!text || text === '—') return null;
  return (
    <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium">
      {icon}
      {text}
    </span>
  );
}

function SummarySection({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-50 rounded-xl p-4">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
        {icon}
        {title}
      </h3>
      {children}
    </div>
  );
}

function SummaryTab({ doc }: { doc: Document }) {
  const d = doc.extracted_data;
  if (!d) {
    return <p className="text-gray-400 text-sm">No extracted data available.</p>;
  }

  const authors = Array.isArray(d.authors) && d.authors.length > 0
    ? d.authors.join(', ')
    : null;
  const keywords = Array.isArray(d.keywords) && d.keywords.length > 0
    ? d.keywords
    : [];
  const keyFindings = Array.isArray(d.key_findings) && d.key_findings.length > 0
    ? d.key_findings
    : [];

  return (
    <div className="space-y-4">
      {/* Meta row */}
      <div className="flex flex-wrap gap-2">
        {d.journal && (
          <MetaPill icon={<BookOpen className="w-3 h-3" />} text={d.journal} />
        )}
        {d.publication_year && (
          <MetaPill icon={<Calendar className="w-3 h-3" />} text={String(d.publication_year)} />
        )}
        {d.study_type && (
          <MetaPill icon={<FlaskConical className="w-3 h-3" />} text={d.study_type} />
        )}
        {d.sample_size && (
          <MetaPill icon={<BarChart2 className="w-3 h-3" />} text={`n = ${d.sample_size}`} />
        )}
      </div>

      {/* Authors */}
      {authors && (
        <div className="flex items-start gap-2 text-sm text-gray-600">
          <Users className="w-4 h-4 text-gray-400 mt-0.5 shrink-0" />
          <span>{authors}</span>
        </div>
      )}

      {/* Abstract */}
      {d.abstract && (
        <SummarySection icon={<FileText className="w-4 h-4 text-blue-500" />} title="Abstract">
          <p className="text-sm text-gray-700 leading-relaxed">{d.abstract}</p>
        </SummarySection>
      )}

      {/* Key Findings */}
      {keyFindings.length > 0 && (
        <SummarySection icon={<Lightbulb className="w-4 h-4 text-amber-500" />} title="Key Findings">
          <ul className="space-y-1.5">
            {keyFindings.map((finding, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="mt-1 flex-shrink-0 w-4 h-4 bg-amber-100 text-amber-700 rounded-full text-xs flex items-center justify-center font-semibold">
                  {i + 1}
                </span>
                {finding}
              </li>
            ))}
          </ul>
        </SummarySection>
      )}

      {/* Conclusions */}
      {d.conclusions && (
        <SummarySection icon={<BarChart2 className="w-4 h-4 text-green-500" />} title="Conclusions">
          <p className="text-sm text-gray-700 leading-relaxed">{d.conclusions}</p>
        </SummarySection>
      )}

      {/* Limitations */}
      {d.limitations && (
        <SummarySection icon={<AlertTriangle className="w-4 h-4 text-orange-400" />} title="Limitations">
          <p className="text-sm text-gray-700 leading-relaxed">{d.limitations}</p>
        </SummarySection>
      )}

      {/* Keywords */}
      {keywords.length > 0 && (
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-600 mb-2">
            <Tag className="w-4 h-4" />
            Keywords
          </h3>
          <div className="flex flex-wrap gap-1.5">
            {keywords.map((kw, i) => (
              <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Document view ─────────────────────────────────────────────────────────────

function DocumentViewTab({ doc }: { doc: Document }) {
  return (
    <div>
      {/* Rendered Markdown */}
      {doc.markdown_content ? (
        <div
          className={[
            'prose prose-sm max-w-none',
            'prose-headings:font-semibold prose-headings:text-gray-900 prose-headings:mt-6 prose-headings:mb-2',
            'prose-h1:text-xl prose-h2:text-lg prose-h3:text-base',
            'prose-p:text-gray-700 prose-p:leading-relaxed',
            'prose-a:text-blue-600 prose-a:no-underline hover:prose-a:underline',
            'prose-strong:text-gray-800',
            'prose-ul:my-2 prose-li:my-0.5',
            'prose-table:text-sm prose-th:bg-gray-50 prose-th:text-gray-600',
            'prose-blockquote:border-l-4 prose-blockquote:border-blue-200 prose-blockquote:bg-blue-50 prose-blockquote:py-1 prose-blockquote:px-3 prose-blockquote:rounded-r',
            'prose-code:bg-gray-100 prose-code:px-1 prose-code:rounded prose-code:text-pink-600',
            'prose-pre:bg-gray-900 prose-pre:text-gray-100',
          ].join(' ')}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {doc.markdown_content}
          </ReactMarkdown>
        </div>
      ) : (
        <p className="text-gray-400 text-sm">No document content available.</p>
      )}

      {/* Figures — shown below the text content, numbered and full-width */}
      {doc.images && doc.images.length > 0 && (
        <div className="mt-10 pt-6 border-t border-gray-100">
          <h3 className="text-base font-semibold text-gray-800 mb-4">
            Figures &amp; Images
            <span className="ml-2 text-sm font-normal text-gray-400">({doc.images.length})</span>
          </h3>
          <div className="space-y-6">
            {doc.images.map((img, i) => (
              <figure key={i} className="flex flex-col items-center gap-2">
                <img
                  src={`data:image/png;base64,${img}`}
                  alt={`Figure ${i + 1}`}
                  className="rounded-lg border border-gray-200 max-w-full object-contain"
                  style={{ maxHeight: '480px' }}
                />
                <figcaption className="text-xs text-gray-400 italic">
                  Figure {i + 1}
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Modal ─────────────────────────────────────────────────────────────────────

const TAB_CONFIG: { id: ModalTab; label: string }[] = [
  { id: 'summary',  label: 'Summary' },
  { id: 'document', label: 'Document View' },
  { id: 'extracted', label: 'All Fields' },
];

export default function DocumentDetailModal({ document: doc, onClose }: Props) {
  const [activeTab, setActiveTab] = useState<ModalTab>('summary');

  function handleBackdropClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === e.currentTarget) onClose();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">

        {/* ── Header ── */}
        <div className="flex items-start justify-between px-6 pt-5 pb-4 border-b border-gray-100">
          <div className="min-w-0 flex-1 pr-4">
            <h2 className="text-lg font-semibold text-gray-900 leading-snug">
              {doc.extracted_data?.title ?? doc.original_filename}
            </h2>
            <p className="text-xs text-gray-400 mt-1 truncate">{doc.original_filename}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 shrink-0 transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* ── Sub-tabs ── */}
        <div className="flex gap-1 px-6 pt-3 pb-0 border-b border-gray-100">
          {TAB_CONFIG.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === id
                  ? 'text-blue-700 border-b-2 border-blue-600'
                  : 'text-gray-500 hover:text-blue-600'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* ── Body ── */}
        <div className="overflow-y-auto flex-1 px-6 py-5">

          {activeTab === 'summary' && <SummaryTab doc={doc} />}

          {activeTab === 'document' && <DocumentViewTab doc={doc} />}

          {activeTab === 'extracted' && (
            <div className="space-y-0">
              {doc.extracted_data ? (
                Object.entries(FIELD_LABELS).map(([key, label]) => {
                  const value = doc.extracted_data?.[key as keyof ExtractedData];
                  return (
                    <div
                      key={key}
                      className="grid grid-cols-3 gap-4 py-2.5 border-b border-gray-50 last:border-0"
                    >
                      <dt className="text-sm font-medium text-gray-500">{label}</dt>
                      <dd className="col-span-2 text-sm text-gray-800 break-words">{renderValue(value)}</dd>
                    </div>
                  );
                })
              ) : (
                <p className="text-gray-400 text-sm">No extracted data available.</p>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
