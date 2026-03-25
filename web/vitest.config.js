import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  test: {
    // Use jsdom environment for DOM testing
    environment: 'jsdom',

    // Global test utilities
    globals: true,

    // Setup files to run before tests
    setupFiles: './src/test/setup.js',

    // Include/exclude patterns
    include: ['**/*.{test,spec}.{js,jsx,ts,tsx}'],
    exclude: ['node_modules', 'dist', '.idea', '.git', '.cache'],

    // Test timeout
    testTimeout: 10000,

    // Retry failed tests
    retry: 0,

    // Environment variables for tests
    env: {
      VITE_API_URL: 'http://localhost:8000',
      // Fake but format-valid values so supabase.js initialises without throwing
      VITE_SUPABASE_URL: 'https://test.supabase.co',
      VITE_SUPABASE_ANON_KEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dGVzdA.test',
    },
  },

  // Resolve aliases to match Vite config
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
