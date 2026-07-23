import type { UserCreate, UserLogin, UserRead } from './types';
import { apiClient } from './client';
import { ApiError } from './errors';

export const register = (payload: UserCreate) => apiClient.post<UserRead>('/auth/register', payload);
export const login = (payload: UserLogin) => apiClient.post<UserRead>('/auth/login', payload);
export const logout = () => apiClient.post<void>('/auth/logout');

export async function getMe(): Promise<UserRead | null> {
  try {
    return await apiClient.get<UserRead>('/auth/me');
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) return null;
    throw err;
  }
}
