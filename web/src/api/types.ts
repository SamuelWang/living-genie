export interface DiaryEntryCreate {
  title: string;
  content?: string;
  entry_date?: string | null;
}

export interface DiaryEntryUpdate {
  title?: string;
  content?: string;
  entry_date?: string;
}

export interface DiaryEntryRead {
  id: string;
  title: string;
  content: string;
  entry_date: string;
  created_at: string;
  updated_at: string;
}

export interface DiaryEntrySummary {
  id: string;
  title: string;
  entry_date: string;
}

export interface UploadResponse {
  url: string;
}

export interface UserCreate {
  email: string;
  password: string;
}

export interface UserRead {
  id: string;
  email: string;
  created_at: string;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface ValidationErrorItem {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export type ApiErrorDetail = string | ValidationErrorItem[];

export interface CitationRead {
  diary_entry_id: string;
  title: string | null;
  entry_date: string | null;
}

export interface MessageRead {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  citations: CitationRead[];
}

export interface ConversationRead {
  id: string;
  created_at: string;
  updated_at: string;
  preview: string | null;
}

export interface ConversationDetailRead extends ConversationRead {
  messages: MessageRead[];
}

export interface SendMessageRequest {
  content: string;
}

export interface ChatCitationsEvent {
  citations: CitationRead[];
}

export interface ChatTokenEvent {
  text: string;
}

export interface ChatDoneEvent {
  id: string;
  created_at: string;
}

export interface ChatErrorEvent {
  message: string;
}
