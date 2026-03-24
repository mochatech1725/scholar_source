/**
 * Signup Form Component
 *
 * Handles user registration with email, password, and password confirmation.
 */

import { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import AuthInput from './AuthInput';

export default function SignupForm({ onSwitchToLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const { signUp } = useAuth();

  const validatePassword = (pwd) => {
    if (pwd.length < 8) return 'Password must be at least 8 characters long';
    if (!/[A-Z]/.test(pwd)) return 'Password must contain at least one uppercase letter';
    if (!/[a-z]/.test(pwd)) return 'Password must contain at least one lowercase letter';
    if (!/[0-9]/.test(pwd)) return 'Password must contain at least one number';
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const passwordError = validatePassword(password);
    if (passwordError) { setError(passwordError); return; }
    if (password !== confirmPassword) { setError('Passwords do not match'); return; }

    setLoading(true);
    try {
      await signUp(email, password);
    } catch (err) {
      setError(err.message || 'Failed to create account');
    } finally {
      setLoading(false);
    }
  };

  const getPasswordStrength = () => {
    if (!password) return null;
    if (validatePassword(password)) return 'weak';
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) return 'strong';
    return 'medium';
  };

  const passwordStrength = getPasswordStrength();

  return (
    <>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-900" style={{ fontFamily: "'Fraunces', serif" }}>
          Create account
        </h2>
        <p className="text-sm text-slate-500 mt-1">Start discovering educational resources</p>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
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
        >
          {password && (
            <div className="mt-2 flex items-center gap-2">
              <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 ${
                    passwordStrength === 'weak' ? 'w-1/3 bg-red-500'
                    : passwordStrength === 'medium' ? 'w-2/3 bg-amber-500'
                    : 'w-full bg-green-500'
                  }`}
                />
              </div>
              <span className={`text-xs font-medium ${
                passwordStrength === 'weak' ? 'text-red-600'
                : passwordStrength === 'medium' ? 'text-amber-600'
                : 'text-green-600'
              }`}>
                {passwordStrength === 'weak' ? 'Weak' : passwordStrength === 'medium' ? 'Medium' : 'Strong'}
              </span>
            </div>
          )}
          <p className="mt-1 text-xs text-slate-400">8+ characters with uppercase, lowercase, and numbers</p>
        </AuthInput>

        <AuthInput
          id="confirmPassword"
          label="Confirm Password"
          type="password"
          icon="🔒"
          required
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          placeholder="••••••••••"
          disabled={loading}
        />

        <div className="pt-2">
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 bg-slate-800 hover:bg-slate-900 text-white text-sm font-semibold rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-slate-700 focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {loading ? 'Creating account...' : 'Create Account →'}
          </button>
        </div>
      </form>

      <div className="mt-6 text-center border-t border-slate-100 pt-5">
        <p className="text-sm text-slate-500">
          Already have an account?{' '}
          <button
            type="button"
            onClick={onSwitchToLogin}
            className="text-blue-600 hover:text-blue-700 font-semibold focus:outline-none focus:underline"
          >
            Sign in
          </button>
        </p>
      </div>
    </>
  );
}
