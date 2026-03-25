/**
 * Tests for StatusMessage component
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StatusMessage from './StatusMessage';

describe('StatusMessage', () => {
  it('renders error message with error CSS class', () => {
    const { container } = render(<StatusMessage type="error" message="Something went wrong" />);

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(container.firstChild).toHaveClass('status-message-error');
  });

  it('renders success message with success CSS class', () => {
    const { container } = render(<StatusMessage type="success" message="Operation completed" />);

    expect(screen.getByText('Operation completed')).toBeInTheDocument();
    expect(container.firstChild).toHaveClass('status-message-success');
  });

  it('renders info message with info CSS class', () => {
    const { container } = render(<StatusMessage type="info" message="Please wait" />);

    expect(screen.getByText('Please wait')).toBeInTheDocument();
    expect(container.firstChild).toHaveClass('status-message-info');
  });

  it('renders warning message with warning CSS class', () => {
    const { container } = render(<StatusMessage type="warning" message="Be careful" />);

    expect(screen.getByText('Be careful')).toBeInTheDocument();
    expect(container.firstChild).toHaveClass('status-message-warning');
  });

  it('does not render when message is empty string', () => {
    const { container } = render(<StatusMessage type="error" message="" />);

    expect(container.firstChild).toBeNull();
  });

  it('does not render when message is null', () => {
    const { container } = render(<StatusMessage type="error" message={null} />);

    expect(container.firstChild).toBeNull();
  });

  it('renders the default icon for the message type', () => {
    render(<StatusMessage type="error" message="Error occurred" />);

    // Component renders emoji icons inside an aria-hidden div
    const iconEl = document.querySelector('[aria-hidden="true"]');
    expect(iconEl).toBeInTheDocument();
    expect(iconEl.textContent).toBeTruthy();
  });
});
