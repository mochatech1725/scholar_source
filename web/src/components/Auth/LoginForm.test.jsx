import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import LoginForm from './LoginForm';

const signIn = vi.fn();
const resetPassword = vi.fn();

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    signIn,
    resetPassword,
  }),
}));

describe('LoginForm', () => {
  beforeEach(() => {
    signIn.mockReset();
    resetPassword.mockReset();
  });

  it('asks for an email before sending a password reset', () => {
    render(<LoginForm onSwitchToSignup={() => {}} />);

    fireEvent.click(screen.getByRole('button', { name: 'Forgot password?' }));

    expect(screen.getByText('Enter your email address first, then request a password reset.')).toBeInTheDocument();
    expect(resetPassword).not.toHaveBeenCalled();
  });

  it('sends a password reset email for the entered email address', async () => {
    resetPassword.mockResolvedValue({});
    render(<LoginForm onSwitchToSignup={() => {}} />);

    fireEvent.change(screen.getByLabelText('Email Address'), {
      target: { value: 'student@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Forgot password?' }));

    await waitFor(() => expect(resetPassword).toHaveBeenCalledWith('student@example.com'));
    expect(screen.getByText('Password reset email sent. Check your inbox for the reset link.')).toBeInTheDocument();
  });
});
