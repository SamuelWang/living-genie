import type { UploadResponse } from './types';
import { apiClient } from './client';

export const uploadImage = (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient.post<UploadResponse>('/uploads/images', formData);
};
