import { defineConfig } from 'vite';

const backend = 'http://127.0.0.1:5001';

export default defineConfig({
  server: {
    proxy: {
      '/socket.io': {
        target: backend,
        ws: true,
        changeOrigin: true,
      },
      // Same-origin during `vite dev` — forward HTTP API to Flask on :5001
      '/api': {
        target: backend,
        changeOrigin: true,
      },
      '/export': {
        target: backend,
        changeOrigin: true,
      },
      '/admin': {
        target: backend,
        changeOrigin: true,
      },
      '/chat': {
        target: backend,
        changeOrigin: true,
      },
      '/scene': {
        target: backend,
        changeOrigin: true,
      },
      '/refine': {
        target: backend,
        changeOrigin: true,
      },
    },
  },
});
