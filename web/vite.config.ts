import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    proxy: {
      '/socket.io': {
        target: 'http://localhost:5001',
        ws: true,
        changeOrigin: true,
      },
    },
  },
});
