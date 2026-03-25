/**
 * InlineSearchStatus Component
 *
 * Compact inline status strip for search progress.
 * Displays inside the Search Parameters card for better visual integration.
 */

import { useEffect, useState, useRef, useCallback } from 'react';
import { getJobStatus, cancelJob } from '../api/client';
import ConfirmDialog from './ConfirmDialog';

// Timeout in minutes (default 8 minutes)
const SEARCH_TIMEOUT_MINUTES = parseInt(import.meta.env.VITE_SEARCH_TIMEOUT_MINUTES || '8', 10);
const SEARCH_TIMEOUT_MS = SEARCH_TIMEOUT_MINUTES * 60 * 1000;

// Format elapsed time as "Xm Ys" or "Xs"
function formatElapsedTime(ms) {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}

export default function InlineSearchStatus({ jobId, onComplete, onError }) {
  const [status, setStatus] = useState('pending');
  const [statusMessage, setStatusMessage] = useState('Initializing...');
  const [isCancelling, setIsCancelling] = useState(false);
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);

  // Track if job is still active (not completed/failed/cancelled)
  const isActiveRef = useRef(true);
  const timeoutIdRef = useRef(null);
  const startTimeRef = useRef(Date.now());
  const elapsedIntervalRef = useRef(null);
  // Timeout flag kept in a ref so the polling effect doesn't need it as a
  // dependency — flipping it must not tear down and restart the interval.
  const isTimedOutRef = useRef(false);

  // Auto-cancel function for timeout
  const handleTimeoutCancel = useCallback(async () => {
    if (!isActiveRef.current) return; // Job already finished
    
    console.log(`Search timeout after ${SEARCH_TIMEOUT_MINUTES} minutes, cancelling job ${jobId}`);
    isTimedOutRef.current = true;
    setIsCancelling(true);
    
    try {
      await cancelJob(jobId);
      // The polling will pick up the cancelled status and call onError
    } catch (error) {
      console.error('Failed to cancel timed-out job:', error);
      onError(`Search timed out after ${SEARCH_TIMEOUT_MINUTES} minutes and failed to cancel`);
    }
  }, [jobId, onError]);

  const getDefaultMessage = (status) => {
    switch (status) {
      case 'pending':
        return 'Job created, waiting to be queued...';
      case 'queued':
        return 'Job queued, waiting to start...';
      case 'running':
        return 'Analyzing course and discovering resources...';
      default:
        return 'Processing...';
    }
  };

  useEffect(() => {
    let intervalId;
    isActiveRef.current = true;
    startTimeRef.current = Date.now();

    // Update elapsed time every second
    elapsedIntervalRef.current = setInterval(() => {
      setElapsedTime(Date.now() - startTimeRef.current);
    }, 1000);

    // Set up timeout to auto-cancel
    timeoutIdRef.current = setTimeout(() => {
      handleTimeoutCancel();
    }, SEARCH_TIMEOUT_MS);

    const pollStatus = async () => {
      try {
        const data = await getJobStatus(jobId);

        setStatus(data.status);
        setStatusMessage(data.status_message || getDefaultMessage(data.status));

        // Check if job is complete or failed
        if (data.status === 'completed') {
          isActiveRef.current = false;
          clearInterval(intervalId);
          clearTimeout(timeoutIdRef.current);
          clearInterval(elapsedIntervalRef.current);

          const textbookInfo = data.metadata?.textbook_info || null;
          const courseInfo = {
            course_name: data.course_name,
            book_title: data.book_title,
            book_author: data.book_author,
            ...textbookInfo
          };
          onComplete(data.results, data.raw_output, data.search_title, courseInfo, data.metadata?.section_groups || null);
        } else if (data.status === 'failed' || data.status === 'cancelled') {
          isActiveRef.current = false;
          clearInterval(intervalId);
          clearTimeout(timeoutIdRef.current);
          clearInterval(elapsedIntervalRef.current);
          
          // Check if this was a timeout cancellation
          const errorMsg = isTimedOutRef.current
            ? `Search timed out after ${SEARCH_TIMEOUT_MINUTES} minutes`
            : data.status === 'cancelled'
              ? 'Job was cancelled'
              : (data.error || 'Job failed with unknown error');
          onError(errorMsg);
        }
      } catch (error) {
        isActiveRef.current = false;
        clearInterval(intervalId);
        clearTimeout(timeoutIdRef.current);
        clearInterval(elapsedIntervalRef.current);
        onError(error.message);
      }
    };

    // Start polling immediately
    pollStatus();

    // Then poll every 2 seconds
    intervalId = setInterval(pollStatus, 2000);

    // Cleanup on unmount
    return () => {
      isActiveRef.current = false;
      if (intervalId) {
        clearInterval(intervalId);
      }
      if (timeoutIdRef.current) {
        clearTimeout(timeoutIdRef.current);
      }
      if (elapsedIntervalRef.current) {
        clearInterval(elapsedIntervalRef.current);
      }
    };
  }, [jobId, onComplete, onError, handleTimeoutCancel]);

  const handleCancelClick = () => {
    setShowCancelDialog(true);
  };

  const handleCancelConfirm = async () => {
    setShowCancelDialog(false);
    setIsCancelling(true);
    try {
      await cancelJob(jobId);
    } catch (error) {
      onError(error.message || 'Failed to cancel job');
    } finally {
      setIsCancelling(false);
    }
  };

  const handleCancelDialogClose = () => {
    setShowCancelDialog(false);
  };

  // Check if status message contains error/warning indicators
  const isErrorMessage = statusMessage && (statusMessage.includes('⚠️') || statusMessage.includes('error') || statusMessage.includes('workers are available'));
  const messageClass = isErrorMessage ? 'text-red-600 font-medium' : 'text-slate-700';

  return (
    <div className="mt-4 status-container info">
      {/* Header row: spinner + title + cancel */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0 flex-1">
          <div className="mt-0.5 spinner" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="m-0 text-sm sm:text-base font-semibold text-slate-900">
                Finding resources
              </h4>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                ⏱ {formatElapsedTime(elapsedTime)}
              </span>
            </div>
            <p className={`mt-1 mb-0 text-sm ${messageClass}`} aria-live="polite">
              {statusMessage}
            </p>
          </div>
        </div>

        {(status === 'pending' || status === 'queued' || status === 'running') && (
          <button
            onClick={handleCancelClick}
            disabled={isCancelling}
            type="button"
            className="btn-cancel"
            title="Cancel this search"
          >
            {isCancelling ? 'Cancelling…' : 'Cancel'}
          </button>
        )}
      </div>

      {/* Footer */}
      <p className="mt-3 mb-0 text-xs text-slate-600">
        Our AI agents are analyzing your course, searching for resources, and validating quality. Usually takes <span className="font-medium text-slate-700">1–5 minutes</span>.
        {SEARCH_TIMEOUT_MINUTES && (
          <span className="text-slate-500"> (timeout: {SEARCH_TIMEOUT_MINUTES} min)</span>
        )}
      </p>

      {/* Cancel Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showCancelDialog}
        title="Cancel Search"
        message="Are you sure you want to cancel this search? The job will be stopped and no results will be returned."
        confirmText="Yes, Cancel Search"
        cancelText="Continue Searching"
        isDanger={true}
        onConfirm={handleCancelConfirm}
        onCancel={handleCancelDialogClose}
      />
    </div>
  );
}
