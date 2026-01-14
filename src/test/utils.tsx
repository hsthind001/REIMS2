import { render, type RenderOptions } from '@testing-library/react';
import type { ReactElement } from 'react';
import { ToastProvider } from '../hooks/ToastContext';

// Custom render function that includes common providers
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  withToast?: boolean;
}

export function renderWithProviders(
  ui: ReactElement,
  { withToast = true, ...options }: CustomRenderOptions = {}
) {
  function Wrapper({ children }: { children: React.ReactNode }) {
    if (withToast) {
      return <ToastProvider>{children}</ToastProvider>;
    }
    return <>{children}</>;
  }

  return render(ui, { wrapper: Wrapper, ...options });
}

// Re-export everything from testing library
export * from '@testing-library/react';
export { renderWithProviders as render };
