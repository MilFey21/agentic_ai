import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('redirects to login when not authenticated', async ({ page }) => {
    await page.goto('/modules');
    await expect(page).toHaveURL('/login');
  });

  test('can login and navigate to modules', async ({ page }) => {
    await page.goto('/login');

    // Wait for users to load
    await expect(page.getByText('admin')).toBeVisible();

    // Select admin user
    await page.getByRole('button', { name: /Выбрать пользователя admin/i }).click();

    // Click login
    await page.getByRole('button', { name: /Войти/i }).click();

    // Should navigate to modules
    await expect(page).toHaveURL('/modules');
    await expect(page.getByText('Каталог модулей')).toBeVisible();
  });

  test('shows role-based navigation for admin', async ({ page }) => {
    await page.goto('/login');

    await expect(page.getByText('admin')).toBeVisible();
    await page.getByRole('button', { name: /Выбрать пользователя admin/i }).click();
    await page.getByRole('button', { name: /Войти/i }).click();

    await expect(page).toHaveURL('/modules');

    // Admin should see admin link
    await expect(page.getByRole('link', { name: /Админ/i })).toBeVisible();
  });

  test('student cannot access admin pages', async ({ page }) => {
    await page.goto('/login');

    await expect(page.getByText('ivan_petrov')).toBeVisible();
    await page.getByRole('button', { name: /Выбрать пользователя ivan_petrov/i }).click();
    await page.getByRole('button', { name: /Войти/i }).click();

    await expect(page).toHaveURL('/modules');

    // Try to navigate to admin
    await page.goto('/admin');

    // Should redirect back to modules
    await expect(page).toHaveURL('/modules');
  });
});

