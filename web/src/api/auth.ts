import type {
  ForgotPasswordRequest,
  LocaleUpdate,
  ResendVerificationRequest,
  ResetPasswordRequest,
  UserCreate,
  UserLogin,
  UserRead,
  VerifyEmailRequest,
} from './types';
import { apiClient } from './client';
import { ApiError } from './errors';

export const register = (payload: UserCreate) => apiClient.post<UserRead>('/auth/register', payload);
export const login = (payload: UserLogin) => apiClient.post<UserRead>('/auth/login', payload);
export const logout = () => apiClient.post<void>('/auth/logout');
export const resendVerification = (payload: ResendVerificationRequest) =>
  apiClient.post<void>('/auth/resend-verification', payload);
export const verifyEmail = (payload: VerifyEmailRequest) =>
  apiClient.post<UserRead>('/auth/verify-email', payload);
export const forgotPassword = (payload: ForgotPasswordRequest) =>
  apiClient.post<void>('/auth/forgot-password', payload);
export const resetPassword = (payload: ResetPasswordRequest) =>
  apiClient.post<UserRead>('/auth/reset-password', payload);
export const updateLocale = (payload: LocaleUpdate) => apiClient.put<UserRead>('/auth/locale', payload);

export async function getMe(): Promise<UserRead | null> {
  try {
    return await apiClient.get<UserRead>('/auth/me');
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) return null;
    throw err;
  }
}
