/**
 * LoadingStatus Component
 *
 * Polls job status and shows progress updates while crew is running.
 */

import { useEffect, useState } from 'react';
import { getJobStatus } from '../api/client';
import './LoadingStatus.css';

export default function LoadingStatus({ jobId, onComplete, onError }) {
  const [status, setStatus] = useState('pending');
  const [statusMessage, setStatusMessage] = useState('Initializing...');

  useEffect(() => {
    let intervalId;

    const pollStatus = async () => {
      try {
        const data = await getJobStatus(jobId);

        setStatus(data.status);
        setStatusMessage(data.status_message || getDefaultMessage(data.status));

        // Check if job is complete or failed
        if (data.status === 'completed') {
          clearInterval(intervalId);
          onComplete(data.results, data.raw_output, data.search_title);
        } else if (data.status === 'failed') {
          clearInterval(intervalId);
          onError(data.error || 'Job failed with unknown error');
        }
      } catch (error) {
        clearInterval(intervalId);
        onError(error.message);
      }
    };

    // Start polling immediately
    pollStatus();

    // Then poll every 2 seconds
    intervalId = setInterval(pollStatus, 2000);

    // Cleanup on unmount
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [jobId, onComplete, onError]);

  const getDefaultMessage = (status) => {
    switch (status) {
      case 'pending':
        return 'Job queued, waiting to start...';
      case 'running':
        return 'Analyzing course and discovering resources...';
      default:
        return 'Processing...';
    }
  };

  return (
    <div className="loading-status-card">
      <div className="loading-spinner-container">
        <div className="loading-spinner"></div>
      </div>

      <div className="loading-content">
        <h3>Finding Resources</h3>
        <p className="status-message">{statusMessage}</p>

        <div className="progress-steps">
          <div className={`progress-step ${status !== 'pending' ? 'active' : ''}`}>
            <div className="step-icon">1</div>
            <div className="step-label">Analyzing Course</div>
          </div>
          <div className={`progress-step ${status === 'completed' ? 'active' : ''}`}>
            <div className="step-icon">2</div>
            <div className="step-label">Discovering Resources</div>
          </div>
          <div className={`progress-step ${status === 'completed' ? 'active' : ''}`}>
            <div className="step-icon">3</div>
            <div className="step-label">Validating Quality</div>
          </div>
        </div>

        <p className="loading-hint">This may take 1-5 minutes...</p>
      </div>
    </div>
  );
}
