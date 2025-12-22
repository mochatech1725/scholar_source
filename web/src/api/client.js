/**
 * API Client for ScholarSource Backend
 *
 * Handles all HTTP requests to the FastAPI backend.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Submit a new job to find educational resources
 *
 * @param {Object} inputs - Course input parameters
 * @returns {Promise<Object>} Job submission response with job_id
 */
export async function submitJob(inputs) {
  const response = await fetch(`${API_BASE_URL}/api/submit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(inputs),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail?.message || 'Failed to submit job');
  }

  return response.json();
}

/**
 * Get the current status of a job
 *
 * @param {string} jobId - UUID of the job
 * @returns {Promise<Object>} Job status response
 */
export async function getJobStatus(jobId) {
  const response = await fetch(`${API_BASE_URL}/api/status/${jobId}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail?.message || 'Failed to get job status');
  }

  return response.json();
}

/**
 * Check API health
 *
 * @returns {Promise<Object>} Health status
 */
export async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/api/health`);

  if (!response.ok) {
    throw new Error('API health check failed');
  }

  return response.json();
}
