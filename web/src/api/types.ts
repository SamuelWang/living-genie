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

export interface TodoCreate {
  title: string;
  description?: string | null;
  due_date?: string | null;
}

export interface TodoUpdate {
  title?: string;
  description?: string | null;
  due_date?: string | null;
  completed?: boolean;
}

export interface TodoRead {
  id: string;
  title: string;
  description: string | null;
  due_date: string | null;
  completed: boolean;
  created_at: string;
  updated_at: string;
}

export interface TodoSummary {
  id: string;
  title: string;
  due_date: string | null;
  completed: boolean;
}

export interface UploadResponse {
  url: string;
}

export interface UserCreate {
  email: string;
  password: string;
  locale: string;
}

export interface UserRead {
  id: string;
  email: string;
  locale: string;
  created_at: string;
  email_verified: boolean;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface ResendVerificationRequest {
  email: string;
}

export interface VerifyEmailRequest {
  email: string;
  code: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  email: string;
  code: string;
  new_password: string;
}

export interface LocaleUpdate {
  locale: string;
}

export interface ValidationErrorItem {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export type ApiErrorDetail = string | ValidationErrorItem[];

export interface MessageReference {
  source_type: 'diary_entry' | 'todo';
  id: string;
  title: string | null;
  entry_date: string | null;
  completed: boolean | null;
}

export interface MessageRead {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  references: MessageReference[];
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

export interface ChatReferencesEvent {
  references: MessageReference[];
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
