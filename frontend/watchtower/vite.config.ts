import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 8000,
    proxy: {
      '/logs/stream': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/gov/stream': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/orion/send': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/logs/chat': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
})
