// Opt-in paid check. No traces, video, request logging, or credential-bearing test reports.
import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const token = process.env.LIVE_DEMO_ADMIN_TOKEN;
const base = new URL(process.env.LIVE_UI_BASE_URL ?? 'http://127.0.0.1:4173');
if (!token) throw new Error('Run this check through scripts/verify_browser_workflow.py.');
if (!['127.0.0.1', 'localhost'].includes(base.hostname))
  throw new Error('Live smoke is limited to localhost.');
const artifact = new URL('../../artifacts/', import.meta.url);
await mkdir(artifact, { recursive: true });
const caseId = `UI-${randomUUID()}`;
const text = `Fictional browser smoke case ${caseId}. The payment-router recovery time documented for case ${caseId} was 17 minutes.`;
const browser = await chromium.launch({ channel: 'chromium' });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
page.setDefaultTimeout(20_000);
const runtimeErrors = [];
page.on('pageerror', (error) => runtimeErrors.push(error.message));
let createdId = null;
let deleted = false;
try {
  await page.goto(base.href);
  await page
    .getByRole('navigation')
    .getByRole('button', { name: 'Documents', exact: true })
    .click();
  await page.locator('.access-box > summary').click();
  await page.getByLabel('Demo admin token', { exact: true }).fill(token);
  await page.getByLabel('Add a document', { exact: true }).setInputFiles({
    name: `${caseId}.txt`,
    mimeType: 'text/plain',
    buffer: Buffer.from(text),
  });
  const uploadResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/documents') && response.request().method() === 'POST',
    { timeout: 120_000 },
  );
  await page.getByRole('button', { name: 'Upload document', exact: true }).click();
  const upload = await uploadResponse;
  assert.equal(
    upload.status(),
    201,
    'Only a newly created smoke source may be changed or deleted.',
  );
  const document = (await upload.json()).document;
  createdId = document.document_id;
  assert.equal(document.index_status, 'ready');
  await page
    .getByRole('region', { name: 'Canonical source text' })
    .filter({ hasText: caseId })
    .waitFor();
  await page.getByRole('button', { name: 'Close source' }).click();
  await page
    .getByRole('navigation')
    .getByRole('button', { name: 'Investigate', exact: true })
    .click();
  await page
    .getByLabel('Your question')
    .fill(`What recovery time was documented for fictional browser smoke case ${caseId}?`);
  const investigationResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/investigations') && response.request().method() === 'POST',
    { timeout: 110_000 },
  );
  await page.getByRole('main').getByRole('button', { name: 'Investigate', exact: true }).click();
  const answered = await investigationResponse;
  if (answered.status() !== 200) {
    const failure = await answered.json();
    await page.getByRole('alert').waitFor();
    await page.screenshot({
      path: fileURLToPath(new URL('slice-7-live-error.png', artifact)),
      fullPage: true,
    });
    const detail = String(failure.detail ?? 'Unknown API failure').replaceAll(token, '[redacted]');
    await writeFile(
      new URL('browser-live-failure.json', artifact),
      JSON.stringify(
        {
          scope: 'live browser development failure',
          case_id: caseId,
          http_status: answered.status(),
          detail,
          displayed_as_error: true,
          created_document_id: createdId,
        },
        null,
        2,
      ) + '\n',
    );
    throw new Error(`Live investigation HTTP ${answered.status()}: ${detail}`);
  }
  assert.equal(answered.status(), 200, 'The live investigation must succeed.');
  const result = await answered.json();
  assert.equal(result.status, 'answered');
  assert.match(result.answer, /17 minutes/);
  await page.getByText('Answered', { exact: true }).waitFor();
  const hit = result.evidence.find((evidence) => evidence.document_id === createdId);
  assert.ok(hit, 'The newly uploaded source must actually be retrieved.');
  assert.ok(
    result.claims.some((claim) =>
      claim.citations.some((citation) => citation.evidence_id === hit.evidence_id),
    ),
  );
  await page
    .getByRole('button', { name: new RegExp(`Open citation ${hit.evidence_id}:`) })
    .first()
    .click();
  const canonical = page.getByRole('region', { name: 'Canonical source text' });
  await canonical.locator('mark').waitFor();
  assert.ok((await canonical.textContent()).includes('17 minutes'));
  await page.screenshot({ path: fileURLToPath(new URL('slice-7-live-citation.png', artifact)) });
  await page.keyboard.press('Escape');
  await page.locator('details.search-trace > summary').click();
  await page.getByText('Round 2', { exact: true }).waitFor();
  await page.screenshot({
    path: fileURLToPath(new URL('slice-7-live-answer.png', artifact)),
    fullPage: true,
  });
  await page
    .getByRole('navigation')
    .getByRole('button', { name: 'Documents', exact: true })
    .click();
  await page.getByRole('button', { name: /Open last uploaded source:/ }).click();
  await page.getByRole('region', { name: 'Canonical source text' }).waitFor();
  await page.getByRole('button', { name: 'Delete document', exact: true }).click();
  const deleteResponse = page.waitForResponse(
    (response) =>
      response.url().includes(`/api/documents/${createdId}`) &&
      response.request().method() === 'DELETE',
  );
  await page.getByRole('button', { name: 'Confirm delete' }).click();
  assert.equal((await deleteResponse).status(), 204);
  deleted = true;
  assert.equal(
    (await context.request.get(new URL(`/api/documents/${createdId}`, base).href)).status(),
    404,
  );
  assert.deepEqual(runtimeErrors, []);
  const report = {
    scope: 'one live browser smoke, not final evaluation',
    source_case: caseId,
    created_document_id: createdId,
    upload_http: upload.status(),
    answer_status: result.status,
    answer: result.answer,
    source_citation_checked: true,
    trace_opened: true,
    deleted: true,
    deleted_source_http: 404,
    browser_runtime_errors: runtimeErrors,
    configuration: result.configuration,
    execution: result.execution,
    usage: result.usage,
    latency_ms: result.latency_ms,
  };
  await writeFile(
    new URL('browser-live-verification.json', artifact),
    JSON.stringify(report, null, 2) + '\n',
  );
  console.log(JSON.stringify(report, null, 2));
} catch (error) {
  console.error(String(error).replaceAll(token, '[redacted]'));
  process.exitCode = 1;
} finally {
  if (createdId && !deleted) {
    try {
      const current = await context.request.get(new URL(`/api/documents/${createdId}`, base).href);
      if (current.status() === 200) {
        const removed = await context.request.delete(
          new URL(`/api/documents/${createdId}`, base).href,
          {
            headers: { Authorization: `Bearer ${token}`, 'If-Match': current.headers().etag },
          },
        );
        console.log('Cleanup of newly created smoke source:', removed.status());
      }
    } catch {
      console.error('Could not confirm cleanup of the newly created smoke source:', createdId);
    }
  }
  await browser.close();
}
