import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import cesium from 'vite-plugin-cesium'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const rawTarget = env.VITE_API_URL || process.env.VITE_API_URL || 'https://threatatlas-backend.onrender.com';
  // Normalize target: trim, strip trailing slash, and remove any trailing /api/v1 prefix
  const target = rawTarget
    .trim()
    .replace(/\/+$/, '')
    .replace(/\/api\/v1\/?$/, '');

  return {
    plugins: [
      react(),
      tailwindcss(),
      (cesium as any)(),
    ],
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  };
})
