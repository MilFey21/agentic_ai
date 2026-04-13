import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { ChatPage } from './ChatPage';
import { setMockUser, clearMockUser } from '@/test/test-utils';
import type { UserWithRole } from '@/api/types';

// Mock useParams
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ moduleId: 'mod-1' }),
    useNavigate: () => vi.fn(),
  };
});

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

describe('ChatPage', () => {
  beforeEach(() => {
    setMockUser(mockUser);
  });

  afterEach(() => {
    clearMockUser();
  });

  it('renders the chat interface', async () => {
    render(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Введите сообщение/i)).toBeInTheDocument();
    });
  });

  it('displays assistant name', async () => {
    render(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByText('SecurityBot')).toBeInTheDocument();
    });
  });

  it('shows message input area', async () => {
    render(<ChatPage />);

    await waitFor(() => {
      const textarea = screen.getByPlaceholderText(/Введите сообщение/i);
      expect(textarea).toBeInTheDocument();
    });

    const sendButton = screen.getByRole('button', { name: /Отправить/i });
    expect(sendButton).toBeInTheDocument();
  });

  it('disables send button when input is empty', async () => {
    render(<ChatPage />);

    await waitFor(() => {
      const sendButton = screen.getByRole('button', { name: /Отправить/i });
      expect(sendButton).toBeDisabled();
    });
  });
});
