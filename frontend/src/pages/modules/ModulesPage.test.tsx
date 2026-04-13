import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { ModulesPage } from './ModulesPage';
import { setMockUser, clearMockUser } from '@/test/test-utils';
import type { UserWithRole } from '@/api/types';

const mockUser: UserWithRole = {
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
};

describe('ModulesPage', () => {
  beforeEach(() => {
    setMockUser(mockUser);
  });

  afterEach(() => {
    clearMockUser();
  });

  it('renders the page title', async () => {
    render(<ModulesPage />);

    await waitFor(() => {
      expect(screen.getByText('Каталог модулей')).toBeInTheDocument();
    });
  });

  it('renders module cards after loading', async () => {
    render(<ModulesPage />);

    await waitFor(() => {
      expect(screen.getByText('Основы информационной безопасности')).toBeInTheDocument();
    });

    expect(screen.getByText('Социальная инженерия и фишинг')).toBeInTheDocument();
  });

  it('shows only active modules', async () => {
    render(<ModulesPage />);

    await waitFor(() => {
      expect(screen.getByText('Основы информационной безопасности')).toBeInTheDocument();
    });

    // Inactive module should not be displayed
    expect(screen.queryByText('Продвинутые техники пентеста')).not.toBeInTheDocument();
  });
});
