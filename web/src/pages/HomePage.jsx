/**
 * HomePage Component (v5 - Split Layout, hero/empty-state left, form right)
 *
 * Layout: narrow left column (hero + steps + empty state) | wider right column (search form + results).
 * - Left: hero banner + how-it-works steps (collapses to empty state while searching/showing results)
 * - Right: search form always visible at top; results appear below the form
 * - Fixed bottom bar: Copy + NotebookLM, appears when ≥1 resource selected
 */

import { useCallback, useState } from 'react';
import { submitJob, uploadPdf } from '../api/client';
import InlineSearchStatus from '../components/InlineSearchStatus';
import ResultsTable from '../components/ResultsTable';
import StatusMessage from '../components/StatusMessage';
import UserMenu from '../components/UserMenu/UserMenu';
import { TextLabel, HelperText, OptionalBadge, TextInput, Button } from '../components/ui';

const SEARCH_TYPES = [
  { value: 'course_url', label: 'Course URL',  icon: '🎓' },
  { value: 'book_url',   label: 'Book URL',    icon: '📖' },
  { value: 'isbn',       label: 'ISBN',         icon: '🔢' },
  { value: 'book_pdf',   label: 'PDF Upload',  icon: '📄' },
];

const RESOURCE_TYPES = [
  { value: 'lecture_videos',        label: 'Lecture Videos',    icon: '🎬' },
  { value: 'practice_problem_sets', label: 'Practice Problems', icon: '✏️' },
  { value: 'practice_exams_tests',  label: 'Practice Exams',    icon: '📝' },
];

export default function HomePage() {
  const [jobId, setJobId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [sectionGroups, setSectionGroups] = useState(null);
  const [searchTitle, setSearchTitle] = useState(null);
  const [textbookInfo, setTextbookInfo] = useState(null);
  const [error, setError] = useState(null);
  const [statusMessage, setStatusMessage] = useState(null);

  // Form state
  const [searchParamType, setSearchParamType] = useState('course_url');
  const [formData, setFormData] = useState({
    course_url: '',
    book_url: '',
    isbn: '',
    topics_list: '',
    desired_resource_types: [],
    excluded_sites: '',
    targeted_sites: '',
    chapter: '',
    sections: '',
    preferred_creators: '',
    book_pdf_path: ''
  });
  const [pdfFile, setPdfFile] = useState(null);
  const [validationError, setValidationError] = useState('');
  const [isChapterSearchExpanded, setIsChapterSearchExpanded] = useState(false);
  const [isFocusTopicsExpanded, setIsFocusTopicsExpanded] = useState(false);
  const [isExcludeSitesExpanded, setIsExcludeSitesExpanded] = useState(false);
  const [isTargetSitesExpanded, setIsTargetSitesExpanded] = useState(false);

  // Bottom action bar state (controlled by ResultsTable via callback)
  const [selectionState, setSelectionState] = useState({ selectedCount: 0, totalCount: 0, onCopy: null, onCopyAndOpen: null });

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
        ? currentTypes.filter(t => t !== resourceType)
        : [...currentTypes, resourceType];
      return { ...prev, desired_resource_types: newTypes };
    });
    setValidationError('');
  }, []);

  const handleSearchParamChange = (value) => {
    setSearchParamType(value);
    if (validationError) setValidationError('');
    setPdfFile(null);
    setFormData(prev => ({
      course_url: '',
      book_url: '',
      isbn: '',
      topics_list: prev.topics_list,
      desired_resource_types: prev.desired_resource_types,
      excluded_sites: prev.excluded_sites,
      targeted_sites: prev.targeted_sites,
      chapter: prev.chapter,
      sections: prev.sections,
      preferred_creators: prev.preferred_creators,
      book_pdf_path: ''
    }));
  };

  const isFormValid = () => {
    if (!searchParamType) return false;
    switch (searchParamType) {
      case 'course_url': return formData.course_url.trim() !== '';
      case 'book_url':   return formData.book_url.trim() !== '';
      case 'isbn':       return formData.isbn.trim() !== '';
      case 'book_pdf':   return pdfFile !== null;
      default:           return false;
    }
  };

  const handleReset = useCallback(() => {
    setSearchParamType('');
    setFormData({
      course_url: '',
      book_url: '',
      isbn: '',
      topics_list: '',
      desired_resource_types: [],
      excluded_sites: '',
      targeted_sites: '',
      chapter: '',
      sections: '',
      preferred_creators: '',
      book_pdf_path: ''
    });
    setPdfFile(null);
    setSectionGroups(null);
    setValidationError('');
    setIsChapterSearchExpanded(false);
    setIsFocusTopicsExpanded(false);
    setIsExcludeSitesExpanded(false);
    setIsTargetSitesExpanded(false);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!searchParamType) {
      setValidationError('Please select a search type');
      return;
    }
    switch (searchParamType) {
      case 'course_url':
        if (!formData.course_url.trim()) { setValidationError('Please provide a Course URL'); return; }
        break;
      case 'book_url':
        if (!formData.book_url.trim()) { setValidationError('Please provide a Book URL'); return; }
        break;
      case 'isbn':
        if (!formData.isbn.trim()) { setValidationError('Please provide a Book ISBN'); return; }
        break;
      case 'book_pdf':
        if (!pdfFile) { setValidationError('Please select a PDF file to upload'); return; }
        break;
      default:
        setValidationError('Please select a valid search type');
        return;
    }

    try {
      setError(null);
      setStatusMessage(null);
      setResults(null);
      setSectionGroups(null);
      setSearchTitle(null);
      setTextbookInfo(null);
      setJobId(null);
      setIsLoading(true);

      let payload = { ...formData };

      if (searchParamType === 'book_pdf' && pdfFile) {
        const { pdf_path } = await uploadPdf(pdfFile);
        payload = { ...payload, book_pdf_path: pdf_path };
      }

      const response = await submitJob(payload);
      setJobId(response.job_id);
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
    }
  };

  const handleComplete = useCallback((resources, rawOutput, title, textbook, sections) => {
    setResults(resources);
    setSectionGroups(sections || null);
    setSearchTitle(title);
    setTextbookInfo(textbook);
    setIsLoading(false);
  }, []);

  const handleError = useCallback((errorMessage) => {
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
    setSectionGroups(null);
    setSearchTitle(null);
    setTextbookInfo(null);
    setJobId(null);
    setSelectionState({ selectedCount: 0, totalCount: 0, onCopy: null, onCopyAndOpen: null });
  }, []);

  const handleDismissStatus = useCallback(() => {
    setStatusMessage(null);
    setJobId(null);
  }, []);

  const handleDismissError = useCallback(() => {
    setError(null);
    setJobId(null);
  }, []);

  const isBookType = searchParamType === 'book_url' || searchParamType === 'isbn' || searchParamType === 'book_pdf';
  const hasRightContent = jobId !== null || results !== null || error !== null || statusMessage !== null;

  return (
    <div className={`split-page-container ${isLoading ? 'cursor-wait' : ''}`}>

      {/* ── Header ── */}
      <header className="home-page-header">
        <div className="split-header-inner">
          <div className="home-page-header-content">
            <span className="home-page-header-icon" aria-hidden="true">📚</span>
            <div>
              <h1 className="home-page-header-title">Student Study Resource Finder</h1>
              <p className="split-header-tagline">
                AI-powered resource discovery for your courses and textbooks
                <span className="ml-2 text-xs text-slate-400 font-normal">v{import.meta.env.VITE_APP_VERSION}</span>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <a
              href="https://notebooklm.google.com"
              target="_blank"
              rel="noopener noreferrer"
              className="hero-cta-btn-inline"
            >
              <span>✨</span>
              Open NotebookLM
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
            <UserMenu />
          </div>
        </div>
      </header>

      {/* ── Split Body ── */}
      <div className="split-body">

        {/* ── LEFT: Hero / Steps / Empty state ── */}
        <aside className="split-left">
          <div className="split-left-inner">

            {/* How it works — always shown when no results */}
            {!hasRightContent && !isLoading && (
              <div className="hero-steps-panel">
                <p className="hero-steps-eyebrow">How it works</p>
                <div className="hero-steps-list">
                  {[
                    { num: 1, icon: '🎓', title: 'Enter your course details', desc: 'Provide a course URL, textbook link, ISBN, or upload a PDF syllabus.' },
                    { num: 2, icon: '🔍', title: 'AI discovers resources', desc: 'Our AI agents find textbooks, lecture videos, practice problems, and more from trusted sources.' },
                    { num: 3, icon: '📋', title: 'Select & copy links', desc: 'Choose the resources you want, then copy their URLs with one click.' },
                    { num: 4, icon: '✨', title: 'Generate study tools', desc: 'Paste into NotebookLM to create summaries, flashcards, and practice quizzes.' },
                  ].map(step => (
                    <div key={step.num} className="hero-step-row">
                      <div className="hero-step-row-icon">{step.icon}</div>
                      <div className="hero-step-row-body">
                        <div className="hero-step-row-num">{step.num}</div>
                        <div>
                          <p className="hero-step-row-title">{step.title}</p>
                          <p className="hero-step-row-desc">{step.desc}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* While loading — compact status hint */}
            {isLoading && (
              <div className="hero-steps-panel">
                <p className="hero-steps-eyebrow">Search in progress</p>
                <p className="text-sm text-slate-600 mt-2">
                  Your search is running on the right. This usually takes 1–2 minutes while the AI agents analyse your course and discover resources.
                </p>
              </div>
            )}

            {/* After results — compact tip */}
            {hasRightContent && !isLoading && (
              <div className="hero-steps-panel">
                <p className="hero-steps-eyebrow">Next steps</p>
                <div className="hero-steps-list">
                  {[
                    { icon: '☑️', text: 'Select the resources you want using the checkboxes on each card.' },
                    { icon: '📋', text: 'Use the bar at the bottom of the screen to copy selected URLs.' },
                    { icon: '✨', text: 'Paste into NotebookLM to generate flashcards, study guides, and quizzes.' },
                  ].map((tip, i) => (
                    <div key={i} className="hero-tip-row">
                      <span className="hero-tip-icon">{tip.icon}</span>
                      <p className="hero-tip-text">{tip.text}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

          </div>
        </aside>

        {/* ── RIGHT: Form + Results ── */}
        <main className="split-right">

          {/* Search form */}
          <section className="search-panel">
            <div className="split-left-heading mb-3">
              <h2 className="split-section-title">Search Criteria</h2>
              <div className="flex gap-2">
                <Button
                  type="submit"
                  form="search-form"
                  variant="primary"
                  disabled={isLoading || !isFormValid()}
                >
                  {isLoading ? '🔍 Finding…' : '🔍 Find Resources'}
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleReset}
                  disabled={isLoading}
                >
                  Clear
                </Button>
              </div>
            </div>

            <form id="search-form" onSubmit={handleSubmit} className="split-form">

              {/* ── Search Type — icon tab bar ── */}
              <div className="search-type-tab-group">
                <div className="flex items-baseline gap-2 mb-2">
                  <TextLabel required>Search By</TextLabel>
                  <span className="text-xs text-slate-500">Select what you have — a URL, ISBN, or PDF to upload.</span>
                </div>
                <div className="search-type-tab-bar" role="radiogroup" aria-label="Search type">
                  {SEARCH_TYPES.map(({ value, label, icon }) => {
                    const isActive = searchParamType === value;
                    return (
                      <button
                        key={value}
                        type="button"
                        role="radio"
                        aria-checked={isActive}
                        onClick={() => handleSearchParamChange(value)}
                        disabled={isLoading}
                        className={`search-type-tab ${isActive ? 'search-type-tab-active' : ''}`}
                      >
                        <span className="search-type-tab-icon" aria-hidden="true">{icon}</span>
                        <span className="search-type-tab-label">{label}</span>
                      </button>
                    );
                  })}
                </div>

                {/* Input box — appears inside the tab group frame */}
                {searchParamType && (
                  <div className="search-type-tab-input-box">
                    {searchParamType === 'course_url' && (
                      <TextInput type="url" id="course_url" name="course_url" value={formData.course_url}
                        onChange={handleChange} placeholder="https://canvas.university.edu/courses/…"
                        disabled={isLoading} required />
                    )}
                    {searchParamType === 'book_url' && (
                      <TextInput type="url" id="book_url" name="book_url" value={formData.book_url}
                        onChange={handleChange} placeholder="https://openstax.org/books/…"
                        disabled={isLoading} required />
                    )}
                    {searchParamType === 'isbn' && (
                      <TextInput type="text" id="isbn" name="isbn" value={formData.isbn}
                        onChange={handleChange} placeholder="978-0262046305"
                        disabled={isLoading} required />
                    )}
                    {searchParamType === 'book_pdf' && (
                      <>
                        <input
                          type="file"
                          id="book_pdf_file"
                          accept=".pdf"
                          disabled={isLoading}
                          onChange={(e) => {
                            const file = e.target.files?.[0] || null;
                            if (file) {
                              if (file.type !== 'application/pdf') {
                                e.target.value = '';
                                setPdfFile(null);
                                alert('Only PDF files are accepted.');
                                return;
                              }
                              if (file.size > 50 * 1024 * 1024) {
                                e.target.value = '';
                                setPdfFile(null);
                                alert('File exceeds the 50 MB limit.');
                                return;
                              }
                            }
                            setPdfFile(file);
                          }}
                          className="block w-full text-sm text-slate-700 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                        />
                        <p className="mt-1 text-xs text-slate-500">Max 50 MB. PDF will be uploaded securely.</p>
                      </>
                    )}
                  </div>
                )}
              </div>

              {/* ── Target Resources (always open) ── */}
              <div className="target-resources-panel">
                <h3 className="target-resources-title">Target Resources</h3>

                {/* Resource type toggle chips */}
                <div className="mb-3">
                  <div className="flex items-baseline gap-2 mb-2">
                    <TextLabel>Resource Types</TextLabel>
                    <span className="text-xs text-slate-600 font-medium">Select specific types, or leave all unselected to find a mix.</span>
                  </div>
                  <div className="resource-type-chips">
                    {RESOURCE_TYPES.map(({ value, label, icon }) => {
                      const isActive = formData.desired_resource_types?.includes(value);
                      return (
                        <button
                          key={value}
                          type="button"
                          onClick={() => handleResourceTypeChange(value)}
                          disabled={isLoading}
                          aria-pressed={isActive}
                          className={`resource-type-chip ${isActive ? 'resource-type-chip-active' : ''}`}
                        >
                          <span className="resource-type-chip-icon">{icon}</span>
                          {label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Focus Topics */}
                <div className="accordion accordion-blue mb-2">
                  <button type="button" onClick={() => setIsFocusTopicsExpanded(!isFocusTopicsExpanded)}
                    className="accordion-header accordion-header-blue">
                    <div className="accordion-header-content">
                      <span className="accordion-title">Focus Topics</span>
                      <OptionalBadge />
                    </div>
                    <svg className={`accordion-icon ${isFocusTopicsExpanded ? 'accordion-icon-expanded' : ''}`}
                      fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  {isFocusTopicsExpanded && (
                    <div className="accordion-body accordion-body-blue">
                      <div className="mt-1">
                        <TextInput as="textarea" id="topics_list" name="topics_list"
                          value={formData.topics_list} onChange={handleChange}
                          placeholder="e.g., Midterm review, Chapter 4, Dynamic programming"
                          rows="2" disabled={isLoading} />
                      </div>
                      <HelperText>💡 Add 3–6 topics for better matches</HelperText>
                    </div>
                  )}
                </div>

                {/* Target Sites + Exclude Sites */}
                <div className="search-grid-two-col">
                  <div className="accordion accordion-blue">
                    <button type="button" onClick={() => setIsTargetSitesExpanded(!isTargetSitesExpanded)}
                      className="accordion-header accordion-header-blue">
                      <div className="accordion-header-content">
                        <span className="accordion-title">Target Sites</span>
                        <OptionalBadge />
                      </div>
                      <svg className={`accordion-icon ${isTargetSitesExpanded ? 'accordion-icon-expanded' : ''}`}
                        fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    {isTargetSitesExpanded && (
                      <div className="accordion-body accordion-body-blue">
                        <div className="mt-1">
                          <TextInput as="textarea" id="targeted_sites" name="targeted_sites"
                            value={formData.targeted_sites} onChange={handleChange}
                            placeholder="e.g., stanford.edu, berkeley.edu" rows="2" disabled={isLoading} />
                        </div>
                        <HelperText>Prioritize results from specific sites</HelperText>
                      </div>
                    )}
                  </div>

                  <div className="accordion accordion-blue">
                    <button type="button" onClick={() => setIsExcludeSitesExpanded(!isExcludeSitesExpanded)}
                      className="accordion-header accordion-header-blue">
                      <div className="accordion-header-content">
                        <span className="accordion-title">Exclude Sites</span>
                        <OptionalBadge />
                      </div>
                      <svg className={`accordion-icon ${isExcludeSitesExpanded ? 'accordion-icon-expanded' : ''}`}
                        fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    {isExcludeSitesExpanded && (
                      <div className="accordion-body accordion-body-blue">
                        <div className="mt-1">
                          <TextInput as="textarea" id="excluded_sites" name="excluded_sites"
                            value={formData.excluded_sites} onChange={handleChange}
                            placeholder="e.g., khanacademy.org, coursera.org" rows="2" disabled={isLoading} />
                        </div>
                        <HelperText>Exclude specific sites from results</HelperText>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* ── Chapter Search — collapsible, book types only, after Target Resources ── */}
              {isBookType && (
                <div className="advanced-options-panel">
                  <button type="button" onClick={() => setIsChapterSearchExpanded(!isChapterSearchExpanded)}
                    className="advanced-options-header">
                    <div className="advanced-options-header-content">
                      <span className="advanced-options-title">📖 Chapter Search</span>
                      <OptionalBadge />
                    </div>
                    <svg className={`accordion-icon ${isChapterSearchExpanded ? 'accordion-icon-expanded' : ''}`}
                      fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  {isChapterSearchExpanded && (
                    <div className="advanced-options-body">
                      <div className="search-grid-two-col mb-2">
                        <div>
                          <TextLabel htmlFor="chapter">Chapter</TextLabel>
                          <div className="mt-1">
                            <TextInput type="text" id="chapter" name="chapter" value={formData.chapter}
                              onChange={handleChange} placeholder="e.g., Chapter 16 or Vector Calculus"
                              disabled={isLoading} />
                          </div>
                          <HelperText>Find 3+ resources per section within this chapter.</HelperText>
                        </div>
                        <div>
                          <TextLabel htmlFor="sections">Specific Sections</TextLabel>
                          <div className="mt-1">
                            <TextInput type="text" id="sections" name="sections" value={formData.sections}
                              onChange={handleChange} placeholder="e.g., 16.1, 16.4" disabled={isLoading} />
                          </div>
                          <HelperText>Comma-separated sections (optional).</HelperText>
                        </div>
                      </div>
                      <div>
                        <TextLabel htmlFor="preferred_creators">Preferred Creators</TextLabel>
                        <div className="mt-1">
                          <TextInput type="text" id="preferred_creators" name="preferred_creators"
                            value={formData.preferred_creators} onChange={handleChange}
                            placeholder="e.g., Professor Leonard, PatrickJMT, 3Blue1Brown"
                            disabled={isLoading} />
                        </div>
                        <HelperText>Comma-separated YouTube educators to prioritize.</HelperText>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Validation Error */}
              {validationError && (
                <div className="validation-error">{validationError}</div>
              )}
            </form>

            {/* Loading status inline below form */}
            {isLoading && (
              <div className="mt-4">
                {jobId ? (
                  <InlineSearchStatus
                    jobId={jobId}
                    onComplete={handleComplete}
                    onError={handleError}
                  />
                ) : (
                  <div className="status-container info">
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5 spinner" aria-hidden="true" />
                      <div className="min-w-0 flex-1">
                        <h4 className="m-0 text-sm font-semibold text-slate-900">Submitting job…</h4>
                        <p className="mt-1 mb-0 text-sm text-slate-700">Creating your search request</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </section>

          {/* Results + messages below the form */}
          {statusMessage && (
            <StatusMessage
              type={statusMessage.type}
              title={statusMessage.title}
              message={statusMessage.message}
              actions={<Button variant="secondary" onClick={handleDismissStatus}>Dismiss</Button>}
            />
          )}

          {error && (
            <StatusMessage
              type="error"
              title="Something went wrong"
              message={error}
              actions={<Button variant="primary" onClick={handleDismissError}>Dismiss</Button>}
            />
          )}

          {results && !isLoading && (
            <ResultsTable
              resources={results}
              sectionGroups={sectionGroups}
              searchTitle={searchTitle}
              textbookInfo={textbookInfo}
              onClear={handleClearResults}
              onSelectionChange={setSelectionState}
            />
          )}
        </main>
      </div>

      {/* ── Fixed Bottom Action Bar ── */}
      {selectionState.selectedCount > 0 && (
        <div className="bottom-action-bar">
          <span className="bottom-action-badge">
            {selectionState.selectedCount} of {selectionState.totalCount} selected
          </span>
          <button onClick={selectionState.onCopyAndOpen} className="results-table-notebooklm-btn">
            Copy Selected + NotebookLM
          </button>
          <button onClick={selectionState.onCopy} className="results-table-copy-btn">
            📋 Copy Selected
          </button>
          <button
            onClick={() => setSelectionState(prev => ({ ...prev, selectedCount: 0 }))}
            className="bottom-action-dismiss"
            aria-label="Dismiss action bar"
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
}
