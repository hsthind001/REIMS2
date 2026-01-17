import { createRoot } from 'react-dom/client'
import './index.css'
import './styles/globals.css'
import App from './App.tsx'
import { ErrorBoundary } from './components/ErrorBoundary'

console.log('🚀 main.tsx: Starting React app');

const rootElement = document.getElementById('root');
if (!rootElement) {
  console.error('❌ main.tsx: Root element not found!');
  document.body.innerHTML = '<div style="padding: 20px; color: red;">Error: Root element not found!</div>';
} else {
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
})

console.log('✅ main.tsx: Root element found, rendering app');
createRoot(rootElement).render(
  <ErrorBoundary>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </ErrorBoundary>
);
}
