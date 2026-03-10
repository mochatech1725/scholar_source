/**
 * MSW (Mock Service Worker) handlers for API mocking
 *
 * These handlers intercept HTTP requests during tests and return mock responses.
 */

import { http, HttpResponse } from 'msw';
import { APP_VERSION } from '../../config/appVersion';

const API_URL = 'http://localhost:8000';

export const handlers = [
  // Health check endpoint
  http.get(`${API_URL}/api/health`, () => {
    return HttpResponse.json({
      status: 'healthy',
      version: APP_VERSION,
      database: 'connected',
    });
  }),

  // Submit job endpoint
  http.post(`${API_URL}/api/submit`, async ({ request }) => {
    const body = await request.json();

    // Validate inputs
    if (!body.course_url && !body.book_url && !body.isbn) {
      return HttpResponse.json(
        {
          detail: {
            error: 'Invalid inputs',
            message: 'You must provide at least one search parameter',
          },
        },
        { status: 400 }
      );
    }

    // Return mock job creation response
    return HttpResponse.json({
      job_id: 'mock-job-id-12345',
      status: 'pending',
      message: 'Job created successfully. Use job_id to poll for status.',
    });
  }),

  // Get job status endpoint
  http.get(`${API_URL}/api/status/:jobId`, ({ params }) => {
    const { jobId } = params;

    // Mock completed job
    if (jobId === 'mock-completed-job') {
      return HttpResponse.json({
        job_id: jobId,
        status: 'completed',
        status_message: 'Job completed successfully',
        results: [
          {
            type: 'Textbook',
            title: 'Introduction to Algorithms',
            source: 'MIT Press',
            url: 'https://mitpress.mit.edu/books/introduction-algorithms',
            description: 'Comprehensive algorithms textbook',
          },
          {
            type: 'Lecture Notes',
            title: 'MIT 6.006 Lecture Notes',
            source: 'MIT OpenCourseWare',
            url: 'https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-fall-2011/',
            description: 'Complete lecture notes from MIT course',
          },
        ],
        metadata: {
          resource_count: 2,
          textbook_info: {
            title: 'Introduction to Algorithms',
            author: 'Cormen, Leiserson, Rivest, Stein',
            edition: '4th',
          },
        },
        created_at: '2024-01-01T00:00:00Z',
        completed_at: '2024-01-01T00:05:00Z',
      });
    }

    // Mock pending/running job
    if (jobId === 'mock-job-id-12345') {
      return HttpResponse.json({
        job_id: jobId,
        status: 'running',
        status_message: 'Analyzing course content...',
        results: [],
        metadata: {},
        created_at: '2024-01-01T00:00:00Z',
        completed_at: null,
      });
    }

    // Mock failed job
    if (jobId === 'mock-failed-job') {
      return HttpResponse.json({
        job_id: jobId,
        status: 'failed',
        status_message: 'Job failed',
        error: 'CrewAI execution error',
        results: [],
        metadata: {},
        created_at: '2024-01-01T00:00:00Z',
        completed_at: null,
      });
    }

    // Job not found
    return HttpResponse.json(
      {
        detail: {
          error: 'Job not found',
          message: `Job with ID ${jobId} does not exist`,
        },
      },
      { status: 404 }
    );
  }),

  // Cancel job endpoint
  http.post(`${API_URL}/api/cancel/:jobId`, ({ params }) => {
    const { jobId } = params;

    // Job not found
    if (jobId === 'nonexistent-job') {
      return HttpResponse.json(
        {
          detail: {
            error: 'Job not found',
            message: `Job with ID ${jobId} does not exist`,
          },
        },
        { status: 404 }
      );
    }

    // Success
    return HttpResponse.json({
      message: 'Job cancelled successfully',
      job_id: jobId,
    });
  }),
];

// Error handlers for network errors
export const errorHandlers = [
  http.post(`${API_URL}/api/submit`, () => {
    return HttpResponse.error();
  }),
];

// Rate limit handlers
export const rateLimitHandlers = [
  http.post(`${API_URL}/api/submit`, () => {
    return HttpResponse.json(
      {
        error: 'Rate limit exceeded',
        message: 'Too many requests. Please try again in 60 seconds.',
        retry_after: 60,
        limit: '2 per minute',
      },
      { status: 429, headers: { 'Retry-After': '60' } }
    );
  }),
];
