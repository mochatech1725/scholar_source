import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import useCopyToClipboard from './useCopyToClipboard';

describe('useCopyToClipboard', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    navigator.clipboard.writeText = vi.fn().mockResolvedValue();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('starts with copied = false', () => {
    const { result } = renderHook(() => useCopyToClipboard());
    expect(result.current[0]).toBe(false);
  });

  it('sets copied = true after copy()', async () => {
    const { result } = renderHook(() => useCopyToClipboard());
    const [, copy] = result.current;

    await act(async () => {
      await copy('https://example.com');
    });

    expect(result.current[0]).toBe(true);
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('https://example.com');
  });

  it('resets copied to false after delay', async () => {
    const { result } = renderHook(() => useCopyToClipboard(2000));
    const [, copy] = result.current;

    await act(async () => {
      await copy('https://example.com');
    });

    expect(result.current[0]).toBe(true);

    act(() => { vi.advanceTimersByTime(2000); });
    expect(result.current[0]).toBe(false);
  });

  it('respects custom resetDelay', async () => {
    const { result } = renderHook(() => useCopyToClipboard(500));
    const [, copy] = result.current;

    await act(async () => {
      await copy('text');
    });

    act(() => { vi.advanceTimersByTime(499); });
    expect(result.current[0]).toBe(true);

    act(() => { vi.advanceTimersByTime(1); });
    expect(result.current[0]).toBe(false);
  });

  it('handles clipboard failure without throwing', async () => {
    navigator.clipboard.writeText = vi.fn().mockRejectedValue(new Error('denied'));
    const { result } = renderHook(() => useCopyToClipboard());
    const [, copy] = result.current;

    await expect(act(async () => {
      await copy('text');
    })).resolves.not.toThrow();

    expect(result.current[0]).toBe(false);
  });
});
