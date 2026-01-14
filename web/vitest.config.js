import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

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
      VITE_API_URL: 'http://localhost:5173',
    },
  },

  // Resolve aliases to match Vite config
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
