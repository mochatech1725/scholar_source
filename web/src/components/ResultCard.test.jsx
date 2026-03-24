/**
 * Tests for ResultCard component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ResultCard from './ResultCard';

describe('ResultCard', () => {
  const mockResource = {
    type: 'Textbook',
    title: 'Introduction to Algorithms',
    source: 'MIT Press',
    url: 'https://mitpress.mit.edu/books/introduction-algorithms',
    description: 'Comprehensive algorithms textbook covering fundamental concepts',
  };

  beforeEach(() => {
    // Reset clipboard mock before each test
    navigator.clipboard.writeText = vi.fn().mockResolvedValue();
  });

  it('renders resource information correctly', () => {
    render(<ResultCard resource={mockResource} index={0} />);

    expect(screen.getByText('Introduction to Algorithms')).toBeInTheDocument();
    expect(screen.getByText(/MIT Press/i)).toBeInTheDocument();
    expect(screen.getByText(/Comprehensive algorithms textbook/i)).toBeInTheDocument();
  });

  it('displays resource type badge', () => {
    render(<ResultCard resource={mockResource} index={0} />);

    // 'Textbook' type normalises to the 'PDF' label via getTypeMeta
    const badge = screen.getByText('PDF');
    expect(badge).toBeInTheDocument();
  });

  it('renders clickable URL link', () => {
    render(<ResultCard resource={mockResource} index={0} />);

    const link = screen.getByRole('link', { name: /visit resource/i });
    expect(link).toHaveAttribute('href', mockResource.url);
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('copies URL to clipboard when copy button clicked', async () => {
    render(<ResultCard resource={mockResource} index={0} />);

    const copyButton = screen.getByRole('button', { name: /copy url/i });
    fireEvent.click(copyButton);

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(mockResource.url);

    // Should show "Copied" feedback
    await waitFor(() => {
      expect(screen.getByText(/copied/i)).toBeInTheDocument();
    });
  });

  it('opens NotebookLM in new tab when button clicked', () => {
    const windowOpenSpy = vi.spyOn(window, 'open').mockImplementation();

    render(<ResultCard resource={mockResource} index={0} />);

    const notebookButton = screen.getByRole('button', { name: /notebooklm/i });
    fireEvent.click(notebookButton);

    expect(windowOpenSpy).toHaveBeenCalledWith(
      expect.stringContaining('notebooklm.google.com'),
      '_blank',
      'noopener,noreferrer'
    );

    windowOpenSpy.mockRestore();
  });

  it('handles different resource types with appropriate badges', () => {
    const videoResource = { ...mockResource, type: 'Video' };
    const { rerender } = render(<ResultCard resource={videoResource} index={0} />);

    expect(screen.getByText('Video')).toBeInTheDocument();

    const notesResource = { ...mockResource, type: 'Lecture Notes' };
    rerender(<ResultCard resource={notesResource} index={0} />);

    // 'Lecture Notes' matches the NOTES key and normalises to 'Notes'
    expect(screen.getByText('Notes')).toBeInTheDocument();
  });

  it('handles resource without description', () => {
    const resourceWithoutDesc = { ...mockResource, description: null };

    render(<ResultCard resource={resourceWithoutDesc} index={0} />);

    expect(screen.getByText('Introduction to Algorithms')).toBeInTheDocument();
    // Description should not be rendered
    expect(screen.queryByText(/Comprehensive algorithms/i)).not.toBeInTheDocument();
  });

  it('displays index number', () => {
    render(<ResultCard resource={mockResource} index={5} />);

    // Should display as "#6" (index + 1)
    expect(screen.getByText(/6/)).toBeInTheDocument();
  });

  describe('URL protocol validation (fix #3)', () => {
    it('renders title as a link for https:// URLs', () => {
      render(<ResultCard resource={mockResource} index={0} />);

      const titleLink = screen.getByRole('link', { name: /Introduction to Algorithms/i });
      expect(titleLink).toBeInTheDocument();
      expect(titleLink).toHaveAttribute('href', mockResource.url);
      expect(titleLink).toHaveAttribute('rel', 'noopener noreferrer');
    });

    it('renders title as a link for http:// URLs', () => {
      const httpResource = { ...mockResource, url: 'http://example.com/book' };
      render(<ResultCard resource={httpResource} index={0} />);

      const titleLink = screen.getByRole('link', { name: /Introduction to Algorithms/i });
      expect(titleLink).toHaveAttribute('href', 'http://example.com/book');
    });

    it('renders title as plain text for non-http(s) URLs', () => {
      const badResource = { ...mockResource, url: 'javascript:alert(1)' };
      render(<ResultCard resource={badResource} index={0} />);

      expect(screen.queryByRole('link', { name: /Introduction to Algorithms/i })).not.toBeInTheDocument();
      expect(screen.getByText('Introduction to Algorithms')).toBeInTheDocument();
    });

    it('renders title as plain text when url is null', () => {
      const badResource = { ...mockResource, url: null };
      render(<ResultCard resource={badResource} index={0} />);

      expect(screen.queryByRole('link', { name: /Introduction to Algorithms/i })).not.toBeInTheDocument();
      expect(screen.getByText('Introduction to Algorithms')).toBeInTheDocument();
    });
  });

  it('handles clipboard write failure gracefully', async () => {
    navigator.clipboard.writeText = vi.fn().mockRejectedValue(new Error('Clipboard error'));

    render(<ResultCard resource={mockResource} index={0} />);

    const copyButton = screen.getByRole('button', { name: /copy url/i });
    fireEvent.click(copyButton);

    // Should not crash
    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalled();
    });
  });
});
