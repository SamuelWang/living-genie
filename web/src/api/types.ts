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
