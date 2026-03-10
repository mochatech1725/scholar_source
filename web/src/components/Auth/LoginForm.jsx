/**
 * Login Form Component
 *
 * Handles user login with email and password.
 */

import { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';

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
    } catch (err) {
      setError(err.message || 'Failed to sign in');
    } finally {
      setLoading(false);
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

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="email" className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
            Email Address
          </label>
          <div className="relative">
            <span className="absolute inset-y-0 left-3 flex items-center text-slate-400 pointer-events-none">
              ✉️
            </span>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              disabled={loading}
              className="w-full pl-10 pr-4 py-3 border border-slate-200 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-60 transition"
            />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label htmlFor="password" className="block text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Password
            </label>
            <button
              type="button"
              className="text-xs text-blue-600 hover:text-blue-700 font-medium focus:outline-none focus:underline"
            >
              Forgot password?
            </button>
          </div>
          <div className="relative">
            <span className="absolute inset-y-0 left-3 flex items-center text-slate-400 pointer-events-none">
              🔒
            </span>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••"
              disabled={loading}
              className="w-full pl-10 pr-4 py-3 border border-slate-200 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-60 transition"
            />
          </div>
        </div>

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
