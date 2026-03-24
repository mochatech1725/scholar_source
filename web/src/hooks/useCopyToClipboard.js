import { useState, useCallback } from 'react';

/**
 * Manages clipboard copy with a timed "copied" confirmation state.
 *
 * @param {number} resetDelay - ms before `copied` resets to false (default 2000)
 * @returns {[boolean, (text: string) => Promise<void>]} [copied, copy]
 */
export default function useCopyToClipboard(resetDelay = 2000) {
  const [copied, setCopied] = useState(false);

  const copy = useCallback(async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), resetDelay);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  }, [resetDelay]);

  return [copied, copy];
}
