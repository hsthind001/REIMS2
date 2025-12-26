import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react({
      // Babel plugins for optimization
      babel: {
        plugins: [
          // Remove propTypes in production
          ['babel-plugin-transform-react-remove-prop-types', { removeImport: true }],
        ],
      },
    }),
    // Bundle analyzer (only in analyze mode)
    ...(process.env.ANALYZE ? [visualizer({
      open: true,
      filename: 'dist/stats.html',
      gzipSize: true,
      brotliSize: true,
    })] : []),
  ],

  // Optimize dependencies
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'react-leaflet',
      'leaflet',
      'react-pdf',
      'recharts',
      '@mui/material',
      '@mui/icons-material',
      'axios',
    ],
    // Exclude large dependencies that don't need pre-bundling
    exclude: ['@emotion/react', '@emotion/styled'],
  },

  build: {
    target: 'es2020', // Modern browsers for better optimization
    minify: 'terser', // Better minification than esbuild
    cssCodeSplit: true,
    sourcemap: false, // Disable sourcemaps in production for smaller bundle

    // Terser options for aggressive minification
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.log in production
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.info'], // Remove specific console methods
      },
      mangle: {
        safari10: true, // Safari 10+ compatibility
      },
    },

    // Rollup options for advanced code splitting
    rollupOptions: {
      output: {
        // Aggressive code splitting strategy
        manualChunks: (id) => {
          // Core React libraries (loaded on every page)
          if (id.includes('node_modules/react/') ||
              id.includes('node_modules/react-dom/') ||
              id.includes('node_modules/react-router-dom/')) {
            return 'vendor-react';
          }

          // MUI components (heavy, separate chunk)
          if (id.includes('node_modules/@mui/')) {
            return 'vendor-mui';
          }

          // Emotion (MUI dependency)
          if (id.includes('node_modules/@emotion/')) {
            return 'vendor-emotion';
          }

          // Charting library (only needed on dashboard/analytics pages)
          if (id.includes('node_modules/recharts/') ||
              id.includes('node_modules/chart.js/')) {
            return 'charts';
          }

          // Map libraries (only needed on map pages)
          if (id.includes('node_modules/leaflet/') ||
              id.includes('node_modules/react-leaflet/')) {
            return 'maps';
          }

          // PDF libraries (only needed for PDF viewing/export)
          if (id.includes('node_modules/react-pdf/') ||
              id.includes('node_modules/jspdf')) {
            return 'pdf';
          }

          // Export libraries (only needed for export functionality)
          if (id.includes('node_modules/xlsx/')) {
            return 'export';
          }

          // Axios (API client)
          if (id.includes('node_modules/axios/')) {
            return 'vendor-axios';
          }

          // Lucide icons (design system)
          if (id.includes('node_modules/lucide-react/')) {
            return 'icons';
          }

          // Framer Motion (animations)
          if (id.includes('node_modules/framer-motion/')) {
            return 'animations';
          }

          // All other node_modules
          if (id.includes('node_modules/')) {
            return 'vendor-misc';
          }
        },

        // Optimize chunk names
        chunkFileNames: () => {
          return `assets/js/[name]-[hash].js`;
        },
        assetFileNames: (assetInfo) => {
          const name = assetInfo.name || 'asset';
          if (/\.(png|jpe?g|svg|gif|tiff|bmp|ico)$/i.test(name)) {
            return `assets/images/[name]-[hash][extname]`;
          } else if (/\.css$/i.test(name)) {
            return `assets/css/[name]-[hash][extname]`;
          } else if (/\.(woff2?|eot|ttf|otf)$/i.test(name)) {
            return `assets/fonts/[name]-[hash][extname]`;
          }
          return `assets/[name]-[hash][extname]`;
        },
      },
    },

    // Chunk size warnings
    chunkSizeWarningLimit: 500, // 500KB per chunk

    // Asset inlining threshold (smaller files inlined as base64)
    assetsInlineLimit: 4096, // 4KB

    // CSS options
    cssMinify: true,
  },

  // Server options for development
  server: {
    port: 5173,
    host: '0.0.0.0',
    strictPort: true,
    hmr: {
      overlay: true, // Show errors as overlay
    },
    // Proxy API requests to backend (optional)
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },

  // Preview options (for production preview)
  preview: {
    port: 4173,
    host: '0.0.0.0',
    strictPort: true,
  },

  // Enable JSON import optimization
  json: {
    stringify: true, // Inline JSON as strings
  },

  // Worker options
  worker: {
    format: 'es', // Use ES modules for workers
  },
})
