/**
 * ResultCard Component
 *
 * Compact search result card with title-first design
 */

import { useState } from 'react';

export default function ResultCard({ resource, index, onCopy, isSelected, onToggleSelect }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(resource.url);
      setCopied(true);
      if (onCopy) onCopy(resource.url, index);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  const getBadgeClass = (type) => {
    const upperType = type?.toUpperCase() || '';
    if (upperType.includes('PDF') || upperType.includes('TEXTBOOK')) return 'badge badge-pdf';
    if (upperType.includes('VIDEO') || upperType.includes('YOUTUBE')) return 'badge badge-video';
    if (upperType.includes('COURSE')) return 'badge badge-course';
    if (upperType.includes('WEBSITE') || upperType.includes('WEB')) return 'badge badge-website';
    if (upperType.includes('PRACTICE') || upperType.includes('PROBLEM')) return 'badge badge-practice';
    return 'badge badge-default';
  };

  const getHostname = (url) => {
    if (!url) return '';
    try {
      return new URL(url).hostname.replace(/^www\./, '');
    } catch {
      return url;
    }
  };

  const getSiteName = (url) => {
    const hostname = getHostname(url);
    const lower = hostname.toLowerCase();

    // Map common educational domains to friendly names
    if (lower.includes('mit.edu') || lower.includes('ocw.mit.edu')) return 'MIT';
    if (lower.includes('stanford.edu')) return 'Stanford';
    if (lower.includes('berkeley.edu') || lower.includes('ucb.edu')) return 'UC Berkeley';
    if (lower.includes('openstax.org')) return 'OpenStax';
    if (lower.includes('libretexts.org')) return 'LibreTexts';
    if (lower.includes('youtube.com') || lower.includes('youtu.be')) return 'YouTube';
    if (lower.includes('khanacademy.org')) return 'Khan Academy';
    if (lower.includes('coursera.org')) return 'Coursera';
    if (lower.includes('edx.org')) return 'edX';

    // Extract a clean site name from the hostname
    const parts = hostname.split('.');

    // For .edu sites, extract university name (skip subdomains like "ocw", "www")
    if (lower.endsWith('.edu')) {
      // Handle subdomains: "ocw.mit.edu" -> "MIT"
      if (parts.length > 2) {
        const subdomain = parts[parts.length - 3].toLowerCase();
        if (subdomain === 'ocw' || subdomain === 'www' || subdomain === 'web') {
          const universityName = parts[parts.length - 2];
          return universityName.charAt(0).toUpperCase() + universityName.slice(1);
        }
      }
      // Standard .edu domain: "mit.edu" -> "MIT"
      if (parts.length >= 2) {
        const name = parts[parts.length - 2];
        return name.charAt(0).toUpperCase() + name.slice(1);
      }
    }

    // For other domains, extract the main domain name (part before TLD)
    // e.g., "example.com" -> "Example", "some-site.org" -> "Some Site"
    if (parts.length >= 2) {
      const mainName = parts[parts.length - 2];
      // Convert to title case, handling hyphens (e.g., "some-site" -> "Some Site")
      return mainName.split('-').map(word =>
        word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
      ).join(' ');
    }

    // Fallback: use first part of hostname
    return parts[0].charAt(0).toUpperCase() + parts[0].slice(1);
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
        <span className={getBadgeClass(resource.type)}>
          {resource.type}
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
