import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
  },
  // Allow Render preview host to access the app in production
  preview: {
    allowedHosts: ['agent-factory-ui.onrender.com'],
  },
  build: {
    outDir: 'dist'
  }
})
