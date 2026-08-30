import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{js,jsx}'],
    /* Unit tests mock or inject their API client, so this only affects the
       live integration test — which points src/api.js at the local backend and
       skips itself when nothing is listening there. */
    env: {
      VITE_API_BASE: process.env.CULIN_API || 'http://127.0.0.1:8001',
      VITE_OPENAI_API_KEY: process.env.VITE_OPENAI_API_KEY || process.env.OPENAI_API_KEY || '',
      VITE_OPENAI_MODEL: process.env.VITE_OPENAI_MODEL || process.env.OPENAI_MODEL || 'gpt-4o-mini',
    },
  },
  server: {
    port: 5173,
    open: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
