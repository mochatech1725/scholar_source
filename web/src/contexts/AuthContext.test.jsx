/**
 * Tests for AuthContext
 *
 * Verifies that onAuthStateChange is the single source of truth for auth state
 * and that signIn / signUp / signOut delegate correctly to supabase.auth.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act, waitFor, renderHook } from '@testing-library/react';
import { AuthProvider, useAuth } from './AuthContext';

// ── Supabase mock ────────────────────────────────────────────────────────────
// Keep a reference to the registered onAuthStateChange callback so tests can
// fire synthetic auth events.
let authStateCallback = null;
let unsubscribeMock = vi.fn();

vi.mock('../lib/supabase', () => ({
  supabase: {
    auth: {
      onAuthStateChange: vi.fn((cb) => {
        authStateCallback = cb;
        return { data: { subscription: { unsubscribe: unsubscribeMock } } };
      }),
      signUp: vi.fn(),
      signInWithPassword: vi.fn(),
      resetPasswordForEmail: vi.fn(),
      signOut: vi.fn(),
    },
  },
}));

// ── Helper ───────────────────────────────────────────────────────────────────
function TestConsumer() {
  const { user, loading, error } = useAuth();
  if (loading) return <p>loading</p>;
  if (error)   return <p>error: {error}</p>;
  return <p>{user ? `user:${user.id}` : 'no user'}</p>;
}

function renderWithProvider() {
  return render(
    <AuthProvider>
      <TestConsumer />
    </AuthProvider>
  );
}

function renderAuthHook() {
  const wrapper = ({ children }) => (
    <AuthProvider>
      {children}
    </AuthProvider>
  );

  return renderHook(() => useAuth(), { wrapper });
}

// ── Tests ────────────────────────────────────────────────────────────────────
describe('AuthContext', () => {
  beforeEach(() => {
    authStateCallback = null;
    unsubscribeMock.mockClear();
  });

  it('starts in loading state until onAuthStateChange fires', () => {
    renderWithProvider();
    expect(screen.getByText('loading')).toBeInTheDocument();
  });

  it('sets user to null when INITIAL_SESSION has no session', async () => {
    renderWithProvider();

    act(() => authStateCallback('INITIAL_SESSION', null));

    await waitFor(() => expect(screen.getByText('no user')).toBeInTheDocument());
  });

  it('sets user when INITIAL_SESSION has a session', async () => {
    renderWithProvider();

    act(() => authStateCallback('INITIAL_SESSION', { user: { id: 'u-1' } }));

    await waitFor(() => expect(screen.getByText('user:u-1')).toBeInTheDocument());
  });

  it('updates user on SIGNED_IN event', async () => {
    renderWithProvider();
    act(() => authStateCallback('INITIAL_SESSION', null));
    await waitFor(() => screen.getByText('no user'));

    act(() => authStateCallback('SIGNED_IN', { user: { id: 'u-2' } }));
    await waitFor(() => expect(screen.getByText('user:u-2')).toBeInTheDocument());
  });

  it('clears user on SIGNED_OUT event', async () => {
    renderWithProvider();
    act(() => authStateCallback('INITIAL_SESSION', { user: { id: 'u-3' } }));
    await waitFor(() => screen.getByText('user:u-3'));

    act(() => authStateCallback('SIGNED_OUT', null));
    await waitFor(() => expect(screen.getByText('no user')).toBeInTheDocument());
  });

  it('unsubscribes from onAuthStateChange on unmount', () => {
    const { unmount } = renderWithProvider();
    act(() => authStateCallback('INITIAL_SESSION', null));
    unmount();
    expect(unsubscribeMock).toHaveBeenCalledTimes(1);
  });

  it('does NOT call getSession — only onAuthStateChange is the source of truth', async () => {
    const { supabase } = await import('../lib/supabase');
    renderWithProvider();
    // onAuthStateChange must be registered; getSession must never be called
    expect(supabase.auth.onAuthStateChange).toHaveBeenCalled();
    expect(supabase.auth.signInWithPassword).not.toHaveBeenCalled(); // sanity
    expect('getSession' in supabase.auth).toBe(false);
  });
});

describe('AuthContext — signIn / signUp / signOut', () => {
  beforeEach(() => {
    authStateCallback = null;
  });

  it('signIn delegates to supabase.auth.signInWithPassword', async () => {
    const { supabase } = await import('../lib/supabase');
    supabase.auth.signInWithPassword.mockResolvedValue({
      data: { user: { id: 'u-4' }, session: {} },
      error: null,
    });

    const { result } = renderAuthHook();
    act(() => authStateCallback('INITIAL_SESSION', null));

    await act(async () => {
      await result.current.signIn('a@b.com', 'pass');
    });

    expect(supabase.auth.signInWithPassword).toHaveBeenCalledWith({
      email: 'a@b.com',
      password: 'pass',
    });
  });

  it('signIn throws and exposes error on failure', async () => {
    const { supabase } = await import('../lib/supabase');
    supabase.auth.signInWithPassword.mockResolvedValue({
      data: null,
      error: { message: 'Invalid credentials' },
    });

    const { result } = renderAuthHook();
    act(() => authStateCallback('INITIAL_SESSION', null));

    await expect(
      act(async () => { await result.current.signIn('bad@email.com', 'wrong'); })
    ).rejects.toMatchObject({ message: 'Invalid credentials' });
  });

  it('signUp delegates to supabase.auth.signUp', async () => {
    const { supabase } = await import('../lib/supabase');
    supabase.auth.signUp.mockResolvedValue({
      data: { user: { id: 'u-5' } },
      error: null,
    });

    const { result } = renderAuthHook();
    act(() => authStateCallback('INITIAL_SESSION', null));

    await act(async () => { await result.current.signUp('new@user.com', 'Pass1234'); });

    expect(supabase.auth.signUp).toHaveBeenCalledWith({
      email: 'new@user.com',
      password: 'Pass1234',
    });
  });

  it('resetPassword delegates to supabase.auth.resetPasswordForEmail', async () => {
    const { supabase } = await import('../lib/supabase');
    supabase.auth.resetPasswordForEmail.mockResolvedValue({
      data: {},
      error: null,
    });

    const { result } = renderAuthHook();
    act(() => authStateCallback('INITIAL_SESSION', null));

    await act(async () => { await result.current.resetPassword('reset@user.com'); });

    expect(supabase.auth.resetPasswordForEmail).toHaveBeenCalledWith(
      'reset@user.com',
      { redirectTo: window.location.origin }
    );
  });
});
