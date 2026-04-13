import { LOCAL_STORAGE_KEYS } from '@/shared/constants';

// API base URL - empty to go through nginx proxy
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// Auth error codes that should trigger logout
const AUTH_ERROR_CODES = [401, 403];

// Error messages that indicate auth issues (for 422 responses)
const AUTH_ERROR_MESSAGES = [
  'token',
  'expired',
  'invalid',
  'unauthorized',
  'credential',
  'authentication',
  'jwt',
  'signature',
];

/**
 * Check if an error response indicates an authentication failure
 */
function isAuthError(status: number, errorBody: { detail?: string; message?: string }): boolean {
  // Direct auth error codes
  if (AUTH_ERROR_CODES.includes(status)) {
    return true;
  }
  
  // Check for auth-related 422 errors (e.g., invalid/expired token)
  if (status === 422) {
    const errorText = (errorBody.detail || errorBody.message || '').toLowerCase();
    return AUTH_ERROR_MESSAGES.some(keyword => errorText.includes(keyword));
  }
  
  return false;
}

/**
 * Handle authentication failure by clearing auth state and redirecting to login
 */
function handleAuthFailure(): void {
  // Clear all auth data from localStorage
  localStorage.removeItem(LOCAL_STORAGE_KEYS.AUTH_TOKEN);
  localStorage.removeItem(LOCAL_STORAGE_KEYS.CURRENT_USER);
  
  // Redirect to login page if not already there
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = this.baseUrl ? `${this.baseUrl}${endpoint}` : endpoint;
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    // Add auth token if available
    const token = localStorage.getItem(LOCAL_STORAGE_KEYS.AUTH_TOKEN);
    if (token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({ message: 'Unknown error' }));
      
      // Check for auth errors and handle them
      if (isAuthError(response.status, errorBody)) {
        handleAuthFailure();
        throw new Error('Сессия истекла. Пожалуйста, войдите заново.');
      }
      
      throw new Error(errorBody.detail || errorBody.message || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  async get<T>(endpoint: string, params?: Record<string, string>): Promise<T> {
    const url = params
      ? `${endpoint}?${new URLSearchParams(params).toString()}`
      : endpoint;
    return this.request<T>(url, { method: 'GET' });
  }

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async patch<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

export const apiClient = new ApiClient(API_BASE_URL);

