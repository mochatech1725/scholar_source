import { describe, it, expect } from 'vitest';
import { getHostname, getSiteName } from './resourceUtils';

describe('getHostname', () => {
  it('strips www. prefix', () => {
    expect(getHostname('https://www.example.com/page')).toBe('example.com');
  });

  it('returns empty string for null', () => {
    expect(getHostname(null)).toBe('');
  });

  it('returns empty string for empty string', () => {
    expect(getHostname('')).toBe('');
  });

  it('returns raw value for unparseable input', () => {
    expect(getHostname('not-a-url')).toBe('not-a-url');
  });
});

describe('getSiteName', () => {
  it('returns a known name for a mapped domain', () => {
    expect(getSiteName('https://www.youtube.com/watch?v=abc')).toBe('YouTube');
  });

  it('strips recognised .edu subdomain and capitalises', () => {
    // ocw.mit.edu -> "MIT" (subdomain is "ocw", university segment is "mit")
    expect(getSiteName('https://ocw.mit.edu/courses/6-001')).toBe('MIT');
  });

  it('converts hyphenated domain to title-case words', () => {
    expect(getSiteName('https://open-textbook.org/chapter/1')).toBe('Open Textbook');
  });

  it('returns empty-string fallback for null URL', () => {
    // getHostname returns '' -> parts is [''] -> first branch misses, falls to last return
    expect(getSiteName(null)).toBe('');
  });
});
