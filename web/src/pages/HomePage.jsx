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
import SkeletonResourceList from '../components/SkeletonResourceList';
import './HomePage.css';

export default function HomePage() {
  const [jobId, setJobId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [searchTitle, setSearchTitle] = useState(null);
  const [textbookInfo, setTextbookInfo] = useState(null);
  const [error, setError] = useState(null);

  const handleJobSubmitted = async (formData) => {
    try {
      // Clear previous results and errors
      setError(null);
      setResults(null);
      setSearchTitle(null);
      setTextbookInfo(null);
      setJobId(null);
      setIsLoading(true);

      // Submit job to backend
      const response = await submitJob(formData);
      setJobId(response.job_id);
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
    }
  };

  const handleComplete = (resources, rawOutput, title, textbook) => {
    setResults(resources);
    setSearchTitle(title);
    setTextbookInfo(textbook);
    setIsLoading(false);
  };

  const handleError = (errorMessage) => {
    setError(errorMessage);
    setIsLoading(false);
  };

  const handleClearResults = () => {
    setResults(null);
    setSearchTitle(null);
    setTextbookInfo(null);
    setJobId(null);
  };

  return (
    <div className="home-page">
      {/* Header */}
      <header className="page-header">
        <h1>
          <span className="header-emoji">📚</span>
          <span className="header-text">Scholar Source</span>
        </h1>
        <p>Find study resources matched to your class.</p>
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
                <div className="placeholder-icon">📦</div>
                <h3>Your study kit will show up here</h3>
                <p>Enter your course info and click 'Find Resources' to generate videos, notes, practice problems, and more.</p>
              </div>
            </div>
          )}

          {isLoading && jobId && (
            <div>
              <LoadingStatus
                jobId={jobId}
                onComplete={handleComplete}
                onError={handleError}
              />
              <div style={{ marginTop: '24px' }}>
                <SkeletonResourceList />
              </div>
            </div>
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

          {results && !isLoading && (
            <ResultsTable
              resources={results}
              searchTitle={searchTitle}
              textbookInfo={textbookInfo}
              onClear={handleClearResults}
            />
          )}
        </div>
      </div>
    </div>
  );
}
