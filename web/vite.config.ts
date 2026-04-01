import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    proxy: {
      '/socket.io': {
        target: 'http://localhost:5001',
        ws: true,
        changeOrigin: true,
      },
      // Same-origin during `vite dev` — Flask serves these on :5001
      '/chat': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      '/scene': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
    },
  },
});
