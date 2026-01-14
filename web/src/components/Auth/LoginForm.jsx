/**
 * Login Form Component
 *
 * Handles user login with email and password.
 */

import { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { TextLabel, TextInput, Button } from '../ui';

export default function LoginForm({ onSwitchToSignup }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const { signIn } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await signIn(email, password);
      // Redirect handled by AuthContext state change
    } catch (err) {
      setError(err.message || 'Failed to sign in');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-md border border-slate-200">
      <h2 className="text-2xl font-semibold mb-6 text-center text-slate-900">
        Sign In to ScholarSource
      </h2>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <TextLabel htmlFor="email">
            Email Address
          </TextLabel>
          <div className="mt-1">
            <TextInput
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              disabled={loading}
            />
          </div>
        </div>

        <div>
          <TextLabel htmlFor="password">
            Password
          </TextLabel>
          <div className="mt-1">
            <TextInput
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              disabled={loading}
            />
          </div>
        </div>

        <div className="pt-2">
          <Button
            type="submit"
            variant="primary"
            disabled={loading}
            className="w-full min-h-[44px] text-sm"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </Button>
        </div>
      </form>

      <div className="mt-6 text-center border-t border-slate-200 pt-4">
        <p className="text-sm text-slate-600">
          Don't have an account?{' '}
          <button
            type="button"
            onClick={onSwitchToSignup}
            className="text-blue-600 hover:text-blue-700 font-medium focus:outline-none focus:underline"
          >
            Sign up
          </button>
        </p>
      </div>
    </div>
  );
}
