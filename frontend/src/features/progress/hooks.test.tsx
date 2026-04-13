import React from 'react';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useUserProgress } from './hooks';
import { useAuthStore } from '@/features/auth/store';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('useUserProgress', () => {
  beforeEach(() => {
    useAuthStore.getState().setUser({
      id: 'user-2',
      role_id: 'role-2',
      username: 'ivan_petrov',
      email: 'ivan@example.com',
      langflow_user_id: null,
      langflow_folder_id: null,
      created_at: '2025-01-15T14:30:00Z',
      updated_at: '2025-01-15T14:30:00Z',
      deleted_at: null,
      role: {
        id: 'role-2',
        name: 'student',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
        deleted_at: null,
      },
    });
  });

  afterEach(() => {
    useAuthStore.getState().logout();
  });

  it('fetches user progress', async () => {
    const { result } = renderHook(() => useUserProgress(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeDefined();
    expect(Array.isArray(result.current.data)).toBe(true);
  });

  it('returns progress for the authenticated user', async () => {
    const { result } = renderHook(() => useUserProgress(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const progress = result.current.data;
    expect(progress?.every((p) => p.user_id === 'user-2')).toBe(true);
  });
});

