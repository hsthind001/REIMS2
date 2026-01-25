import { createRoot } from 'react-dom/client'
import './index.css'
import './styles/globals.css'
import App from './App.tsx'
import { ErrorBoundary } from './components/ErrorBoundary'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAuthStore } from './store/authStore'

console.log('🚀 main.tsx: Starting React app');

// Inject organization header for API requests without rewriting every fetch call.
const baseFetch = window.fetch.bind(window);
window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
  const request = new Request(input, init);
  const url = request.url;
  const isApiRequest = url.includes('/api/');
  if (!isApiRequest) {
    return baseFetch(request);
  }

  const currentOrg = useAuthStore.getState().currentOrganization;
  if (!currentOrg) {
    return baseFetch(request);
  }

  const headers = new Headers(request.headers);
  if (!headers.has('X-Organization-ID')) {
    headers.set('X-Organization-ID', currentOrg.id.toString());
  }

  const nextRequest = new Request(request, { headers });
  return baseFetch(nextRequest);
};

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
})

const rootElement = document.getElementById('root');
if (!rootElement) {
  console.error('❌ main.tsx: Root element not found!');
  document.body.innerHTML = '<div style="padding: 20px; color: red;">Error: Root element not found!</div>';
} else {
  console.log('✅ main.tsx: Root element found, rendering app');
  createRoot(rootElement).render(
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
