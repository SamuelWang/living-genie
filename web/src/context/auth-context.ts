import { createContext } from 'react';
import type { UserRead } from '@/api/types';

export interface AuthContextValue {
  user: UserRead | null;
  isLoading: boolean;
  refetchUser: () => void;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);
