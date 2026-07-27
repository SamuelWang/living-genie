import type { ConversationRead, ConversationDetailRead } from './types';
import { apiClient } from './client';

export const listConversations = () => apiClient.get<ConversationRead[]>('/conversations');
export const getConversation = (id: string) =>
  apiClient.get<ConversationDetailRead>(`/conversations/${id}`);
export const createConversation = () => apiClient.post<ConversationRead>('/conversations');
export const deleteConversation = (id: string) => apiClient.del<void>(`/conversations/${id}`);
