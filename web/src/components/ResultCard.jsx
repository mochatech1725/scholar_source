/**
 * ResultCard Component
 *
 * Compact search result card with title-first design
 */

import { getHostname, getSiteName, getTypeMeta } from '../lib/resourceUtils';
import useCopyToClipboard from '../hooks/useCopyToClipboard';

export default function ResultCard({ resource, index, onCopy, isSelected, onToggleSelect }) {
  const [copied, copy] = useCopyToClipboard();

  const handleCopy = async () => {
    await copy(resource.url);
    if (onCopy) onCopy(resource.url, index);
  };



  const getDisplayTitle = () => {
    if (resource.title && resource.title !== resource.url) return resource.title;
    return `${getHostname(resource.url)} resource`;
  };

  const handleCardClick = (e) => {
    // Do NOT toggle when clicking interactive elements inside the card.
    // (Visit link, Copy URL button, etc.)
    const interactive = e.target.closest('a,button,input,textarea,select,label');
    if (interactive) return;
    onToggleSelect?.();
  };

  const handleCardKeyDown = (e) => {
    // Keyboard accessibility: Space/Enter toggles selection when the card has focus.
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onToggleSelect?.();
    }
  };

  return (
    <article
      role="button"
      tabIndex={0}
      aria-pressed={isSelected}
      onClick={handleCardClick}
      onKeyDown={handleCardKeyDown}
      className={`result-card ${isSelected ? 'selected' : ''}`}
      title={isSelected ? 'Selected for copy to NotebookLM' : 'Click to select for copy to NotebookLM'}
    >
      {/* Left side checkbox */}
      <div className="result-card-checkbox">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(e) => {
            e.stopPropagation();
            onToggleSelect?.();
          }}
          className="result-card-checkbox-input"
          aria-label={isSelected ? 'Deselect resource' : 'Select resource'}
        />
      </div>

      {/* Header row */}
      <div className="result-card-header">
        <span className={`badge badge-${getTypeMeta(resource.type).typeKey}`}>
          {getTypeMeta(resource.type).label}
        </span>

        <span className="result-card-site-name">{getSiteName(resource.url)}</span>
      </div>

      {/* Title */}
      <h3 className="result-card-title-wrapper">
        {/^https?:\/\//i.test(resource.url ?? '') ? (
          <a
            href={resource.url}
            target="_blank"
            rel="noopener noreferrer"
            className="result-card-title-link"
          >
            {getDisplayTitle()}
          </a>
        ) : (
          <span className="result-card-title-link">{getDisplayTitle()}</span>
        )}
      </h3>

      {/* Description */}
      {resource.description && (
        <p className="result-card-description">{resource.description}</p>
      )}

      {/* Actions row */}
      <div className="result-card-actions">
        <a
          href={resource.url}
          target="_blank"
          rel="noopener noreferrer"
          className="result-card-visit-link"
        >
          Visit Resource ↗
        </a>

        <button
          onClick={handleCopy}
          className="result-card-copy-btn"
          title="Copy URL"
          type="button"
        >
          {copied ? '✓ Copied' : 'Copy URL'}
        </button>
      </div>
    </article>
  );
}
