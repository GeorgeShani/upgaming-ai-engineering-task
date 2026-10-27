import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const proxy = { '/api': process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:8000' };

export default defineConfig({
  plugins: [react()],
  server: { proxy },
  preview: { port: 4173, proxy },
});
