import type { TodoCreate, TodoRead, TodoSummary, TodoUpdate } from './types';
import { apiClient } from './client';

export const listTodos = (completed?: boolean) =>
  apiClient.get<TodoSummary[]>(
    completed === undefined ? '/todos' : `/todos?completed=${completed}`,
  );
export const getTodo = (id: string) => apiClient.get<TodoRead>(`/todos/${id}`);
export const createTodo = (payload: TodoCreate) => apiClient.post<TodoRead>('/todos', payload);
export const updateTodo = (id: string, payload: TodoUpdate) =>
  apiClient.put<TodoRead>(`/todos/${id}`, payload);
export const deleteTodo = (id: string) => apiClient.del<void>(`/todos/${id}`);
