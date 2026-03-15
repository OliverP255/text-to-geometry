import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    proxy: {
      '/scene': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      '/socket.io': {
        target: 'http://localhost:5001',
        ws: true,
      },
    },
  },
});
