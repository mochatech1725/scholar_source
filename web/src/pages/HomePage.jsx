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
        <div className="header-logo">
          <span className="logo-icon">📚</span>
          <div className="logo-text-container">
            <h1 className="logo-title">Scholar Source</h1>
          </div>
        </div>

        {/* Welcome Message - Centered */}
        <div className="welcome-section">
          <h3>Ready to find your perfect study resources?</h3>
          <p className="welcome-description">
            <strong>Enter your course info below</strong> to discover relevant videos, lecture notes, practice problems, and study guides matched to your course or textbook!
          </p>
          <div className="welcome-features">
            <div className="feature-tag feature-tag-math">
              <span className="feature-icon">🧮</span>
              <span>Practice problems</span>
            </div>
            <div className="feature-tag feature-tag-test">
              <span className="feature-icon">📋</span>
              <span>Practice Tests</span>
            </div>
            <div className="feature-tag feature-tag-video">
              <span className="feature-icon">🎥</span>
              <span>Lecture Videos</span>
            </div>
          </div>
        </div>
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
            <div className="results-placeholder-card">
              <div className="results-placeholder-content">
                <div className="results-placeholder-icon">📊</div>
                <h3>Your results will appear here</h3>
                <p>Fill out the form and click "Find Resources" to see curated study materials matched to your course.</p>
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
