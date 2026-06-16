import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/upload-csv': 'http://localhost:8000',
      '/upload-metadata': 'http://localhost:8000',
      '/analyze': 'http://localhost:8000',
      '/compute-causal-impact': 'http://localhost:8000',
      '/cate': 'http://localhost:8000',
      '/sessions': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/sample-data': 'http://localhost:8000',
    },
  },
})
