import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    proxy: {
      '/api': {
        // 固定到 5001：与 app.py 默认端口、gunicorn 与 nginx 配置保持一致，避免多端口错配。
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
