'use client';

import { useState } from 'react';
import { FlaskConical } from 'lucide-react';
import UploadTab from '@/components/UploadTab';
import DocumentsTab from '@/components/DocumentsTab';
import ChatTab from '@/components/ChatTab';

type Tab = 'upload' | 'documents' | 'chat';

const TABS: { id: Tab; label: string }[] = [
  { id: 'upload', label: 'Upload' },
  { id: 'documents', label: 'Documents' },
  { id: 'chat', label: 'Chat' },
];

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>('upload');
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleTabChange = (tab: Tab) => {
    setActiveTab(tab);
    if (tab === 'documents') {
      // Trigger refresh when switching to documents tab
      setRefreshTrigger(prev => prev + 1);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3 h-16">
            <div className="flex items-center justify-center w-9 h-9 bg-blue-600 rounded-lg">
              <FlaskConical className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">Medical Research Assistant</h1>
              <p className="text-xs text-gray-500">AI-powered paper analysis &amp; retrieval</p>
            </div>
          </div>
        </div>
      </header>

      {/* Tab navigation */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        <div className="flex gap-1 border-b border-gray-200">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={`tab-btn ${activeTab === tab.id ? 'tab-btn-active' : 'tab-btn-inactive'}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="py-6">
          {activeTab === 'upload' && <UploadTab onUploaded={() => handleTabChange('documents')} />}
          {activeTab === 'documents' && <DocumentsTab refreshTrigger={refreshTrigger} />}
          {activeTab === 'chat' && <ChatTab />}
        </div>
      </div>
    </div>
  );
}
