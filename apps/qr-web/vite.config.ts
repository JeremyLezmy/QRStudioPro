import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const envBase = (
  globalThis as {
    process?: {
      env?: Record<string, string | undefined>;
    };
  }
).process?.env?.VITE_BASE_PATH;

const base = envBase ?? '/';

export default defineConfig({
  base,
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
  },
});
