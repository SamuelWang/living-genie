import type { DiaryEntryCreate, DiaryEntryRead, DiaryEntrySummary, DiaryEntryUpdate } from './types';
import { apiClient } from './client';

export const listDiaryEntries = () => apiClient.get<DiaryEntrySummary[]>('/diaries');
export const getDiaryEntry = (id: string) => apiClient.get<DiaryEntryRead>(`/diaries/${id}`);
export const createDiaryEntry = (payload: DiaryEntryCreate) =>
  apiClient.post<DiaryEntryRead>('/diaries', payload);
export const updateDiaryEntry = (id: string, payload: DiaryEntryUpdate) =>
  apiClient.put<DiaryEntryRead>(`/diaries/${id}`, payload);
export const deleteDiaryEntry = (id: string) => apiClient.del<void>(`/diaries/${id}`);
