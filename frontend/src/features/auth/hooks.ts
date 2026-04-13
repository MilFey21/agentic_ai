import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi } from '@/api/endpoints';
import { useAuthStore } from './store';
import type { UserWithRole, LoginRequest, LoginCredentials, RegisterRequest } from '@/api/types';

export const authKeys = {
  all: ['auth'] as const,
  me: () => [...authKeys.all, 'me'] as const,
  users: () => [...authKeys.all, 'users'] as const,
};

export function useUsers() {
  return useQuery({
    queryKey: authKeys.users(),
    queryFn: () => authApi.getUsers(),
  });
}

// Real login with username/password
export function useLoginWithCredentials() {
  const queryClient = useQueryClient();
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation({
    mutationFn: async (data: LoginCredentials) => {
      // First, get the token
      const tokenResponse = await authApi.loginWithCredentials(data);
      // Store token temporarily to make the /me request work
      localStorage.setItem('windchaser_auth_token', tokenResponse.access_token);
      // Then fetch user data
      const user = await authApi.me();
      return { user, token: tokenResponse.access_token };
    },
    onSuccess: ({ user, token }) => {
      setAuth(user, token);
      queryClient.invalidateQueries({ queryKey: authKeys.me() });
    },
    onError: () => {
      // Remove token if login failed
      localStorage.removeItem('windchaser_auth_token');
    },
  });
}

// Registration
export function useRegister() {
  return useMutation({
    mutationFn: (data: RegisterRequest) => authApi.register(data),
  });
}

// Demo login (by user_id selection)
export function useDemoLogin() {
  const queryClient = useQueryClient();
  const setUser = useAuthStore((state) => state.setUser);

  return useMutation({
    mutationFn: (data: LoginRequest) => authApi.demoLogin(data),
    onSuccess: (user: UserWithRole) => {
      setUser(user);
      queryClient.invalidateQueries({ queryKey: authKeys.me() });
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  const logout = useAuthStore((state) => state.logout);

  return () => {
    logout();
    queryClient.clear();
  };
}

