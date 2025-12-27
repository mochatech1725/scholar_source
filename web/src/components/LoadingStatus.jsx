/**
 * LoadingStatus Component
 *
 * Polls job status and shows progress updates while crew is running.
 */

import { useEffect, useState } from 'react';
import { getJobStatus, cancelJob } from '../api/client';

export default function LoadingStatus({ jobId, onComplete, onError }) {
  const [status, setStatus] = useState('pending');
  const [statusMessage, setStatusMessage] = useState('Initializing...');
  const [isCancelling, setIsCancelling] = useState(false);
  const [textbookInfo, setTextbookInfo] = useState(null);

  useEffect(() => {
    let intervalId;

    const pollStatus = async () => {
      try {
        const data = await getJobStatus(jobId);

        setStatus(data.status);
        setStatusMessage(data.status_message || getDefaultMessage(data.status));
        
        // Update textbook info if available
        if (data.book_title || data.book_author || data.metadata?.textbook_info) {
          setTextbookInfo({
            book_title: data.book_title || data.metadata?.textbook_info?.title,
            book_author: data.book_author || data.metadata?.textbook_info?.author,
            course_name: data.course_name
          });
        }
        
        // Debug: log status to help troubleshoot cancel button visibility
        console.log('Job status:', data.status, 'Should show cancel:', data.status === 'pending' || data.status === 'running');

        // Check if job is complete or failed
        if (data.status === 'completed') {
          clearInterval(intervalId);

          const textbookInfo = data.metadata?.textbook_info || null;
          // Pass course and book info for display
          const courseInfo = {
            course_name: data.course_name,
            book_title: data.book_title,
            book_author: data.book_author,
            ...textbookInfo
          };
          onComplete(data.results, data.raw_output, data.search_title, courseInfo);
        } else if (data.status === 'failed' || data.status === 'cancelled') {
          clearInterval(intervalId);
          const errorMsg = data.status === 'cancelled' 
            ? 'Job was cancelled' 
            : (data.error || 'Job failed with unknown error');
          onError(errorMsg);
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

  const handleCancel = async () => {
    if (!confirm('Are you sure you want to cancel this job? The search will be stopped.')) {
      return;
    }

    setIsCancelling(true);
    try {
      await cancelJob(jobId);
      // The status will update on the next poll, which will trigger the error handler
    } catch (error) {
      onError(error.message || 'Failed to cancel job');
    } finally {
      setIsCancelling(false);
    }
  };

  return (
    <div className="bg-transparent rounded-xl p-0 text-center">
      <div className="mb-8 flex justify-center">
        <div className="w-14 h-14 border-4 border-gray-100 border-t-primary rounded-full animate-spin motion-reduce:animate-none"></div>
      </div>

      <div>
        <div className="flex justify-between items-center mb-6 gap-4 w-full relative">
          <h3 className="m-0 text-2xl font-bold text-green-800 text-center tracking-tight flex-1">Finding Resources</h3>
          {(status === 'pending' || status === 'running') && (
            <button
              onClick={handleCancel}
              disabled={isCancelling}
              className="px-5 py-2.5 bg-gradient-to-br from-red-500 to-red-600 text-white border-2 border-white/30 rounded-lg text-sm font-bold cursor-pointer transition-all whitespace-nowrap shadow-md flex-shrink-0 min-w-[100px] hover:not(:disabled):bg-gradient-to-br hover:not(:disabled):from-red-600 hover:not(:disabled):to-red-700 hover:not(:disabled):border-white/50 hover:not(:disabled):scale-105 hover:not(:disabled):shadow-lg active:not(:disabled):scale-100 active:not(:disabled):shadow-md disabled:opacity-70 disabled:cursor-not-allowed disabled:bg-gradient-to-br disabled:from-gray-400 disabled:to-gray-500 motion-reduce:hover:not(:disabled):scale-100"
              title="Cancel this job"
              type="button"
            >
              {isCancelling ? 'Cancelling...' : '✕ Cancel'}
            </button>
          )}
        </div>
        {textbookInfo && (textbookInfo.book_title || textbookInfo.book_author) && (
          <div className="m-0 mb-4 p-4 bg-white/30 rounded-lg border-l-[3px] border-green-800">
            <p className="m-0 mb-1 text-xs text-green-700 font-semibold uppercase tracking-wide">📚 Searching for resources matching:</p>
            <p className="m-0 text-base text-green-800 font-bold">
              {textbookInfo.book_title}
              {textbookInfo.book_author && ` by ${textbookInfo.book_author}`}
            </p>
          </div>
        )}
        <p className="m-0 mb-8 text-base text-green-700 font-medium">{statusMessage}</p>

        <div className="flex justify-center gap-8 mb-6 flex-wrap">
          <div className={`flex flex-col items-center gap-2 transition-opacity ${status !== 'pending' ? 'opacity-100' : 'opacity-40'}`}>
            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-base transition-all border-2 ${
              status !== 'pending'
                ? 'bg-gradient-to-r from-primary to-primary-dark text-white border-primary shadow-md scale-110 motion-reduce:scale-100'
                : 'bg-gray-100 text-gray-500 border-gray-200'
            }`}>1</div>
            <div className="text-xs text-green-700 font-semibold text-center">Analyzing Course</div>
          </div>
          <div className={`flex flex-col items-center gap-2 transition-opacity ${status === 'completed' ? 'opacity-100' : 'opacity-40'}`}>
            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-base transition-all border-2 ${
              status === 'completed'
                ? 'bg-gradient-to-r from-primary to-primary-dark text-white border-primary shadow-md scale-110 motion-reduce:scale-100'
                : 'bg-gray-100 text-gray-500 border-gray-200'
            }`}>2</div>
            <div className="text-xs text-green-700 font-semibold text-center">Discovering Resources</div>
          </div>
          <div className={`flex flex-col items-center gap-2 transition-opacity ${status === 'completed' ? 'opacity-100' : 'opacity-40'}`}>
            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-base transition-all border-2 ${
              status === 'completed'
                ? 'bg-gradient-to-r from-primary to-primary-dark text-white border-primary shadow-md scale-110 motion-reduce:scale-100'
                : 'bg-gray-100 text-gray-500 border-gray-200'
            }`}>3</div>
            <div className="text-xs text-green-700 font-semibold text-center">Validating Quality</div>
          </div>
        </div>

        <p className="m-0 text-sm text-green-700 italic">This may take 1-5 minutes...</p>
      </div>
    </div>
  );
}
