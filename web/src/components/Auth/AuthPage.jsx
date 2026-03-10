/**
 * Auth Page Component
 *
 * Combined authentication page with tabs for login and signup.
 */

import { useState } from 'react';
import LoginForm from './LoginForm';
import SignupForm from './SignupForm';

export default function AuthPage() {
  const [activeTab, setActiveTab] = useState('login');

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-4 py-10"
      style={{ background: 'linear-gradient(160deg, #1e3a5f 0%, #2c5282 40%, #dbe6f5 70%, #f0f4f8 100%)' }}
    >
      {/* Logo + tagline */}
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-2 mb-2">
          <span className="text-4xl">📚</span>
          <span
            className="text-3xl font-bold text-white"
            style={{ fontFamily: "'Barlow Condensed', sans-serif" }}
          >
            Scholar Source
          </span>
        </div>
        <p className="text-sm text-blue-200">Discover educational resources for your courses</p>
      </div>

      {/* Card */}
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden">
        {/* Tabs */}
        <div className="flex border-b border-slate-200">
          <button
            type="button"
            onClick={() => setActiveTab('login')}
            className={`flex-1 py-4 text-sm font-semibold transition-colors focus:outline-none ${
              activeTab === 'login'
                ? 'text-slate-900 border-b-2 border-slate-800'
                : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('signup')}
            className={`flex-1 py-4 text-sm font-semibold transition-colors focus:outline-none ${
              activeTab === 'signup'
                ? 'text-slate-900 border-b-2 border-slate-800'
                : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            Sign Up
          </button>
        </div>

        {/* Form */}
        <div className="p-8">
          {activeTab === 'login' ? (
            <LoginForm onSwitchToSignup={() => setActiveTab('signup')} />
          ) : (
            <SignupForm onSwitchToLogin={() => setActiveTab('login')} />
          )}
        </div>

        {/* Footer trust line */}
        <div className="px-8 pb-6 text-center text-xs text-slate-400 flex items-center justify-center gap-4">
          <span>🔒 Secure</span>
          <span>· No ads ·</span>
          <span>📖 Free to use</span>
        </div>
      </div>
    </div>
  );
}
