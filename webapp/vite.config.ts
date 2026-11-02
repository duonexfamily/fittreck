import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // Локально API крутится на uvicorn :8000
    proxy: { '/api': 'http://127.0.0.1:8000' },
    // Разрешаем открывать dev-сервер через HTTPS-туннель (cloudflared)
    allowedHosts: ['.trycloudflare.com'],
  },
})
