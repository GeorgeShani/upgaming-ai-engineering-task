import { expect, test } from '@playwright/test';
import { createSource, manage, resetFixture, token } from './helpers';
import type { Investigation, Evidence } from '../../src/types';

function result(status: Investigation['status']): Investigation {
  const evidence: Evidence[] = [3, 5].map((value, index) => ({
    evidence_id: `E${index + 1}`,
    chunk_id: `chunk-${index}`,
    document_id: `doc-${index}`,
    revision_id: 'revision',
    title: `Report ${index + 1}`,
    text: `Retry limit was ${value} attempts.`,
    start: 0,
    end: 27,
    locations: [],
    metadata: {},
    fusion_score: 0.03,
  }));
  return {
    status,
    answer:
      status === 'insufficient_evidence'
        ? 'The sources do not name an approver.'
        : 'Reports disagree.',
    claims: [],
    conflicting_claims:
      status === 'conflicting_evidence'
        ? evidence.map((hit) => ({
            text: hit.text,
            citations: [{ evidence_id: hit.evidence_id, quote: hit.text }],
          }))
        : [],
    evidence: status === 'insufficient_evidence' ? [] : evidence,
    search_trace: [],
    latency_ms: 120,
    execution: { retrieval_rounds: 2, searches: 2, llm_calls: 3, stop_reason: 'retrieval_limit' },
    usage: { estimated_total_cost_usd: 0.001 },
    configuration: { strategy: 'a', generation_model: 'fixture', prompt_version: 'fixture' },
  };
}

test.beforeEach(async ({ page, request }) => {
  await resetFixture(page, request);
});

test('browse shortcut preserves a draft, moves focus, and never submits a question', async ({
  page,
}) => {
  let paidRequests = 0;
  page.on('request', (request) => {
    if (request.url().endsWith('/api/investigations')) paidRequests += 1;
  });
  await page.getByLabel('Your question').fill('Which source reports the recovery time?');
  await page.getByRole('button', { name: 'Browse documents', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Documents', exact: true })).toBeFocused();
  await page
    .getByRole('navigation')
    .getByRole('button', { name: 'Investigate', exact: true })
    .click();
  await expect(page.getByLabel('Your question')).toHaveValue(
    'Which source reports the recovery time?',
  );
  await page.getByRole('button', { name: 'Use a development example' }).click();
  await expect(page.getByLabel('Your question')).toBeFocused();
  expect(paidRequests).toBe(0);
});

for (const status of ['conflicting_evidence', 'insufficient_evidence'] as const) {
  test(`renders ${status} as an evidence result, not an API error`, async ({ page }) => {
    await page.route('**/api/investigations', (route) => route.fulfill({ json: result(status) }));
    await page.getByLabel('Your question').fill('Who approved this fictional change?');
    await page.getByRole('main').getByRole('button', { name: 'Investigate', exact: true }).click();
    await expect(
      page.getByText(
        status === 'conflicting_evidence' ? 'Conflicting evidence' : 'Insufficient evidence',
        { exact: true },
      ),
    ).toBeVisible();
    await expect(page.getByRole('alert')).toHaveCount(0);
    if (status === 'conflicting_evidence') {
      await expect(page.getByText('Retry limit was 3 attempts.', { exact: true })).toBeVisible();
      await expect(page.getByText('Retry limit was 5 attempts.', { exact: true })).toBeVisible();
      await expect(page.getByRole('button', { name: /Open citation/ })).toHaveCount(2);
    } else await expect(page.getByText('The sources do not name an approver.')).toBeVisible();
  });
}

for (const status of [429, 502, 503]) {
  test(`HTTP ${status} is an actionable error and is not retried automatically`, async ({
    page,
  }) => {
    let calls = 0;
    await page.route('**/api/investigations', (route) => {
      calls += 1;
      return route.fulfill({
        status,
        headers: { 'Retry-After': '60' },
        json: { detail: 'Fixture dependency unavailable.' },
      });
    });
    await page.getByLabel('Your question').fill('What happened in the fictional source?');
    await page.getByRole('main').getByRole('button', { name: 'Investigate', exact: true }).click();
    await expect(page.getByRole('alert')).toContainText('Investigation could not finish');
    await expect(page.getByRole('alert')).toContainText('not an insufficient-evidence result');
    if (status === 429) await expect(page.getByRole('alert')).toContainText('60 seconds');
    await expect(page.locator('.result-status')).toHaveCount(0);
    expect(calls).toBe(1);
  });
}

test('pending questions cannot submit a second paid request', async ({ page }) => {
  let calls = 0;
  let finish = () => {};
  const gate = new Promise<void>((resolve) => {
    finish = resolve;
  });
  await page.route('**/api/investigations', async (route) => {
    calls += 1;
    await gate;
    await route.fulfill({ json: result('insufficient_evidence') });
  });
  await page.getByLabel('Your question').fill('Who approved the fictional change?');
  await page.getByRole('main').getByRole('button', { name: 'Investigate', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Investigating…', exact: true })).toBeDisabled();
  await expect(page.getByLabel('Your question')).toBeDisabled();
  await page.keyboard.press('Enter');
  await expect.poll(() => calls).toBe(1);
  finish();
  await expect(page.getByText('Insufficient evidence', { exact: true })).toBeVisible();
  expect(calls).toBe(1);
});

test('question validation explains that no paid request was submitted', async ({ page }) => {
  let calls = 0;
  page.on('request', (request) => {
    if (request.url().endsWith('/api/investigations')) calls += 1;
  });
  await page.getByLabel('Your question').fill('x'.repeat(1001));
  await page.getByRole('main').getByRole('button', { name: 'Investigate', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Check your question');
  await expect(page.getByRole('alert')).toContainText('Nothing has been submitted.');
  expect(calls).toBe(0);
});

test('trace distinguishes a proposed query from its grounded executed query', async ({ page }) => {
  const report = result('insufficient_evidence');
  report.search_trace = [
    {
      query: 'Verified Entity recovery time',
      requested_query: 'recovery time',
      query_adjusted: true,
      round: 2,
      tool_call_id: 'verification',
      executed: true,
      follow_up: { evidence_id: 'E1', entity: 'Verified Entity' },
      evidence: [],
      candidate_counts: { dense: 0, bm25: 0, active_dense: 0, active_bm25: 0 },
    },
  ];
  await page.route('**/api/investigations', (route) => route.fulfill({ json: report }));
  await page.getByLabel('Your question').fill('What was the recovery time?');
  await page.getByRole('main').getByRole('button', { name: 'Investigate', exact: true }).click();
  await page.locator('details.search-trace > summary').click();
  await expect(page.getByText('Verified Entity recovery time', { exact: true })).toBeVisible();
  await expect(page.getByText(/Grounded entity added to the model's proposed query/)).toContainText(
    'recovery time',
  );
});

test('invalid file types stay client-side and incorrect tokens are rejected by the server', async ({
  page,
}) => {
  await manage(page);
  let writes = 0;
  page.on('request', (request) => {
    if (request.method() === 'POST' && request.url().endsWith('/api/documents')) writes += 1;
  });
  await page.getByLabel('Add a document').setInputFiles({
    name: 'unsupported.exe',
    mimeType: 'application/octet-stream',
    buffer: Buffer.from('unsupported'),
  });
  await page.getByRole('button', { name: 'Upload document', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('PDF, DOCX, or TXT');
  expect(writes).toBe(0);
  await page.getByLabel('Demo admin token').fill('incorrect-fixture-token');
  await page.getByLabel('Add a document').setInputFiles({
    name: 'valid.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('A valid fictional source.'),
  });
  await page.getByRole('button', { name: 'Upload document', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('valid demo admin bearer token');
  expect(writes).toBe(1);
  await page.getByLabel('Demo admin token').fill(token);
  await page.getByRole('button', { name: 'Upload document', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
});

test('cursor pagination moves forwards and backwards without loading the whole corpus', async ({
  page,
  request,
}) => {
  for (let i = 0; i < 21; i++)
    await createSource(request, `Pagination fictional source ${i}.`, `source-${i}.txt`);
  await page
    .getByRole('navigation')
    .getByRole('button', { name: 'Documents', exact: true })
    .click();
  await page.getByRole('button', { name: 'Refresh sources' }).click();
  const rows = page.getByRole('list', { name: 'Stored documents' }).getByRole('listitem');
  await expect(rows).toHaveCount(20);
  await page.getByRole('button', { name: 'Next page' }).click();
  await expect(rows).toHaveCount(1);
  await expect(page.getByText('Page 2 · 1 sources shown')).toBeVisible();
  await page.getByRole('button', { name: 'Previous page' }).click();
  await expect(rows).toHaveCount(20);
});

test('late source responses cannot replace the newly opened document', async ({
  page,
  request,
}) => {
  const first = await createSource(request, 'First fictional source body.', 'first-source.txt');
  await createSource(request, 'Second fictional source body.', 'second-source.txt');
  const old = await request.get(`/api/documents/${first.document_id}`);
  const oldBody = await old.json();
  let finish = () => {};
  const gate = new Promise<void>((resolve) => {
    finish = resolve;
  });
  let seen = false;
  await page.route(`**/api/documents/${first.document_id}`, async (route) => {
    seen = true;
    await gate;
    await route.fulfill({ json: oldBody, headers: { ETag: old.headers().etag } }).catch(() => {});
  });
  await page
    .getByRole('navigation')
    .getByRole('button', { name: 'Documents', exact: true })
    .click();
  await page.getByRole('button', { name: 'Refresh sources' }).click();
  await page.getByRole('button', { name: /first-source\.txt/ }).click();
  await expect.poll(() => seen).toBeTruthy();
  await page.getByRole('button', { name: 'Close source' }).click();
  await page.getByRole('button', { name: /second-source\.txt/ }).click();
  await expect(page.getByRole('region', { name: 'Canonical source text' })).toContainText(
    'Second fictional source body.',
  );
  finish();
  await expect(
    page.getByRole('dialog').getByRole('heading', { name: 'second-source.txt', exact: true }),
  ).toBeVisible();
});
