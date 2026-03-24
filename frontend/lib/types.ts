export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface ExtractedData {
  title?: string | null;
  authors?: string[] | null;
  abstract?: string | null;
  study_type?: string | null;
  methods?: string | null;
  results?: string | null;
  conclusions?: string | null;
  keywords?: string[] | null;
  sample_size?: string | null;
  key_findings?: string[] | null;
  limitations?: string | null;
  publication_year?: number | null;
  journal?: string | null;
}

export interface Document {
  id: string;
  filename: string;
  original_filename: string;
  upload_date: string;
  status: DocumentStatus;
  markdown_content?: string | null;
  extracted_data?: ExtractedData | null;
  error_message?: string | null;
  file_path?: string | null;
  images?: string[] | null;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatSource {
  document_id: string;
  filename: string;
  content: string;
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
}
