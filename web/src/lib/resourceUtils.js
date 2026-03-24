/**
 * Shared utilities for displaying resource metadata.
 */

/**
 * Maps resource type strings to a display label and a neutral typeKey.
 * typeKey is a lowercase string (e.g. 'pdf', 'video') that each component
 * can use to construct its own CSS class (e.g. `badge badge-${typeKey}`
 * or `rt-badge-${typeKey}`).
 */
const TYPE_MAP = [
  { keys: ['VIDEO', 'YOUTUBE'],         label: 'Video',    typeKey: 'video' },
  { keys: ['PDF', 'TEXTBOOK'],          label: 'PDF',      typeKey: 'pdf' },
  { keys: ['COURSE'],                   label: 'Course',   typeKey: 'course' },
  { keys: ['PRACTICE', 'PROBLEM'],      label: 'Practice', typeKey: 'practice' },
  { keys: ['NOTES'],                    label: 'Notes',    typeKey: 'notes' },
  { keys: ['WEBSITE', 'WEB'],           label: 'Web',      typeKey: 'website' },
];

/**
 * Returns the display label and typeKey for a resource type string.
 * Falls back to the raw type string and 'default' typeKey for unknown types.
 *
 * @param {string} type - Resource type from the API (e.g. "Video", "PDF")
 * @returns {{ label: string, typeKey: string }}
 */
export function getTypeMeta(type = '') {
  const upper = type.toUpperCase();
  for (const entry of TYPE_MAP) {
    if (entry.keys.some(k => upper.includes(k))) {
      return { label: entry.label, typeKey: entry.typeKey };
    }
  }
  return { label: type || '—', typeKey: 'default' };
}


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
