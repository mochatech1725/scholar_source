/**
 * HomePage Component
 *
 * Main page with form and results display.
 */

import { useState } from 'react';
import { submitJob } from '../api/client';
import CourseForm from '../components/CourseForm';
import LoadingStatus from '../components/LoadingStatus';
import ResultsTable from '../components/ResultsTable';
import './HomePage.css';

export default function HomePage() {
  const [jobId, setJobId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [searchTitle, setSearchTitle] = useState(null);
  const [error, setError] = useState(null);

  const handleJobSubmitted = async (formData) => {
    try {
      setError(null);
      setResults(null);
      setIsLoading(true);

      // Submit job to backend
      const response = await submitJob(formData);
      setJobId(response.job_id);
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
    }
  };

  const handleComplete = (resources, rawOutput, title) => {
    setResults(resources);
    setSearchTitle(title);
    setIsLoading(false);
  };

  const handleError = (errorMessage) => {
    setError(errorMessage);
    setIsLoading(false);
  };

  return (
    <div className="home-page">
      {/* Header */}
      <header className="page-header">
        <h1>📚 ScholarSource</h1>
        <p>Discover educational resources aligned with your course textbook</p>
      </header>

      {/* Main Content - Two Column Layout */}
      <div className="content-container">
        {/* Left Column - Form */}
        <div className="left-column">
          <CourseForm
            onJobSubmitted={handleJobSubmitted}
            isLoading={isLoading}
          />
        </div>

        {/* Right Column - Results/Loading/Error */}
        <div className="right-column">
          {!isLoading && !results && !error && (
            <div className="placeholder-card">
              <div className="placeholder-content">
                <h3>Your resources will appear here</h3>
                <p>Fill in the form and click "Find Resources" to discover study materials aligned with your course.</p>
              </div>
            </div>
          )}

          {isLoading && jobId && (
            <LoadingStatus
              jobId={jobId}
              onComplete={handleComplete}
              onError={handleError}
            />
          )}

          {error && (
            <div className="error-card">
              <h3>Error</h3>
              <p>{error}</p>
              <button
                onClick={() => {
                  setError(null);
                  setJobId(null);
                }}
                className="retry-button"
              >
                Try Again
              </button>
            </div>
          )}

          {results && (
            <ResultsTable
              resources={results}
              searchTitle={searchTitle}
            />
          )}
        </div>
      </div>
    </div>
  );
}
