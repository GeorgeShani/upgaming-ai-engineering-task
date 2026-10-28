import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

import { manage, resetFixture, source, token, upload } from './helpers';

test.beforeEach(async ({ page, request }) => {
  await resetFixture(page, request);
});

test('upload -> question -> citation -> trace -> delete through the real API', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (['error', 'warning'].includes(message.type())) errors.push(message.text());
  });
  await page.reload({ waitUntil: 'networkidle' });
  await manage(page);
  await upload(page);
  await page.getByRole('button', { name: 'Close source' }).click();
  await page
    .getByRole('navigation')
    .getByRole('button', { name: 'Investigate', exact: true })
    .click();
  await page.getByLabel('Your question').fill('What does the fictional UI incident report?');
  await page.getByRole('main').getByRole('button', { name: 'Investigate', exact: true }).click();
  await expect(page.getByText('Answered', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Open citation E1:/ }).click();
  await expect(page.getByRole('dialog')).toContainText('Retrieved evidence');
  await expect(
    page.getByRole('region', { name: 'Canonical source text' }).locator('mark'),
  ).toHaveText(source);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.getByRole('button', { name: /Open citation E1:/ })).toBeFocused();
  await page.locator('details.search-trace > summary').click();
  await expect(page.getByText('Round 2', { exact: true })).toBeVisible();
  await expect(page.getByText(/probability that a claim is true/)).toBeVisible();
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations).toEqual([]);
  await page.screenshot({ path: '../artifacts/slice-7-answer.png', fullPage: true });
  await page
    .getByRole('navigation')
    .getByRole('button', { name: 'Documents', exact: true })
    .click();
  await page.getByRole('button', { name: /Open last uploaded source:/ }).click();
  await page.getByRole('button', { name: 'Delete document', exact: true }).click();
  await page.getByRole('button', { name: 'Keep source' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button', { name: 'Delete document', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm delete' }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.getByText('No sources on this page')).toBeVisible();
  await expect(page.getByRole('button', { name: /Open last uploaded source:/ })).toHaveCount(0);
  await expect(
    page.getByRole('navigation').getByRole('button', { name: 'Documents', exact: true }),
  ).toBeFocused();
  expect(errors).toEqual([]);
});

test('duplicate upload reuses a source; replacement changes its revision', async ({ page }) => {
  await manage(page);
  await upload(page);
  await page.getByRole('button', { name: 'Close source' }).click();
  await upload(page);
  await page.getByRole('button', { name: 'Close source' }).click();
  await expect(page.getByRole('status')).toContainText('Already stored:');
  await expect(
    page.getByRole('list', { name: 'Stored documents' }).getByRole('listitem'),
  ).toHaveCount(1);
  await page.getByRole('button', { name: /Open last uploaded source:/ }).click();
  await page.getByLabel('Replacement file').setInputFiles({
    name: 'updated.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('Fictional replacement. Recovery took 8 minutes.'),
  });
  await page.getByRole('button', { name: 'Replace document', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Canonical source text' })).toContainText(
    'Recovery took 8 minutes.',
  );
  await expect(page.getByRole('dialog')).toContainText('Replacement saved.');
});

test('stale replacement is blocked until current text and ETag are reloaded', async ({
  page,
  request,
}) => {
  await manage(page);
  await upload(page);
  const docs = (await (await request.get('/api/documents')).json()).items;
  const id = docs[0].document_id;
  const loaded = await request.get(`/api/documents/${id}`);
  await request.put(`/api/documents/${id}`, {
    headers: {
      Authorization: `Bearer ${token}`,
      'If-Match': loaded.headers().etag,
    },
    multipart: {
      file: {
        name: 'concurrent.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from('A concurrent revision. Recovery took 6 minutes.'),
      },
    },
  });
  await page.getByLabel('Replacement file').setInputFiles({
    name: 'mine.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('My reviewed revision.'),
  });
  await page.getByRole('button', { name: 'Replace document', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('This source changed.');
  await expect(page.getByRole('button', { name: 'Replace document', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Reload source', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Canonical source text' })).toContainText(
    'Recovery took 6 minutes.',
  );
  await expect(page.getByRole('button', { name: 'Replace document', exact: true })).toBeDisabled();
  await page.getByLabel('Replacement file').setInputFiles({
    name: 'mine.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('My reviewed revision.'),
  });
  await page.getByRole('button', { name: 'Replace document', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Canonical source text' })).toContainText(
    'My reviewed revision.',
  );
});

test('old citations stay snapshots after the document changes or disappears', async ({
  page,
  request,
}) => {
  await manage(page);
  await upload(page);
  await page.getByRole('button', { name: 'Close source' }).click();
  await page
    .getByRole('navigation')
    .getByRole('button', { name: 'Investigate', exact: true })
    .click();
  await page.getByLabel('Your question').fill('What does the fictional UI incident report?');
  await page.getByRole('main').getByRole('button', { name: 'Investigate', exact: true }).click();
  await expect(page.getByText('Answered', { exact: true })).toBeVisible();
  const id = (await (await request.get('/api/documents')).json()).items[0].document_id;
  const loaded = await request.get(`/api/documents/${id}`);
  const updated = await request.put(`/api/documents/${id}`, {
    headers: {
      Authorization: `Bearer ${token}`,
      'If-Match': loaded.headers().etag,
    },
    multipart: {
      file: {
        name: 'newer.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from('A later fictional report. Recovery took 4 minutes.'),
      },
    },
  });
  await page.getByRole('button', { name: /Open citation E1:/ }).click();
  await expect(page.getByRole('dialog')).toContainText('This source has a newer revision.');
  await expect(page.getByRole('region', { name: 'Retrieved evidence' })).toContainText(
    '12 minutes',
  );
  await expect(page.getByRole('region', { name: 'Canonical source text' })).toContainText(
    '4 minutes',
  );
  await expect(page.getByRole('dialog').locator('mark')).toHaveCount(0);
  await page.getByRole('button', { name: 'Close source' }).click();
  await request.delete(`/api/documents/${id}`, {
    headers: { Authorization: `Bearer ${token}`, 'If-Match': updated.headers().etag },
  });
  await page.getByRole('button', { name: /Open citation E1:/ }).click();
  await expect(page.getByRole('alert')).toContainText('This source is no longer available.');
  await expect(page.getByRole('region', { name: 'Retrieved evidence' })).toContainText(
    '12 minutes',
  );
});

test('source text is escaped, token clears on reload, and the dialog is keyboard accessible', async ({
  page,
}) => {
  await manage(page);
  await upload(
    page,
    '<img src=x onerror="alert(1)"> Fictional source content.',
    'literal-markup.txt',
  );
  await expect(page.getByRole('dialog').locator('img, script')).toHaveCount(0);
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations).toEqual([]);
  await page.keyboard.press('Escape');
  await page.reload();
  await page
    .getByRole('navigation')
    .getByRole('button', { name: 'Documents', exact: true })
    .click();
  await page.locator('.access-box > summary').click();
  await expect(page.getByLabel('Demo admin token', { exact: true })).toHaveValue('');
  await expect(page.getByRole('button', { name: 'Upload document', exact: true })).toBeDisabled();
});

for (const width of [320, 768, 1024, 1440]) {
  test(`workspace and source dialog fit at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await expect(page.getByLabel('Your question')).toBeVisible();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBeTruthy();
    await manage(page);
    await upload(page);
    const dialog = await page.getByRole('dialog').boundingBox();
    expect(dialog?.x).toBeGreaterThanOrEqual(0);
    expect((dialog?.x ?? 0) + (dialog?.width ?? 0)).toBeLessThanOrEqual(width);
    await expect(page.getByRole('button', { name: 'Close source' })).toBeVisible();
    const accessibility = await new AxeBuilder({ page }).analyze();
    expect(accessibility.violations).toEqual([]);
    await page.screenshot({ path: `../artifacts/slice-7-source-${width}.png` });
  });
}
