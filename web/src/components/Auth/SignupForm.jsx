/**
 * Signup Form Component
 *
 * Handles user registration with email, password, and password confirmation.
 */

import { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { TextLabel, TextInput, Button, HelperText } from '../ui';

export default function SignupForm({ onSwitchToLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const { signUp } = useAuth();

  const validatePassword = (pwd) => {
    if (pwd.length < 8) {
      return 'Password must be at least 8 characters long';
    }
    if (!/[A-Z]/.test(pwd)) {
      return 'Password must contain at least one uppercase letter';
    }
    if (!/[a-z]/.test(pwd)) {
      return 'Password must contain at least one lowercase letter';
    }
    if (!/[0-9]/.test(pwd)) {
      return 'Password must contain at least one number';
    }
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Validate password strength
    const passwordError = validatePassword(password);
    if (passwordError) {
      setError(passwordError);
      return;
    }

    // Validate password confirmation
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);

    try {
      await signUp(email, password);
      // Success message or redirect handled by AuthContext
    } catch (err) {
      setError(err.message || 'Failed to create account');
    } finally {
      setLoading(false);
    }
  };

  const getPasswordStrength = () => {
    if (!password) return null;

    const error = validatePassword(password);
    if (error) return 'weak';

    // Strong if it has special characters too
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
      return 'strong';
    }

    return 'medium';
  };

  const passwordStrength = getPasswordStrength();

  return (
    <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-md border border-slate-200">
      <h2 className="text-2xl font-semibold mb-6 text-center text-slate-900">
        Create Your ScholarSource Account
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
          {password && (
            <div className="mt-2">
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${
                      passwordStrength === 'weak'
                        ? 'w-1/3 bg-red-500'
                        : passwordStrength === 'medium'
                        ? 'w-2/3 bg-amber-500'
                        : 'w-full bg-green-500'
                    }`}
                  />
                </div>
                <span
                  className={`text-xs font-medium ${
                    passwordStrength === 'weak'
                      ? 'text-red-600'
                      : passwordStrength === 'medium'
                      ? 'text-amber-600'
                      : 'text-green-600'
                  }`}
                >
                  {passwordStrength === 'weak'
                    ? 'Weak'
                    : passwordStrength === 'medium'
                    ? 'Medium'
                    : 'Strong'}
                </span>
              </div>
              <HelperText>
                Must be 8+ characters with uppercase, lowercase, and numbers
              </HelperText>
            </div>
          )}
        </div>

        <div>
          <TextLabel htmlFor="confirmPassword">
            Confirm Password
          </TextLabel>
          <div className="mt-1">
            <TextInput
              id="confirmPassword"
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
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
            {loading ? 'Creating account...' : 'Sign Up'}
          </Button>
        </div>
      </form>

      <div className="mt-6 text-center border-t border-slate-200 pt-4">
        <p className="text-sm text-slate-600">
          Already have an account?{' '}
          <button
            type="button"
            onClick={onSwitchToLogin}
            className="text-blue-600 hover:text-blue-700 font-medium focus:outline-none focus:underline"
          >
            Sign in
          </button>
        </p>
      </div>
    </div>
  );
}
