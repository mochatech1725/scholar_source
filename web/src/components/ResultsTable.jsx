/**
 * ResultsTable Component
 *
 * Displays discovered resources in a clean list format with copy functionality.
 */

import { useState } from 'react';
import './ResultsTable.css';

export default function ResultsTable({ resources, searchTitle }) {
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
          <p>No resources found. Try adjusting your search criteria.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="results-card">
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
