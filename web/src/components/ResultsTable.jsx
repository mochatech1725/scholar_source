/**
 * ResultsTable Component
 *
 * Renders discovered resources in a scrollable table with filter pills,
 * a selection header bar, and per-row Visit links.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getSiteName } from '../lib/resourceUtils';

// ── helpers shared between table rows ──────────────────────────────────────

const TYPE_META = {
  VIDEO:    { label: 'Video',    cls: 'rt-badge-video' },
  YOUTUBE:  { label: 'Video',    cls: 'rt-badge-video' },
  PDF:      { label: 'PDF',      cls: 'rt-badge-pdf' },
  TEXTBOOK: { label: 'Textbook', cls: 'rt-badge-pdf' },
  COURSE:   { label: 'Course',   cls: 'rt-badge-course' },
  PRACTICE: { label: 'Practice', cls: 'rt-badge-practice' },
  PROBLEM:  { label: 'Practice', cls: 'rt-badge-practice' },
  NOTES:    { label: 'Notes',    cls: 'rt-badge-notes' },
  WEBSITE:  { label: 'Web',      cls: 'rt-badge-website' },
  WEB:      { label: 'Web',      cls: 'rt-badge-website' },
};

function getTypeMeta(type = '') {
  const up = type.toUpperCase();
  for (const [key, meta] of Object.entries(TYPE_META)) {
    if (up.includes(key)) return meta;
  }
  return { label: type || '—', cls: 'rt-badge-default' };
}


// ── Row ────────────────────────────────────────────────────────────────────

function ResourceRow({ resource, isSelected, onToggle }) {
  const [copied, setCopied] = useState(false);

  const handleCopyUrl = async (e) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(resource.url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error(err);
    }
  };

  const { label, cls } = getTypeMeta(resource.type);
  const displayTitle = resource.title && resource.title !== resource.url
    ? resource.title
    : getSiteName(resource.url);

  const handleRowClick = (e) => {
    if (e.target.closest('a,button,input')) return;
    onToggle?.();
  };

  return (
    <tr
      className={`rt-row ${isSelected ? 'rt-row-selected' : ''}`}
      onClick={handleRowClick}
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); onToggle?.(); } }}
      aria-selected={isSelected}
    >
      {/* Checkbox */}
      <td className="rt-cell-check">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(e) => { e.stopPropagation(); onToggle?.(); }}
          className="rt-checkbox"
          aria-label={isSelected ? 'Deselect' : 'Select'}
        />
      </td>

      {/* Type badge */}
      <td className="rt-cell-type">
        <span className={`rt-badge ${cls}`}>{label}</span>
      </td>

      {/* Title + description */}
      <td className="rt-cell-title">
        <a href={resource.url} target="_blank" rel="noopener noreferrer" className="rt-title-link">
          {displayTitle}
        </a>
        {resource.description && (
          <p className="rt-description">{resource.description}</p>
        )}
      </td>

      {/* Section / chapter */}
      <td className="rt-cell-section">
        {resource.section ? (
          <span className="rt-section-label">{resource.section}</span>
        ) : '—'}
      </td>

      {/* Copy URL */}
      <td className="rt-cell-source">
        <button type="button" onClick={handleCopyUrl} className="rt-copy-url-btn">
          {copied ? '✓ Copied' : 'Copy URL'}
        </button>
      </td>

      {/* Visit */}
      <td className="rt-cell-visit">
        <a href={resource.url} target="_blank" rel="noopener noreferrer" className="rt-visit-link">
          Visit ↗
        </a>
      </td>
    </tr>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

export default function ResultsTable({ resources, searchTitle, textbookInfo, sectionGroups, onClear, onSelectionChange }) {
  const allResources = useMemo(() => {
    if (sectionGroups && sectionGroups.length > 0) {
      return sectionGroups.flatMap((g) => g.resources);
    }
    return resources || [];
  }, [resources, sectionGroups]);

  const totalCount = allResources.length;
  const urlList    = useMemo(() => allResources.map((r) => r.url).filter(Boolean), [allResources]);

  const resourcesRef = useRef(resources);
  const [selectedUrls, setSelectedUrls] = useState(() => new Set(urlList));

  useEffect(() => {
    if (resourcesRef.current !== resources) {
      resourcesRef.current = resources;
      setSelectedUrls(new Set(urlList));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resources]);

  const selectedCount = selectedUrls.size;

  // ── filter pills ────────────────────────────────────────────────────────
  const typeFilters = useMemo(() => {
    const seen = new Set();
    const filters = [];
    allResources.forEach((r) => {
      const { label } = getTypeMeta(r.type);
      if (!seen.has(label)) { seen.add(label); filters.push(label); }
    });
    return filters;
  }, [allResources]);

  const sectionFilters = useMemo(() => {
    const seen = new Set();
    allResources.forEach((r) => { if (r.section) seen.add(r.section); });
    return [...seen];
  }, [allResources]);

  const [activeFilter, setActiveFilter] = useState('All');

  const filteredResources = useMemo(() => {
    if (activeFilter === 'All') return allResources;
    // section match
    if (sectionFilters.includes(activeFilter)) {
      return allResources.filter((r) => r.section === activeFilter);
    }
    // type match
    return allResources.filter((r) => getTypeMeta(r.type).label === activeFilter);
  }, [allResources, activeFilter, sectionFilters]);

  // ── copy / clipboard ────────────────────────────────────────────────────
  const getSelectedUrlsInOrder = useCallback(
    () => urlList.filter((u) => selectedUrls.has(u)),
    [urlList, selectedUrls],
  );

  const copyToClipboard = useCallback(async (text) => {
    try { await navigator.clipboard.writeText(text); } catch (e) { console.error(e); }
  }, []);

  const copySelected = useCallback(async () => {
    await copyToClipboard(getSelectedUrlsInOrder().join('\n'));
  }, [getSelectedUrlsInOrder, copyToClipboard]);

  const copySelectedAndOpenNotebookLM = useCallback(async () => {
    await copyToClipboard(getSelectedUrlsInOrder().join('\n'));
    window.open('https://notebooklm.google.com', '_blank', 'noopener,noreferrer');
  }, [getSelectedUrlsInOrder, copyToClipboard]);

  const handleSelectAll   = useCallback(() => setSelectedUrls(new Set(urlList)), [urlList]);
  const handleClearSel    = useCallback(() => setSelectedUrls(new Set()), []);

  const toggleHandlers = useMemo(() => {
    const map = new Map();
    allResources.forEach((r) => {
      if (r.url) map.set(r.url, () => setSelectedUrls((prev) => {
        const next = new Set(prev);
        next.has(r.url) ? next.delete(r.url) : next.add(r.url);
        return next;
      }));
    });
    return map;
  }, [allResources]);

  useEffect(() => {
    onSelectionChange?.({ selectedCount, totalCount, onCopy: copySelected, onCopyAndOpen: copySelectedAndOpenNotebookLM });
  }, [selectedCount, totalCount, copySelected, copySelectedAndOpenNotebookLM, onSelectionChange]);

  // ── empty state ─────────────────────────────────────────────────────────
  if (allResources.length === 0) {
    return (
      <div className="results-table-empty">
        <div className="results-table-empty-content">
          <div className="results-table-empty-icon">📭</div>
          <h3 className="results-table-empty-title">No resources found</h3>
          <p className="results-table-empty-text">Try adjusting your search criteria or selecting a different search type.</p>
        </div>
      </div>
    );
  }

  const hasSections = sectionFilters.length > 0;

  return (
    <div className="rt-container">

      {/* ── Header bar ── */}
      <div className="rt-header">
        <div className="rt-header-left">
          <h2 className="rt-title">
            Discovered Resources
            <span className="rt-count-badge">{totalCount} RESULTS</span>
          </h2>
          {searchTitle && <p className="rt-subtitle">{searchTitle}</p>}
          {(textbookInfo?.book_title || textbookInfo?.title) && (
            <p className="rt-textbook-info">
              📚 {textbookInfo.book_title || textbookInfo.title}
              {(textbookInfo.book_author || textbookInfo.author) && (
                <span className="rt-textbook-author"> · {textbookInfo.book_author || textbookInfo.author}</span>
              )}
            </p>
          )}
        </div>

        <div className="rt-header-right">
          {selectedCount > 0 && (
            <>
              <span className="rt-selected-badge">{selectedCount} selected</span>
              <button onClick={copySelected} className="rt-copy-btn" type="button">
                📋 Copy URLs
              </button>
              <button onClick={copySelectedAndOpenNotebookLM} className="rt-notebooklm-btn" type="button">
                Open in NotebookLM ↗
              </button>
            </>
          )}
          {onClear && (
            <button onClick={onClear} className="rt-clear-btn" type="button">
              Clear
            </button>
          )}
        </div>
      </div>

      {/* ── Filter pills ── */}
      <div className="rt-filter-bar">
        {['All', ...typeFilters, ...(hasSections ? sectionFilters : [])].map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setActiveFilter(f)}
            className={`rt-filter-pill ${activeFilter === f ? 'rt-filter-pill-active' : ''}`}
          >
            {f}
          </button>
        ))}

        <div className="rt-filter-bar-right">
          <button type="button" onClick={handleSelectAll} className="rt-sel-link">All</button>
          <span className="rt-sel-sep">·</span>
          <button type="button" onClick={handleClearSel} className="rt-sel-link">None</button>
        </div>
      </div>

      {/* ── Table ── */}
      <div className="rt-scroll">
        <table className="rt-table">
          <thead>
            <tr className="rt-thead-row">
              <th className="rt-th rt-th-check" />
              <th className="rt-th rt-th-type">TYPE</th>
              <th className="rt-th rt-th-title">TITLE &amp; DESCRIPTION</th>
              {hasSections && <th className="rt-th rt-th-section">SECTION</th>}
              <th className="rt-th rt-th-source">COPY</th>
              <th className="rt-th rt-th-visit" />
            </tr>
          </thead>
          <tbody>
            {filteredResources.map((resource, index) => {
              const key = resource.url || `resource-${index}`;
              return (
                <ResourceRow
                  key={key}
                  resource={resource}
                  isSelected={selectedUrls.has(resource.url)}
                  onToggle={resource.url ? toggleHandlers.get(resource.url) : undefined}
                />
              );
            })}
          </tbody>
        </table>
      </div>

      {/* ── Footer ── */}
      <div className="rt-footer">
        Showing {filteredResources.length} of {totalCount} results
        {hasSections && activeFilter !== 'All' && ` · ${activeFilter}`}
      </div>
    </div>
  );
}
