import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ErrorBoundary } from './components/ErrorBoundary'
import { QueryClient, QueryClientProvider } from './lib/queryClient'

console.log('🚀 main.tsx: Starting React app');

const rootElement = document.getElementById('root');
const queryClient = new QueryClient();
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
