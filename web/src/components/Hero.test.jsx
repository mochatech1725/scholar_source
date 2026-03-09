/**
 * Tests for the hero / how-it-works section rendered by HomePage
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import HomePage from '../pages/HomePage';

// Stub out heavy child components so the hero section renders in isolation
vi.mock('../api/client', () => ({
  submitJob: vi.fn(),
  uploadPdf: vi.fn(),
}));
vi.mock('../components/InlineSearchStatus', () => ({ default: () => null }));
vi.mock('../components/ResultsTable', () => ({ default: () => null }));
vi.mock('../components/StatusMessage', () => ({ default: () => null }));
vi.mock('../components/UserMenu/UserMenu', () => ({ default: () => null }));

describe('HomePage hero section', () => {
  beforeEach(() => {
    render(<HomePage />);
  });

  it('renders the page heading', () => {
    expect(screen.getByText(/Student Study Resource Finder/i)).toBeInTheDocument();
  });

  it('renders the how-it-works steps', () => {
    expect(screen.getByText(/How it works/i)).toBeInTheDocument();
    expect(screen.getByText(/Enter your course details/i)).toBeInTheDocument();
    expect(screen.getByText(/AI discovers resources/i)).toBeInTheDocument();
    expect(screen.getByText(/Select & copy links/i)).toBeInTheDocument();
    expect(screen.getByText(/Generate study tools/i)).toBeInTheDocument();
  });

  it('renders the Open NotebookLM link', () => {
    const links = screen.getAllByRole('link', { name: /Open NotebookLM/i });
    expect(links.length).toBeGreaterThan(0);
    expect(links[0]).toHaveAttribute('href', 'https://notebooklm.google.com');
  });
});
