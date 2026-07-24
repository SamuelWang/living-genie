import type { ReactElement, ReactNode } from 'react';
import { render as rtlRender } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';
import { AuthProvider } from '@/context/AuthProvider';

interface RenderWithProvidersOptions {
  route?: string;
  withAuthProvider?: boolean;
}

export function renderWithProviders(
  ui: ReactElement,
  { route = '/', withAuthProvider = true }: RenderWithProvidersOptions = {},
) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  function Wrapper({ children }: { children: ReactNode }) {
    const tree = <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>;
    return (
      <QueryClientProvider client={queryClient}>
        {withAuthProvider ? <AuthProvider>{tree}</AuthProvider> : tree}
      </QueryClientProvider>
    );
  }

  return rtlRender(ui, { wrapper: Wrapper });
}
