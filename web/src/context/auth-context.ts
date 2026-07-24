import { createContext } from 'react';
import type { UserLogin, UserRead } from '@/api/types';

export interface AuthContextValue {
  user: UserRead | null;
  isLoading: boolean;
  refetchUser: () => void;
  login: (payload: UserLogin) => Promise<UserRead>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);
