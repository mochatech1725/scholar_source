/**
 * Login Form Component
 *
 * Handles user login with email and password.
 */

import { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import AuthInput from './AuthInput';

export default function LoginForm({ onSwitchToSignup }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  const { signIn, resetPassword } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);
    setLoading(true);
    try {
      await signIn(email, password);
    } catch (err) {
      setError(err.message || 'Failed to sign in');
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async () => {
    setError(null);
    setSuccessMessage(null);

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setError('Enter your email address first, then request a password reset.');
      return;
    }

    setResetLoading(true);
    try {
      await resetPassword(trimmedEmail);
      setSuccessMessage('Password reset email sent. Check your inbox for the reset link.');
    } catch (err) {
      setError(err.message || 'Failed to send password reset email');
    } finally {
      setResetLoading(false);
    }
  };

  return (
    <>
      <div className="mb-6">
        <h2 className="text-2xl font-bold" style={{ fontFamily: "'Fraunces', serif", color: '#1e3a5f' }}>
          Welcome back
        </h2>
        <p className="text-sm text-slate-500 mt-1">Sign in to continue finding resources</p>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {successMessage && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-700">{successMessage}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <AuthInput
          id="email"
          label="Email Address"
          type="email"
          icon="✉️"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          disabled={loading}
        />

        <AuthInput
          id="password"
          label="Password"
          type="password"
          icon="🔒"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••••"
          disabled={loading}
          showPasswordToggle
          labelExtra={
            <button
              type="button"
              onClick={handleForgotPassword}
              disabled={resetLoading || loading}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium focus:outline-none focus:underline"
            >
              {resetLoading ? 'Sending...' : 'Forgot password?'}
            </button>
          }
        />

        <div className="pt-2">
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 bg-slate-800 hover:bg-slate-900 text-white text-sm font-semibold rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-slate-700 focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {loading ? 'Signing in...' : 'Sign In →'}
          </button>
        </div>
      </form>

      <div className="mt-6 text-center border-t border-slate-100 pt-5">
        <p className="text-sm text-slate-500">
          Don't have an account?{' '}
          <button
            type="button"
            onClick={onSwitchToSignup}
            className="text-blue-600 hover:text-blue-700 font-semibold focus:outline-none focus:underline"
          >
            Sign up free
          </button>
        </p>
      </div>
    </>
  );
}
