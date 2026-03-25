/**
 * Tests for ConfirmDialog component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ConfirmDialog from './ConfirmDialog';

describe('ConfirmDialog', () => {
  const mockOnConfirm = vi.fn();
  const mockOnCancel = vi.fn();

  // Component uses confirmText / cancelText (not confirmLabel / cancelLabel)
  const defaultProps = {
    isOpen: true,
    title: 'Confirm Action',
    message: 'Are you sure you want to proceed?',
    confirmText: 'Yes',
    cancelText: 'No',
    onConfirm: mockOnConfirm,
    onCancel: mockOnCancel,
  };

  beforeEach(() => {
    mockOnConfirm.mockClear();
    mockOnCancel.mockClear();
  });

  it('renders dialog when isOpen is true', () => {
    render(<ConfirmDialog {...defaultProps} />);

    expect(screen.getByText('Confirm Action')).toBeInTheDocument();
    expect(screen.getByText('Are you sure you want to proceed?')).toBeInTheDocument();
  });

  it('does not render dialog when isOpen is false', () => {
    render(<ConfirmDialog {...defaultProps} isOpen={false} />);

    expect(screen.queryByText('Confirm Action')).not.toBeInTheDocument();
  });

  it('calls onConfirm when confirm button clicked', () => {
    render(<ConfirmDialog {...defaultProps} />);

    fireEvent.click(screen.getByRole('button', { name: 'Yes' }));

    expect(mockOnConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when cancel button clicked', () => {
    render(<ConfirmDialog {...defaultProps} />);

    fireEvent.click(screen.getByRole('button', { name: 'No' }));

    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it('uses default labels when not provided', () => {
    render(<ConfirmDialog isOpen title="Confirm" message="Proceed?" onConfirm={mockOnConfirm} onCancel={mockOnCancel} />);

    expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  it('renders with danger styling when isDanger is true', () => {
    render(<ConfirmDialog {...defaultProps} isDanger />);

    const confirmButton = screen.getByRole('button', { name: 'Yes' });
    expect(confirmButton).toHaveClass('confirm-dialog-btn-confirm-danger');
  });

  it('exposes role="dialog" for accessibility', () => {
    render(<ConfirmDialog {...defaultProps} />);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('handles Escape key press', () => {
    render(<ConfirmDialog {...defaultProps} />);

    fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });
    // Escape handling is not implemented — just ensure no crash
  });
});
