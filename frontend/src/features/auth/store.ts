import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UserWithRole } from '@/api/types';
import { LOCAL_STORAGE_KEYS } from '@/shared/constants';

interface AuthState {
  user: UserWithRole | null;
  token: string | null;
  isAuthenticated: boolean;
  setUser: (user: UserWithRole | null) => void;
  setToken: (token: string | null) => void;
  setAuth: (user: UserWithRole, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      setUser: (user) =>
        set({
          user,
          isAuthenticated: !!user,
        }),
      setToken: (token) => {
        if (token) {
          localStorage.setItem(LOCAL_STORAGE_KEYS.AUTH_TOKEN, token);
        } else {
          localStorage.removeItem(LOCAL_STORAGE_KEYS.AUTH_TOKEN);
        }
        set({ token });
      },
      setAuth: (user, token) => {
        localStorage.setItem(LOCAL_STORAGE_KEYS.AUTH_TOKEN, token);
        set({
          user,
          token,
          isAuthenticated: true,
        });
      },
      logout: () => {
        localStorage.removeItem(LOCAL_STORAGE_KEYS.AUTH_TOKEN);
        set({
          user: null,
          token: null,
          isAuthenticated: false,
        });
      },
    }),
    {
      name: LOCAL_STORAGE_KEYS.CURRENT_USER,
      partialize: (state) => ({ user: state.user, token: state.token, isAuthenticated: state.isAuthenticated }),
      onRehydrateStorage: () => (state) => {
        // Sync token to localStorage when store is rehydrated
        if (state?.token) {
          localStorage.setItem(LOCAL_STORAGE_KEYS.AUTH_TOKEN, state.token);
        }
      },
    }
  )
);

// Helper hooks
export const useCurrentUser = () => useAuthStore((state) => state.user);
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useIsAdmin = () =>
  useAuthStore((state) => state.user?.role?.name === 'admin');
export const useIsStudent = () =>
  useAuthStore((state) => state.user?.role?.name === 'student');

