import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    include: ['react-leaflet', 'leaflet', 'react-pdf']
  },
  build: {
    target: 'es2015',
    cssCodeSplit: true,
    rollupOptions: {
      output: {
        manualChunks: {
          // Core React libraries
          'vendor': ['react', 'react-dom', 'react-router-dom'],
          // Charting library (heavy)
          'charts': ['recharts'],
          // Map libraries
          'maps': ['leaflet', 'react-leaflet'],
          // Export libraries (only needed for exports)
          'export': ['jspdf', 'jspdf-autotable', 'xlsx'],
        }
      }
    },
    chunkSizeWarningLimit: 500,
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
  },
})
