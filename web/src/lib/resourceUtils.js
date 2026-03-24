/**
 * Shared utilities for displaying resource metadata.
 */

/**
 * Returns the hostname of a URL with the leading "www." stripped.
 * Returns an empty string for null/undefined input and the raw value
 * for unparseable strings.
 *
 * @param {string|null} url
 * @returns {string}
 */
export function getHostname(url) {
  if (!url) return '';
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

/**
 * Converts a resource URL into a short, human-readable site name.
 * Recognises common educational domains and falls back to the main
 * domain segment for everything else.
 *
 * @param {string|null} url
 * @returns {string}
 */
export function getSiteName(url) {
  const hostname = getHostname(url);
  const lower = hostname.toLowerCase();

  // Well-known educational domains
  if (lower.includes('mit.edu') || lower.includes('ocw.mit.edu')) return 'MIT';
  if (lower.includes('stanford.edu'))   return 'Stanford';
  if (lower.includes('berkeley.edu') || lower.includes('ucb.edu')) return 'UC Berkeley';
  if (lower.includes('openstax.org'))   return 'OpenStax';
  if (lower.includes('libretexts.org')) return 'LibreTexts';
  if (lower.includes('youtube.com') || lower.includes('youtu.be')) return 'YouTube';
  if (lower.includes('khanacademy.org')) return 'Khan Academy';
  if (lower.includes('coursera.org'))   return 'Coursera';
  if (lower.includes('edx.org'))        return 'edX';

  const parts = hostname.split('.');

  // .edu sites: lift the university name, skipping common subdomains
  if (lower.endsWith('.edu')) {
    if (parts.length > 2) {
      const subdomain = parts[parts.length - 3].toLowerCase();
      if (subdomain === 'ocw' || subdomain === 'www' || subdomain === 'web') {
        const name = parts[parts.length - 2];
        return name.charAt(0).toUpperCase() + name.slice(1);
      }
    }
    if (parts.length >= 2) {
      const name = parts[parts.length - 2];
      return name.charAt(0).toUpperCase() + name.slice(1);
    }
  }

  // General domains: use the part before the TLD, converting hyphens to spaces
  if (parts.length >= 2) {
    return parts[parts.length - 2]
      .split('-')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  }

  return parts[0].charAt(0).toUpperCase() + parts[0].slice(1);
}
