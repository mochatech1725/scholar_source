/**
 * ResultsTable Component
 *
 * Displays discovered resources in a clean list format with copy functionality.
 */

import { useState } from 'react';
import './ResultsTable.css';

export default function ResultsTable({ resources, searchTitle, textbookInfo, onClear }) {
  const [copiedUrl, setCopiedUrl] = useState(null);
  const [copiedAll, setCopiedAll] = useState(false);

  const getTypeBadgeClass = (type) => {
    const typeUpper = type?.toUpperCase() || '';

    if (typeUpper.includes('PDF') || typeUpper.includes('TEXTBOOK')) {
      return 'badge-pdf';
    } else if (typeUpper.includes('VIDEO') || typeUpper.includes('YOUTUBE')) {
      return 'badge-video';
    } else if (typeUpper.includes('COURSE')) {
      return 'badge-course';
    } else if (typeUpper.includes('WEBSITE') || typeUpper.includes('WEB')) {
      return 'badge-website';
    } else {
      return 'badge-default';
    }
  };

  const copyToClipboard = async (text, identifier = null) => {
    try {
      await navigator.clipboard.writeText(text);

      if (identifier) {
        setCopiedUrl(identifier);
        setTimeout(() => setCopiedUrl(null), 2000);
      }
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  const copyAllUrls = async () => {
    const urls = resources.map(r => r.url).join('\n');
    await copyToClipboard(urls);
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 2000);
  };

  if (!resources || resources.length === 0) {
    return (
      <div className="results-card">
        <div className="empty-state">
          <div className="empty-state-icon">📭</div>
          <h3>No resources found</h3>
          <p>Try adjusting your search criteria or selecting a different search type.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="results-card">
      {/* Course and Book Information - Display first for verification */}
      {(textbookInfo?.course_name || textbookInfo?.book_title || textbookInfo?.book_author || 
        textbookInfo?.title || textbookInfo?.author) && (
        <div className="course-book-info-box">
          <h3>
            {textbookInfo?.course_name ? '📖 Course & Textbook Information' : '📚 Textbook Information'}
          </h3>
          {textbookInfo?.course_name && (
            <p className="info-item"><strong>Course:</strong> {textbookInfo.course_name}</p>
          )}
          {(textbookInfo?.book_title || textbookInfo?.title) && (
            <p className="info-item"><strong>Textbook:</strong> {textbookInfo.book_title || textbookInfo.title}</p>
          )}
          {(textbookInfo?.book_author || textbookInfo?.author) && (
            <p className="info-item"><strong>Author(s):</strong> {textbookInfo.book_author || textbookInfo.author}</p>
          )}
          {textbookInfo?.source && (
            <p className="info-item"><strong>Source:</strong> {textbookInfo.source}</p>
          )}
        </div>
      )}

      <div className="results-header">
        <div>
          <h2>Discovered Resources</h2>
          {searchTitle && <p className="search-title">{searchTitle}</p>}
        </div>
        <div className="header-actions">
          <button
            onClick={copyAllUrls}
            className="action-button primary"
            title="Copy all URLs for NotebookLM"
          >
            {copiedAll ? '✓ Copied!' : '📋 Copy All URLs'}
          </button>
          {onClear && (
            <button
              onClick={onClear}
              className="action-button secondary"
              title="Clear results"
            >
              🗑️ Clear Results
            </button>
          )}
        </div>
      </div>

      <div className="resources-list">
        {resources.map((resource, index) => (
          <div key={index} className="resource-item">
            <div className="resource-header">
              <span className={`type-badge ${getTypeBadgeClass(resource.type)}`}>
                {resource.type}
              </span>
              <h3 className="resource-title">{resource.title}</h3>
            </div>

            <div className="resource-url">
              <a
                href={resource.url}
                target="_blank"
                rel="noopener noreferrer"
                className="url-link"
              >
                {resource.url}
              </a>
              <button
                onClick={() => copyToClipboard(resource.url, index)}
                className="copy-button"
                title="Copy URL"
              >
                {copiedUrl === index ? '✓' : '📋'}
              </button>
            </div>

            <div className="resource-meta">
              <span className="resource-source">
                <strong>Source:</strong> {resource.source}
              </span>
            </div>

            {resource.description && (
              <p className="resource-description">{resource.description}</p>
            )}
          </div>
        ))}
      </div>

      <div className="results-footer">
        <div className="tip-box">
          💡 <strong>Tip:</strong> Click "Copy All URLs" above, then paste them into{' '}
          <a
            href="https://notebooklm.google.com"
            target="_blank"
            rel="noopener noreferrer"
          >
            Google NotebookLM
          </a>{' '}
          to create flashcards, study guides, and quizzes from these resources.
        </div>
      </div>
    </div>
  );
}
