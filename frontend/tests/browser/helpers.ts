import { expect } from '@playwright/test';
import type { APIRequestContext, Page } from '@playwright/test';

export const token = 'browser-fixture-admin';
export const source = '🚀 Fictional UI incident. Payment-router recovered after 12 minutes.';

export async function resetFixture(page: Page, request: APIRequestContext) {
  const probe = await request.get('/api/live');
  expect(probe.headers()['x-test-providers']).toBe('in-memory-only');
  expect((await request.post('/api/__test/reset')).ok()).toBeTruthy();
  await page.goto('/');
}

export async function manage(page: Page) {
  await page
    .getByRole('navigation', { name: 'Workspace views' })
    .getByRole('button', { name: 'Documents', exact: true })
    .click();
  await page.locator('.access-box > summary').click();
  await page.getByLabel('Demo admin token', { exact: true }).fill(token);
}

export async function upload(page: Page, text = source, filename = 'browser-incident.txt') {
  await page
    .getByLabel('Add a document', { exact: true })
    .setInputFiles({ name: filename, mimeType: 'text/plain', buffer: Buffer.from(text) });
  await page.getByRole('button', { name: 'Upload document', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('region', { name: 'Canonical source text' })).toContainText(text);
}

export async function createSource(request: APIRequestContext, text: string, name: string) {
  const response = await request.post('/api/documents', {
    headers: { Authorization: `Bearer ${token}` },
    multipart: { file: { name, mimeType: 'text/plain', buffer: Buffer.from(text) } },
  });
  expect(response.status()).toBe(201);
  return (await response.json()).document;
}
