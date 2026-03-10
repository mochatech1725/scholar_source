/**
 * Tests for API client
 */

import { describe, it, expect, beforeAll, afterEach, afterAll } from 'vitest';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { submitJob, getJobStatus, cancelJob, checkHealth } from './client';
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

      await expect(submitJob({})).rejects.toThrow('Invalid input');
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

      expect(requestBody).toEqual(inputs);
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

      await expect(getJobStatus('nonexistent')).rejects.toThrow('Job not found');
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

      await expect(cancelJob('nonexistent')).rejects.toThrow('Job not found');
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
        expect(error.message).toContain('Validation error');
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
        expect(error.message).toContain('Simple error message');
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
        expect(error.message).toContain('Rate limit');
      }
    });
  });
});
