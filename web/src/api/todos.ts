import type { TodoCreate, TodoRead, TodoSummary, TodoUpdate } from './types';
import { apiClient } from './client';

export const listTodos = () => apiClient.get<TodoSummary[]>('/todos');
export const getTodo = (id: string) => apiClient.get<TodoRead>(`/todos/${id}`);
export const createTodo = (payload: TodoCreate) => apiClient.post<TodoRead>('/todos', payload);
export const updateTodo = (id: string, payload: TodoUpdate) =>
  apiClient.put<TodoRead>(`/todos/${id}`, payload);
export const deleteTodo = (id: string) => apiClient.del<void>(`/todos/${id}`);
