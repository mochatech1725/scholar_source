/**
 * HomePage Component (v3 - Vertical Layout)
 *
 * Vertical layout with compact toolbar-style search panel above full-width results.
 * - Search panel: compact card with all filters
 * - Optional sections: collapsible accordions
 * - Results: full-width cards below
 * - Mobile-first, responsive design
 */

import { useCallback, useState } from 'react';
import { submitJob } from '../api/client';
import Hero from '../components/Hero';
import InlineSearchStatus from '../components/InlineSearchStatus';
import ResultsTable from '../components/ResultsTable';
import StatusMessage from '../components/StatusMessage';
import UserMenu from '../components/UserMenu/UserMenu';
import { TextLabel, HelperText, OptionalBadge, TextInput, Button } from '../components/ui';

export default function HomePage() {
  const [jobId, setJobId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [searchTitle, setSearchTitle] = useState(null);
  const [textbookInfo, setTextbookInfo] = useState(null);
  const [error, setError] = useState(null);
  const [statusMessage, setStatusMessage] = useState(null);

  // Form state
  const [searchParamType, setSearchParamType] = useState('');
  const [formData, setFormData] = useState({
    course_url: '',
    book_url: '',
    book_title: '',
    book_author: '',
    isbn: '',
    topics_list: '',
    desired_resource_types: [],
    excluded_sites: '',
    targeted_sites: '',
    bypass_cache: false
  });
  const [validationError, setValidationError] = useState('');
  const [isAdvancedOptionsExpanded, setIsAdvancedOptionsExpanded] = useState(false);
  const [isResourceTypesExpanded, setIsResourceTypesExpanded] = useState(false);
  const [isFocusTopicsExpanded, setIsFocusTopicsExpanded] = useState(false);
  const [isExcludeSitesExpanded, setIsExcludeSitesExpanded] = useState(false);
  const [isTargetSitesExpanded, setIsTargetSitesExpanded] = useState(false);


  // Form handlers
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
    if (validationError) setValidationError('');
  };

  const handleResourceTypeChange = useCallback((resourceType) => {
    setFormData(prev => {
      const currentTypes = prev.desired_resource_types || [];
      const newTypes = currentTypes.includes(resourceType)
        ? currentTypes.filter(type => type !== resourceType)
        : [...currentTypes, resourceType];
      return { ...prev, desired_resource_types: newTypes };
    });
    // Clear validation error (idempotent - safe to clear even if already empty)
    setValidationError('');
  }, []);

  const handleSearchParamChange = (e) => {
    const value = e.target.value;
    setSearchParamType(value);
    if (validationError) setValidationError('');
    setFormData({
      course_url: '',
      book_url: '',
      book_title: '',
      book_author: '',
      isbn: '',
      topics_list: formData.topics_list,
      desired_resource_types: formData.desired_resource_types,
      excluded_sites: formData.excluded_sites,
      targeted_sites: formData.targeted_sites,
      bypass_cache: formData.bypass_cache
    });
  };

  const isFormValid = () => {
    if (!searchParamType) return false;
    switch (searchParamType) {
      case 'course_url': return formData.course_url.trim() !== '';
      case 'book_url': return formData.book_url.trim() !== '';
      case 'book_title_author': return formData.book_title.trim() !== '' && formData.book_author.trim() !== '';
      case 'isbn': return formData.isbn.trim() !== '';
      default: return false;
    }
  };

  const handleReset = useCallback(() => {
    setSearchParamType('');
    setFormData({
      course_url: '',
      book_url: '',
      book_title: '',
      book_author: '',
      isbn: '',
      topics_list: '',
      desired_resource_types: [],
      excluded_sites: '',
      targeted_sites: '',
      bypass_cache: false
    });
    setValidationError('');
    setIsAdvancedOptionsExpanded(false);
    setIsResourceTypesExpanded(false);
    setIsFocusTopicsExpanded(false);
    setIsExcludeSitesExpanded(false);
    setIsTargetSitesExpanded(false);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validate
    if (!searchParamType) {
      setValidationError('Please select a search parameter type');
      return;
    }
    switch (searchParamType) {
      case 'course_url':
        if (formData.course_url.trim() === '') {
          setValidationError('Please provide a Course URL');
          return;
        }
        break;
      case 'book_url':
        if (formData.book_url.trim() === '') {
          setValidationError('Please provide a Book URL');
          return;
        }
        break;
      case 'book_title_author':
        if (formData.book_title.trim() === '' || formData.book_author.trim() === '') {
          setValidationError('Please provide both Book Title and Author');
          return;
        }
        break;
      case 'isbn':
        if (formData.isbn.trim() === '') {
          setValidationError('Please provide a Book ISBN');
          return;
        }
        break;
      default:
        setValidationError('Please select a valid search parameter type');
        return;
    }

    try {
      setError(null);
      setStatusMessage(null);
      setResults(null);
      setSearchTitle(null);
      setTextbookInfo(null);
      setJobId(null);
      setIsLoading(true);

      console.log('[HomePage] Submitting job...');
      const response = await submitJob(formData);
      console.log('[HomePage] Job submitted, response:', response);
      console.log('[HomePage] Setting jobId to:', response.job_id);
      setJobId(response.job_id);
      console.log('[HomePage] jobId state updated');
    } catch (err) {
      console.error('[HomePage] Job submission failed:', err);
      setError(err.message);
      setIsLoading(false);
    }
  };

  const handleComplete = useCallback((resources, rawOutput, title, textbook) => {
    setResults(resources);
    setSearchTitle(title);
    setTextbookInfo(textbook);
    setIsLoading(false);
  }, []);

  const handleError = useCallback((errorMessage) => {
    // Check if this is a cancellation
    if (errorMessage === 'Job was cancelled') {
      setStatusMessage({
        type: 'cancelled',
        title: 'Search Cancelled',
        message: 'You cancelled the search. No results were generated.'
      });
    } else {
      setError(errorMessage);
    }
    setIsLoading(false);
  }, []);

  const handleClearResults = useCallback(() => {
    setResults(null);
    setSearchTitle(null);
    setTextbookInfo(null);
    setJobId(null);
  }, []);

  const handleDismissStatus = useCallback(() => {
    setStatusMessage(null);
    setJobId(null);
  }, []);

  const handleDismissError = useCallback(() => {
    setError(null);
    setJobId(null);
  }, []);


  return (
    <div className={`home-page-container ${isLoading ? 'cursor-wait' : ''}`}>
      {/* Header */}
      <header className="home-page-header">
        <div className="home-page-header-inner">
          <div className="home-page-header-content">
            <span className="home-page-header-icon" aria-hidden="true">📚</span>
            <h1 className="home-page-header-title">
              Student Study Resource Finder
            </h1>
          </div>
          <UserMenu />
        </div>
      </header>

      {/* Main Content */}
      <main className="home-page-main">
        {/* Hero Section */}
        <Hero />

        {/* Search Toolbar Panel */}
        <section id="search-parameters" className="search-panel">
          <div className="search-panel-header">
            <h2 className="search-panel-title">
              Course Information
            </h2>

            {/* Action Buttons */}
            <div className="search-panel-actions">
              <Button
                type="submit"
                form="search-form"
                variant="primary"
                disabled={isLoading || !isFormValid()}
              >
                {isLoading ? '🔍 Finding...' : '🔍 Find Resources'}
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={handleReset}
                disabled={isLoading}
              >
                Clear Search Fields
              </Button>
              </div>
            </div>

          <form id="search-form" onSubmit={handleSubmit}>
              {/* Primary Controls Row */}
              <div className="search-grid">
                {/* Search Type Dropdown */}
                <div>
                  <TextLabel htmlFor="search_param_type" required>
                    Search Type
                  </TextLabel>
                  <div className="mt-1">
                    <TextInput
                      as="select"
                      id="search_param_type"
                      name="search_param_type"
                      value={searchParamType}
                      onChange={handleSearchParamChange}
                      disabled={isLoading}
                      aria-describedby="search-type-helper"
                    >
                      <option value="">Select type...</option>
                      <option value="course_url">Course URL</option>
                      <option value="book_url">Book URL</option>
                      <option value="book_title_author">Book Title + Author</option>
                      <option value="isbn">Book ISBN</option>
                    </TextInput>
                  </div>
                  <p id="search-type-helper" className="helper-text-inline">
                    {!searchParamType && "Selecting a search type will show required fields below."}
                    {searchParamType === 'course_url' && "Enter the URL of the course page you want to search."}
                    {searchParamType === 'book_url' && "Enter the URL of the book page you want to search."}
                    {searchParamType === 'book_title_author' && (
                      <>Enter both the <span className="font-medium">book title</span> and at least one <span className="font-medium">author</span>.</>
                    )}
                    {searchParamType === 'isbn' && "Enter the ISBN of the book you want to search."}
                  </p>
                </div>

                {/* Dynamic Input Field */}
                {searchParamType === 'course_url' && (
                  <div>
                    <TextLabel htmlFor="course_url" required>
                      Course URL
                    </TextLabel>
                    <div className="mt-1">
                      <TextInput
                        type="url"
                        id="course_url"
                        name="course_url"
                        value={formData.course_url}
                        onChange={handleChange}
                        placeholder="https://ocw.mit.edu/courses/..."
                        disabled={isLoading}
                        required
                      />
                    </div>
                  </div>
                )}

                {searchParamType === 'book_url' && (
                  <div>
                    <TextLabel htmlFor="book_url" required>
                      Book URL
                    </TextLabel>
                    <div className="mt-1">
                      <TextInput
                        type="url"
                        id="book_url"
                        name="book_url"
                        value={formData.book_url}
                        onChange={handleChange}
                        placeholder="https://..."
                        disabled={isLoading}
                        required
                      />
                    </div>
                  </div>
                )}

                {searchParamType === 'book_title_author' && (
                  <div className="search-grid-two-col">
                    <div>
                      <TextLabel htmlFor="book_title" required>
                        Book Title
                      </TextLabel>
                      <div className="mt-1">
                        <TextInput
                          type="text"
                          id="book_title"
                          name="book_title"
                          value={formData.book_title}
                          onChange={handleChange}
                          placeholder="e.g., Intro to Algorithms"
                          disabled={isLoading}
                          required
                        />
                      </div>
                    </div>
                    <div>
                      <TextLabel htmlFor="book_author" required>
                        Author(s)
                      </TextLabel>
                      <div className="mt-1">
                        <TextInput
                          type="text"
                          id="book_author"
                          name="book_author"
                          value={formData.book_author}
                          onChange={handleChange}
                          placeholder="e.g., Cormen"
                          disabled={isLoading}
                          required
                        />
                      </div>
                    </div>
                  </div>
                )}

                {searchParamType === 'isbn' && (
                  <div>
                    <TextLabel htmlFor="isbn" required>
                      ISBN
                    </TextLabel>
                    <div className="mt-1">
                      <TextInput
                        type="text"
                        id="isbn"
                        name="isbn"
                        value={formData.isbn}
                        onChange={handleChange}
                        placeholder="978-0262046305"
                        disabled={isLoading}
                        required
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Force Refresh Toggle - Mobile */}
              <div className="mb-1.5 lg:hidden">
                <label htmlFor="bypass_cache_mobile" className="checkbox-label">
                  <input
                    type="checkbox"
                    id="bypass_cache_mobile"
                    name="bypass_cache"
                    checked={formData.bypass_cache}
                    onChange={handleChange}
                    disabled={isLoading}
                    className="checkbox-input"
                  />
                  <span className="checkbox-label-text">
                    Bypass cache
                  </span>
                  <span className="checkbox-label-helper">
                    Don't use cached results from previous searches. (Will make searches a bit slower.)
                  </span>
                </label>
              </div>

              {/* Force Refresh Toggle - Desktop */}
              <div className="hidden lg:block mb-1.5">
                <label htmlFor="bypass_cache" className="checkbox-label">
                  <input
                    type="checkbox"
                    id="bypass_cache"
                    name="bypass_cache"
                    checked={formData.bypass_cache}
                    onChange={handleChange}
                    disabled={isLoading}
                    className="checkbox-input"
                  />
                  <span className="checkbox-label-text">
                    Bypass cache
                  </span>
                  <span className="checkbox-label-helper">
                    Don't use cached results from previous searches. (Will make searches a bit slower.)
                  </span>
                </label>
              </div>

              {/* Advanced Options - Collapsible Panel */}
              <div className="advanced-options-panel mb-2">
                <button
                  type="button"
                  onClick={() => setIsAdvancedOptionsExpanded(!isAdvancedOptionsExpanded)}
                  className="advanced-options-header"
                >
                  <div className="advanced-options-header-content">
                    <span className="advanced-options-title">⚙️ Advanced Options</span>
                    <OptionalBadge />
                  </div>
                  <svg className={`accordion-icon ${isAdvancedOptionsExpanded ? 'accordion-icon-expanded' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                
                {isAdvancedOptionsExpanded && (
                  <div className="advanced-options-body">
                    {/* Row 1: Resource Types + Focus Topics */}
                    <div className="search-grid-two-col mb-2">
                      {/* Resource Types Accordion */}
                      <div className="accordion accordion-blue">
                        <button
                          type="button"
                          onClick={() => setIsResourceTypesExpanded(!isResourceTypesExpanded)}
                          className="accordion-header accordion-header-blue"
                        >
                          <div className="accordion-header-content">
                            <span className="accordion-title">Resource Types</span>
                          </div>
                          <svg className={`accordion-icon ${isResourceTypesExpanded ? 'accordion-icon-expanded' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                        {isResourceTypesExpanded && (
                          <div className="accordion-body accordion-body-blue accordion-grid">
                            {['textbooks', 'practice_problem_sets', 'practice_exams_tests', 'lecture_videos'].map(type => (
                              <label key={type} className="accordion-checkbox-label">
                                <input
                                  type="checkbox"
                                  checked={formData.desired_resource_types?.includes(type) || false}
                                  onChange={() => handleResourceTypeChange(type)}
                                  disabled={isLoading}
                                  className="checkbox-input-with-margin"
                                />
                                <span className="accordion-checkbox-text">{type.replace(/_/g, ' ')}</span>
                              </label>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Focus Topics Accordion */}
                      <div className="accordion accordion-blue">
                        <button
                          type="button"
                          onClick={() => setIsFocusTopicsExpanded(!isFocusTopicsExpanded)}
                          className="accordion-header accordion-header-blue"
                        >
                          <div className="accordion-header-content">
                            <span className="accordion-title">Focus Topics</span>
                          </div>
                          <svg className={`accordion-icon ${isFocusTopicsExpanded ? 'accordion-icon-expanded' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                        {isFocusTopicsExpanded && (
                          <div className="accordion-body accordion-body-blue">
                            <TextLabel htmlFor="topics_list">
                              Topics List
                            </TextLabel>
                            <div className="mt-1">
                              <TextInput
                                as="textarea"
                                id="topics_list"
                                name="topics_list"
                                value={formData.topics_list}
                                onChange={handleChange}
                                placeholder="e.g., Midterm review, Chapter 4, Dynamic programming"
                                rows="2"
                                disabled={isLoading}
                              />
                            </div>
                            <HelperText>
                              💡 Add 3–6 topics for better matches
                            </HelperText>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Row 2: Target Sites + Exclude Sites */}
                    <div className="search-grid-two-col">
                      {/* Target Sites Accordion */}
                      <div className="accordion accordion-blue">
                        <button
                          type="button"
                          onClick={() => setIsTargetSitesExpanded(!isTargetSitesExpanded)}
                          className="accordion-header accordion-header-blue"
                        >
                          <div className="accordion-header-content">
                            <span className="accordion-title">Target Sites</span>
                          </div>
                          <svg className={`accordion-icon ${isTargetSitesExpanded ? 'accordion-icon-expanded' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                        {isTargetSitesExpanded && (
                          <div className="accordion-body accordion-body-blue">
                            <TextLabel htmlFor="targeted_sites">
                              Target Domains
                            </TextLabel>
                            <div className="mt-1">
                              <TextInput
                                as="textarea"
                                id="targeted_sites"
                                name="targeted_sites"
                                value={formData.targeted_sites}
                                onChange={handleChange}
                                placeholder="e.g., stanford.edu, berkeley.edu"
                                rows="2"
                                disabled={isLoading}
                              />
                            </div>
                            <HelperText>
                              💡 Prioritize results from specific sites
                            </HelperText>
                          </div>
                        )}
                      </div>
                      
                      {/* Exclude Sites Accordion */}
                      <div className="accordion accordion-blue">
                        <button
                          type="button"
                          onClick={() => setIsExcludeSitesExpanded(!isExcludeSitesExpanded)}
                          className="accordion-header accordion-header-blue"
                        >
                          <div className="accordion-header-content">
                            <span className="accordion-title">Exclude Sites</span>
                          </div>
                          <svg className={`accordion-icon ${isExcludeSitesExpanded ? 'accordion-icon-expanded' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                        {isExcludeSitesExpanded && (
                          <div className="accordion-body accordion-body-blue">
                            <TextLabel htmlFor="excluded_sites">
                              Exclude Domains
                            </TextLabel>
                            <div className="mt-1">
                              <TextInput
                                as="textarea"
                                id="excluded_sites"
                                name="excluded_sites"
                                value={formData.excluded_sites}
                                onChange={handleChange}
                                placeholder="e.g., khanacademy.org, coursera.org"
                                rows="2"
                                disabled={isLoading}
                              />
                            </div>
                            <HelperText>
                              💡 Exclude specific sites from results
                            </HelperText>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>


            {/* Validation Error */}
            {validationError && (
              <div className="validation-error">
                {validationError}
              </div>
            )}
          </form>

          {/* Inline Loading Status - shown while search is running */}
          {isLoading && (
            <>
              {jobId ? (
                <InlineSearchStatus
                  jobId={jobId}
                  onComplete={handleComplete}
                  onError={handleError}
                />
              ) : (
                <div className="mt-4 status-container info">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 spinner" aria-hidden="true" />
                    <div className="min-w-0 flex-1">
                      <h4 className="m-0 text-sm sm:text-base font-semibold text-slate-900">
                        Submitting job...
                      </h4>
                      <p className="mt-1 mb-0 text-sm text-slate-700">
                        Creating your search request
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </section>

        {/* Results Section - Only show after search is initiated */}
        {(jobId !== null || results !== null || error !== null || statusMessage !== null) && (
          <section>
            {/* Status Message (Cancellation, etc.) */}
            {statusMessage && (
              <StatusMessage
                type={statusMessage.type}
                title={statusMessage.title}
                message={statusMessage.message}
                actions={
                  <Button variant="secondary" onClick={handleDismissStatus}>
                    Dismiss
                  </Button>
                }
              />
            )}

            {/* Error State */}
            {error && (
              <StatusMessage
                type="error"
                title="Something went wrong"
                message={error}
                actions={
                  <Button variant="primary" onClick={handleDismissError}>
                    Dismiss
                  </Button>
                }
              />
            )}

            {/* Results State */}
            {results && !isLoading && (
              <ResultsTable
                resources={results}
                searchTitle={searchTitle}
                textbookInfo={textbookInfo}
                onClear={handleClearResults}
              />
            )}
          </section>
        )}
      </main>
    </div>
  );
}
