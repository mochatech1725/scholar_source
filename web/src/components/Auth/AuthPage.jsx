/**
 * Auth Page Component
 *
 * Combined authentication page with tabs for login and signup.
 */

import { useState } from 'react';
import LoginForm from './LoginForm';
import SignupForm from './SignupForm';

export default function AuthPage() {
  const [activeTab, setActiveTab] = useState('login'); // 'login' or 'signup'

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-semibold text-slate-900 mb-2">
            📚 ScholarSource
          </h1>
          <p className="text-sm text-slate-600">
            Discover educational resources for your courses
          </p>
        </div>

        {/* Tab buttons */}
        <div className="flex border-b border-slate-200 mb-6 bg-white rounded-t-lg">
          <button
            type="button"
            onClick={() => setActiveTab('login')}
            className={`flex-1 py-3 px-4 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-inset ${
              activeTab === 'login'
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('signup')}
            className={`flex-1 py-3 px-4 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-inset ${
              activeTab === 'signup'
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            Sign Up
          </button>
        </div>

        {/* Form content */}
        <div className="mt-0">
          {activeTab === 'login' ? (
            <LoginForm onSwitchToSignup={() => setActiveTab('signup')} />
          ) : (
            <SignupForm onSwitchToLogin={() => setActiveTab('login')} />
          )}
        </div>
      </div>
    </div>
  );
}
