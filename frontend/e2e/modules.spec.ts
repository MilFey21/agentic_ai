import { test, expect } from '@playwright/test';

test.describe('Modules', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login');
    await expect(page.getByText('ivan_petrov')).toBeVisible();
    await page.getByRole('button', { name: /Выбрать пользователя ivan_petrov/i }).click();
    await page.getByRole('button', { name: /Войти/i }).click();
    await expect(page).toHaveURL('/modules');
  });

  test('displays active modules', async ({ page }) => {
    await expect(page.getByText('Основы информационной безопасности')).toBeVisible();
    await expect(page.getByText('Социальная инженерия и фишинг')).toBeVisible();
  });

  test('can navigate to module detail', async ({ page }) => {
    await page.getByText('Основы информационной безопасности').click();
    
    await expect(page.getByRole('heading', { name: 'Основы информационной безопасности' })).toBeVisible();
    await expect(page.getByText('Начать обучение')).toBeVisible();
  });

  test('can start a task in player', async ({ page }) => {
    await page.getByText('Основы информационной безопасности').click();
    await page.getByText('Начать обучение').click();

    // Should be on player page
    await expect(page.getByText('Плеер обучения')).toBeVisible();

    // Select a task
    await page.getByText('Тест: Основы ИБ').click();

    // Task details should be visible
    await expect(page.getByRole('heading', { name: 'Тест: Основы ИБ' })).toBeVisible();
  });

  test('can open chat with assistant', async ({ page }) => {
    await page.getByText('Основы информационной безопасности').click();
    await page.getByText('Чат с ассистентом').click();

    // Should see chat interface
    await expect(page.getByPlaceholder(/Введите сообщение/i)).toBeVisible();
    await expect(page.getByText('SecurityBot')).toBeVisible();
  });
});

