/**
 * ResultsTable Component
 *
 * Renders discovered resources in a flat grid or section-grouped layout.
 * Selection state is lifted to the parent via onSelectionChange so the
 * fixed bottom action bar in HomePage can drive Copy / NotebookLM actions.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ResultCard from './ResultCard';

export default function ResultsTable({ resources, searchTitle, textbookInfo, sectionGroups, onClear, onSelectionChange }) {
  // All resources flat — used for URL list, toggle handlers, total count
  const allResources = useMemo(() => {
    if (sectionGroups && sectionGroups.length > 0) {
      return sectionGroups.flatMap((g) => g.resources);
    }
    return resources || [];
  }, [resources, sectionGroups]);

  const totalCount = allResources.length;

  const urlList = useMemo(() => {
    return allResources.map((r) => r.url).filter(Boolean);
  }, [allResources]);

  // Track the current resources to detect changes
  const resourcesRef = useRef(resources);

  // Selected URLs (default: all)
  const [selectedUrls, setSelectedUrls] = useState(() => new Set(urlList));

  // Synchronize selection with resources changes
  useEffect(() => {
    if (resourcesRef.current !== resources) {
      resourcesRef.current = resources;
      setSelectedUrls(new Set(urlList));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resources]);

  const selectedCount = selectedUrls.size;

  const copyToClipboard = useCallback(async (text) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  }, []);

  const getSelectedUrlsInOrder = useCallback(() => {
    return urlList.filter((u) => selectedUrls.has(u));
  }, [urlList, selectedUrls]);

  const copySelected = useCallback(async () => {
    const selected = getSelectedUrlsInOrder();
    await copyToClipboard(selected.join('\n'));
  }, [getSelectedUrlsInOrder, copyToClipboard]);

  const copySelectedAndOpenNotebookLM = useCallback(async () => {
    const selected = getSelectedUrlsInOrder();
    await copyToClipboard(selected.join('\n'));
    window.open('https://notebooklm.google.com', '_blank', 'noopener,noreferrer');
  }, [getSelectedUrlsInOrder, copyToClipboard]);

  const handleSelectAll = useCallback(() => {
    setSelectedUrls(new Set(urlList));
  }, [urlList]);

  const handleClearSelection = useCallback(() => {
    setSelectedUrls(new Set());
  }, []);

  const toggleSelected = useCallback((url) => {
    setSelectedUrls((prev) => {
      const next = new Set(prev);
      if (next.has(url)) next.delete(url);
      else next.add(url);
      return next;
    });
  }, []);

  const toggleHandlers = useMemo(() => {
    const handlers = new Map();
    allResources.forEach((resource) => {
      if (resource.url) {
        handlers.set(resource.url, () => toggleSelected(resource.url));
      }
    });
    return handlers;
  }, [allResources, toggleSelected]);

  // Notify parent of selection changes so the bottom action bar can react
  useEffect(() => {
    onSelectionChange?.({
      selectedCount,
      totalCount,
      onCopy: copySelected,
      onCopyAndOpen: copySelectedAndOpenNotebookLM,
    });
  }, [selectedCount, totalCount, copySelected, copySelectedAndOpenNotebookLM, onSelectionChange]);

  if (allResources.length === 0) {
    return (
      <div className="results-table-empty">
        <div className="results-table-empty-content">
          <div className="results-table-empty-icon">📭</div>
          <h3 className="results-table-empty-title">No resources found</h3>
          <p className="results-table-empty-text">
            Try adjusting your search criteria or selecting a different search type.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="results-table-container">
      {/* Header */}
      <div className="results-table-header">
        <div className="results-table-header-content">
          <div className="results-table-title-section">
            <h2 className="results-table-title">
              Discovered Resources
              <span className="count-badge ml-2">{totalCount}</span>
            </h2>
            {searchTitle && <p className="results-table-subtitle">{searchTitle}</p>}
          </div>

          <div className="flex items-center gap-3 flex-shrink-0">
            {/* Select all / clear selection */}
            <div className="flex items-center gap-2">
              <span className="results-table-selection-badge">{selectedCount} selected</span>
              <button type="button" onClick={handleSelectAll} className="results-table-control-link">
                All
              </button>
              <button type="button" onClick={handleClearSelection} className="results-table-control-link">
                None
              </button>
            </div>

            {onClear && (
              <button onClick={onClear} className="results-table-clear-btn" title="Clear results">
                Clear results
              </button>
            )}
          </div>
        </div>

        {/* Textbook Info */}
        {(textbookInfo?.book_title || textbookInfo?.book_author || textbookInfo?.title || textbookInfo?.author) && (
          <div className="textbook-info mt-3">
            <div className="flex items-start gap-3">
              <div className="text-2xl flex-shrink-0 mt-0.5">📚</div>
              <div className="min-w-0 flex-1">
                <p className="m-0 mb-1 text-xs font-semibold uppercase tracking-wide text-amber-700">Course Textbook</p>
                {(textbookInfo?.book_title || textbookInfo?.title) && (
                  <p className="m-0 mb-1 text-base sm:text-lg font-bold text-slate-900 leading-tight">
                    {textbookInfo.book_title || textbookInfo.title}
                  </p>
                )}
                {(textbookInfo?.book_author || textbookInfo?.author) && (
                  <p className="m-0 text-sm text-slate-700 font-medium">by {textbookInfo.book_author || textbookInfo.author}</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Help text */}
        <p className="text-xs text-slate-500 mt-2">
          Select resources, then use <strong>Copy Selected + NotebookLM</strong> in the bar at the bottom of the screen.
        </p>
      </div>

      {/* Grid of cards — section-grouped or flat */}
      <div className="results-table-content">
        {sectionGroups && sectionGroups.length > 0 ? (
          <div className="space-y-6">
            {sectionGroups.map((group) => (
              <div key={group.section}>
                <h3 className="text-base font-semibold text-slate-800 mb-3 pb-1 border-b border-slate-200">
                  {group.section}
                </h3>
                <div className="results-table-grid">
                  {group.resources.map((resource, index) => {
                    const uniqueKey = resource.url || `${group.section}-resource-${index}`;
                    return (
                      <ResultCard
                        key={uniqueKey}
                        resource={resource}
                        index={index}
                        onCopy={copyToClipboard}
                        isSelected={selectedUrls.has(resource.url)}
                        onToggleSelect={resource.url ? toggleHandlers.get(resource.url) : undefined}
                      />
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="results-table-grid">
            {resources.map((resource, index) => {
              const uniqueKey = resource.url || `resource-${resource.title || resource.type || 'unknown'}-${index}`;
              return (
                <ResultCard
                  key={uniqueKey}
                  resource={resource}
                  index={index}
                  onCopy={copyToClipboard}
                  isSelected={selectedUrls.has(resource.url)}
                  onToggleSelect={resource.url ? toggleHandlers.get(resource.url) : undefined}
                />
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
