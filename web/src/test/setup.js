/**
 * Test setup file for Vitest + React Testing Library
 *
 * This file runs before all tests and sets up:
 * - jest-dom matchers for better assertions
 * - Cleanup after each test
 * - Mock browser APIs (matchMedia, IntersectionObserver, etc.)
 */

import { expect, afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import * as matchers from '@testing-library/jest-dom/matchers';

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers);

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock window.matchMedia (needed for responsive components)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock IntersectionObserver (if needed for lazy loading)
globalThis.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() {
    return [];
  }
  unobserve() {}
};

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(),
    readText: vi.fn().mockResolvedValue(''),
  },
});

// Mock console methods to reduce noise in tests (optional)
globalThis.console = {
  ...console,
  // Uncomment to suppress console logs in tests:
  // log: vi.fn(),
  // debug: vi.fn(),
  // info: vi.fn(),
  // warn: vi.fn(),
  // error: vi.fn(),
};

// Environment variables are configured in vitest.config.js
// Vite uses import.meta.env, which is automatically available in tests
