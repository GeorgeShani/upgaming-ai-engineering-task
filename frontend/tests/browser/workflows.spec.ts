import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import type { Page } from '@playwright/test';

const token = 'browser-fixture-admin';
const source = '🚀 Fictional UI incident. Payment-router recovered after 12 minutes.';

async function manage(page: Page) {
  await page.getByRole('navigation', { name: 'Workspace views' }).getByRole('button', { name: 'Documents', exact: true }).click();
  await page.locator('.access-box > summary').click();
  await page.getByLabel('Demo admin token', { exact: true }).fill(token);
}

async function upload(page: Page, text = source, filename = 'browser-incident.txt') {
  await page.getByLabel('Add a document', { exact: true }).setInputFiles({ name: filename, mimeType: 'text/plain', buffer: Buffer.from(text) });
  await page.getByRole('button', { name: 'Upload document', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('region', { name: 'Canonical source text' })).toContainText(text);
}

test.beforeEach(async ({ page, request }) => {
  const probe = await request.get('/api/live');
  expect(probe.headers()['x-test-providers']).toBe('in-memory-only');
  expect((await request.post('/api/__test/reset')).ok()).toBeTruthy();
  await page.goto('/');
});

test('upload -> question -> citation -> trace -> delete through the real API', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await manage(page);
  await upload(page);
  await page.getByRole('button', { name: 'Close source' }).click();
  await page.getByRole('navigation').getByRole('button', { name: 'Investigate', exact: true }).click();
  await page.getByLabel('Your question').fill('What does the fictional UI incident report?');
  await page.getByRole('main').getByRole('button', { name: 'Investigate', exact: true }).click();
  await expect(page.getByText('Answered', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Open citation E1:/ }).click();
  await expect(page.getByRole('dialog')).toContainText('Retrieved evidence');
  await expect(page.getByRole('region', { name: 'Canonical source text' }).locator('mark')).toHaveText(source);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.getByRole('button', { name: /Open citation E1:/ })).toBeFocused();
  await page.getByText('Search trace', { exact: false }).click();
  await expect(page.getByText('Round 2', { exact: true })).toBeVisible();
  await expect(page.getByText(/probability that a claim is true/)).toBeVisible();
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations).toEqual([]);
  await page.screenshot({ path: '../artifacts/slice-7-answer.png', fullPage: true });
  await page.getByRole('navigation').getByRole('button', { name: 'Documents', exact: true }).click();
  await page.getByRole('button', { name: /Open last uploaded source:/ }).click();
  await page.getByRole('button', { name: 'Delete document', exact: true }).click();
  await page.getByRole('button', { name: 'Keep source' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button', { name: 'Delete document', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm delete' }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.getByText('No sources on this page')).toBeVisible();
  await expect(page.getByRole('button', { name: /Open last uploaded source:/ })).toHaveCount(0);
  expect(errors).toEqual([]);
});

test('duplicate upload reuses a source; replacement changes its revision', async ({ page }) => {
  await manage(page); await upload(page);
  await page.getByRole('button', { name: 'Close source' }).click();
  await upload(page);
  await page.getByRole('button', { name: 'Close source' }).click();
  await expect(page.getByRole('status')).toContainText('Already stored:');
  await expect(page.getByRole('list', { name: 'Stored documents' }).getByRole('listitem')).toHaveCount(1);
  await page.getByRole('button', { name: /Open last uploaded source:/ }).click();
  await page.getByLabel('Replacement file').setInputFiles({ name: 'updated.txt', mimeType: 'text/plain', buffer: Buffer.from('Fictional replacement. Recovery took 8 minutes.') });
  await page.getByRole('button', { name: 'Replace document', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Canonical source text' })).toContainText('Recovery took 8 minutes.');
  await expect(page.getByRole('dialog')).toContainText('Replacement saved.');
});
