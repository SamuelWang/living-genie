import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getMe } from '@/api/auth';
import { AuthContext } from './auth-context';

export function AuthProvider({ children }: { children: ReactNode }) {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: getMe,
    staleTime: Infinity,
    retry: false,
  });

  return (
    <AuthContext.Provider value={{ user: data ?? null, isLoading, refetchUser: () => void refetch() }}>
      {children}
    </AuthContext.Provider>
  );
}
