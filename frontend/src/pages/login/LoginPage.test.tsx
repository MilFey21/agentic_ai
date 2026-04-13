import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { LoginPage } from './LoginPage';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('LoginPage', () => {
  it('renders login form', async () => {
    render(<LoginPage />);

    expect(screen.getByText('Вход в систему')).toBeInTheDocument();
    expect(screen.getByText(/Выберите пользователя/)).toBeInTheDocument();
  });

  it('displays available users', async () => {
    render(<LoginPage />);

    await waitFor(() => {
      expect(screen.getByText('admin')).toBeInTheDocument();
    });

    expect(screen.getByText('ivan_petrov')).toBeInTheDocument();
    expect(screen.getByText('maria_sidorova')).toBeInTheDocument();
  });

  it('enables login button when user is selected', async () => {
    const user = userEvent.setup();
    render(<LoginPage />);

    await waitFor(() => {
      expect(screen.getByText('admin')).toBeInTheDocument();
    });

    const loginButton = screen.getByRole('button', { name: /Войти/i });
    expect(loginButton).toBeDisabled();

    // Select a user
    const adminButton = screen.getByRole('button', { name: /Выбрать пользователя admin/i });
    await user.click(adminButton);

    expect(loginButton).toBeEnabled();
  });

  it('shows role badges for users', async () => {
    render(<LoginPage />);

    await waitFor(() => {
      expect(screen.getByText('Администратор')).toBeInTheDocument();
    });

    // Two students
    const studentBadges = screen.getAllByText('Студент');
    expect(studentBadges.length).toBe(2);
  });
});

