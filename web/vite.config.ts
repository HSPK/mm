import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Disable buffering for streaming responses (video)
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            // Don't buffer video streams
            if (proxyRes.headers['content-type']?.includes('video')) {
              proxyRes.headers['x-accel-buffering'] = 'no'
            }
          })
        },
      },
      '/assets': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
