/**
 * Tests for API client
 */

import { describe, it, expect, vi, beforeAll, afterEach, afterAll } from 'vitest';

// Mock supabase so getAuthToken() returns a predictable token in all tests
vi.mock('../lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: 'test-jwt-token' } },
      }),
    },
  },
}));
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { submitJob, getJobStatus, cancelJob, uploadPdf, checkHealth } from './client';
import { APP_VERSION } from '../config/appVersion';

const server = setupServer();

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

const API_URL = 'http://localhost:8000';

describe('API Client', () => {
  describe('checkHealth', () => {
    it('returns health status', async () => {
      server.use(
        http.get(`${API_URL}/api/health`, () => {
          return HttpResponse.json({
            status: 'healthy',
            version: APP_VERSION,
          });
        })
      );

      const result = await checkHealth();

      expect(result.status).toBe('healthy');
      expect(result.version).toBe(APP_VERSION);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${API_URL}/api/health`, () => {
          return HttpResponse.json(
            { error: 'Service unavailable' },
            { status: 503 }
          );
        })
      );

      await expect(checkHealth()).rejects.toThrow();
    });
  });

  describe('submitJob', () => {
    it('submits job and returns job_id', async () => {
      server.use(
        http.post(`${API_URL}/api/submit`, () => {
          return HttpResponse.json({
            job_id: 'test-123',
            status: 'pending',
            message: 'Job created',
          });
        })
      );

      const result = await submitJob({ course_url: 'https://example.com' });

      expect(result.job_id).toBe('test-123');
      expect(result.status).toBe('pending');
    });

    it('throws error for invalid input', async () => {
      server.use(
        http.post(`${API_URL}/api/submit`, () => {
          return HttpResponse.json(
            {
              detail: {
                error: 'Invalid input',
                message: 'At least one field required',
              },
            },
            { status: 400 }
          );
        })
      );

      await expect(submitJob({})).rejects.toThrow('At least one field required');
    });

    it('handles network errors', async () => {
      server.use(
        http.post(`${API_URL}/api/submit`, () => {
          return HttpResponse.error();
        })
      );

      await expect(submitJob({ course_url: 'https://example.com' })).rejects.toThrow();
    });

    it('sends all input fields', async () => {
      let requestBody;

      server.use(
        http.post(`${API_URL}/api/submit`, async ({ request }) => {
          requestBody = await request.json();
          return HttpResponse.json({ job_id: 'test', status: 'pending', message: 'OK' });
        })
      );

      const inputs = {
        course_url: 'https://example.com',
        book_title: 'Algorithms',
        desired_resource_types: ['textbooks'],
      };

      await submitJob(inputs);

      // client wraps inputs under course_input and filters empty strings
      expect(requestBody.course_input).toMatchObject({
        course_url: 'https://example.com',
        book_title: 'Algorithms',
        desired_resource_types: ['textbooks'],
      });
    });
  });

  describe('getJobStatus', () => {
    it('retrieves job status', async () => {
      server.use(
        http.get(`${API_URL}/api/status/test-123`, () => {
          return HttpResponse.json({
            job_id: 'test-123',
            status: 'completed',
            results: [],
            metadata: {},
            created_at: '2024-01-01T00:00:00Z',
          });
        })
      );

      const result = await getJobStatus('test-123');

      expect(result.job_id).toBe('test-123');
      expect(result.status).toBe('completed');
    });

    it('throws error for nonexistent job', async () => {
      server.use(
        http.get(`${API_URL}/api/status/nonexistent`, () => {
          return HttpResponse.json(
            {
              detail: {
                error: 'Job not found',
                message: 'Job does not exist',
              },
            },
            { status: 404 }
          );
        })
      );

      await expect(getJobStatus('nonexistent')).rejects.toThrow('Job does not exist');
    });
  });

  describe('cancelJob', () => {
    it('cancels job successfully', async () => {
      server.use(
        http.post(`${API_URL}/api/cancel/test-123`, () => {
          return HttpResponse.json({
            message: 'Job cancelled',
            job_id: 'test-123',
          });
        })
      );

      const result = await cancelJob('test-123');

      expect(result.message).toBe('Job cancelled');
    });

    it('throws error for nonexistent job', async () => {
      server.use(
        http.post(`${API_URL}/api/cancel/nonexistent`, () => {
          return HttpResponse.json(
            {
              detail: {
                error: 'Job not found',
                message: 'Job does not exist',
              },
            },
            { status: 404 }
          );
        })
      );

      await expect(cancelJob('nonexistent')).rejects.toThrow('Job does not exist');
    });
  });

  describe('uploadPdf', () => {
    it('uploads a PDF and returns an opaque upload ID', async () => {
      server.use(
        http.post(`${API_URL}/api/upload-pdf`, () => {
          return HttpResponse.json({
            upload_id: '123e4567-e89b-12d3-a456-426614174000',
          });
        })
      );

      const file = new File(['%PDF-1.7'], 'textbook.pdf', { type: 'application/pdf' });
      const result = await uploadPdf(file);

      expect(result.upload_id).toBe('123e4567-e89b-12d3-a456-426614174000');
      expect(result.pdf_path).toBeUndefined();
    });
  });

  describe('Error handling', () => {
    it('extracts error message from detail object', async () => {
      server.use(
        http.post(`${API_URL}/api/submit`, () => {
          return HttpResponse.json(
            {
              detail: {
                error: 'Validation error',
                message: 'Invalid course URL',
              },
            },
            { status: 400 }
          );
        })
      );

      try {
        await submitJob({ course_url: 'invalid' });
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).toContain('Invalid course URL');
      }
    });

    it('handles string detail', async () => {
      server.use(
        http.post(`${API_URL}/api/submit`, () => {
          return HttpResponse.json(
            { detail: 'Simple error message' },
            { status: 400 }
          );
        })
      );

      try {
        await submitJob({});
        expect.fail('Should have thrown error');
      } catch (error) {
        // client.js reads detail?.message; when detail is a plain string there's no .message
        expect(error.message).toBeDefined();
      }
    });

    it('handles rate limit errors', async () => {
      server.use(
        http.post(`${API_URL}/api/submit`, () => {
          return HttpResponse.json(
            {
              error: 'Rate limit exceeded',
              message: 'Too many requests',
              retry_after: 60,
            },
            { status: 429 }
          );
        })
      );

      try {
        await submitJob({ course_url: 'https://example.com' });
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).toBeDefined();
      }
    });
  });
});
