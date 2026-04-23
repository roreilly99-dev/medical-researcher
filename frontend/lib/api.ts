import axios from 'axios';
import type { Document, ChatMessage, ChatResponse, ProcessingUpdate } from './types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  timeout: 120000,
});

export async function uploadDocuments(files: File[]): Promise<Document[]> {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));

  const response = await api.post<Document[]>('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function getDocuments(): Promise<Document[]> {
  const response = await api.get<Document[]>('/documents/');
  return response.data;
}

export async function getDocument(id: string): Promise<Document> {
  const response = await api.get<Document>(`/documents/${id}`);
  return response.data;
}

export async function deleteDocument(id: string): Promise<void> {
  await api.delete(`/documents/${id}`);
}

export async function sendChatMessage(
  message: string,
  history: ChatMessage[]
): Promise<ChatResponse> {
  const response = await api.post<ChatResponse>('/chat/', {
    message,
    conversation_history: history,
  });
  return response.data;
}

export function connectToDocumentProcessing(
  documentId: string,
  onUpdate: (update: ProcessingUpdate) => void,
  onError?: (error: Event) => void
): () => void {
  const wsUrl = `${BASE_URL.replace('http', 'ws')}/api/v1/ws/document/${documentId}`;
  const ws = new WebSocket(wsUrl);

  ws.onmessage = (event) => {
    try {
      const data: ProcessingUpdate = JSON.parse(event.data);
      onUpdate(data);
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    onError?.(error);
  };

  ws.onclose = () => {
    console.log('WebSocket connection closed');
  };

  // Return cleanup function
  return () => {
    ws.close();
  };
}
