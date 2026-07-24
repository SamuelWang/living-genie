import type { ReactNode } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getMe, login as apiLogin, logout as apiLogout } from '@/api/auth';
import { AuthContext } from './auth-context';

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: getMe,
    staleTime: Infinity,
    retry: false,
  });

  const value = {
    user: data ?? null,
    isLoading,
    refetchUser: () => void refetch(),
    login: async (payload: Parameters<typeof apiLogin>[0]) => {
      const user = await apiLogin(payload);
      queryClient.setQueryData(['auth', 'me'], user);
      return user;
    },
    logout: async () => {
      await apiLogout();
      queryClient.setQueryData(['auth', 'me'], null);
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
