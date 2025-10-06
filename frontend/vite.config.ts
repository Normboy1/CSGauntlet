import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3002,
    strictPort: true,
    host: true,
    open: true,
    proxy: {
      '/api': {
        target: 'http://localhost:5010',
        changeOrigin: true,
        secure: false
      },
      '/socket.io': {
        target: 'http://localhost:5010',
        changeOrigin: true,
        ws: true
      }
    }
  },
})
