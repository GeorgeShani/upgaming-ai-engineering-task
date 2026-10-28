import { test } from 'node:test';
import assert from 'node:assert/strict';
import { api, ApiError, errorMessage, validateFile } from '../../src/api.ts';
import { sourceExcerpt } from '../../src/sourceText.ts';

test('mutations send the exact ETag and token; public reads send no authorization', async (t) => {
  const calls = [];
  t.mock.method(globalThis, 'fetch', async (url, init) => {
    calls.push({ url, init });
    return init.method === 'DELETE'
      ? new Response(null, { status: 204 })
      : Response.json({ document_id: 'one' }, { headers: { ETag: '"revision-two"' } });
  });
  const file = new File(['source'], 'source.txt');
  await api.replace('one', file, 'fixture-token', '"revision-one"');
  assert.equal(calls[0].init.headers['If-Match'], '"revision-one"');
  assert.equal(calls[0].init.headers.Authorization, 'Bearer fixture-token');
  assert.equal(new Headers(calls[0].init.headers).get('Content-Type'), null);
  assert.ok(calls[0].init.body instanceof FormData);
  const read = await api.read('one');
  assert.equal(read.etag, '"revision-two"');
  assert.equal(new Headers(calls[1].init.headers).get('Authorization'), null);
  await api.delete('one', 'fixture-token', read.etag);
  assert.equal(calls[2].init.headers['If-Match'], '"revision-two"');
});

test('API errors stay errors and expose useful stale/rate-limit recovery', async (t) => {
  t.mock.method(globalThis, 'fetch', async () =>
    Response.json(
      { detail: 'Demo busy.' },
      {
        status: 429,
        headers: { 'Retry-After': '60' },
      },
    ),
  );
  await assert.rejects(api.investigate('Question?', new AbortController().signal), (error) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 429);
    assert.match(errorMessage(error), /60 seconds/);
    return true;
  });
  assert.match(errorMessage(new ApiError(412, 'Stale')), /Reload/);
  assert.match(errorMessage(new ApiError(503, 'Unavailable'), true), /may have reached/);
});

test('a proxy-weakened representation ETag does not corrupt the revision precondition', async (t) => {
  const calls = [];
  t.mock.method(globalThis, 'fetch', async (url, init) => {
    calls.push(init);
    return init.method === 'DELETE'
      ? new Response(null, { status: 204 })
      : Response.json(
          { document_id: 'one' },
          {
            headers: { ETag: 'W/"compressed-representation"', 'X-Document-ETag': '"revision-one"' },
          },
        );
  });
  const read = await api.read('one');
  assert.equal(read.etag, '"revision-one"');
  await api.delete('one', 'fixture-token', read.etag);
  assert.equal(calls[1].headers['If-Match'], '"revision-one"');
});

test('file validation agrees with the 5,000,000 byte server boundary', () => {
  assert.equal(validateFile(new File([new Uint8Array(5_000_000)], 'source.PDF')), '');
  assert.match(validateFile(new File([new Uint8Array(5_000_001)], 'source.txt')), /5 MB/);
  assert.match(validateFile(new File(['source'], 'source.exe')), /PDF, DOCX, or TXT/);
  assert.match(validateFile(new File([], 'empty.txt')), /empty/);
});

test('source highlights use Python code-point offsets, including emoji before the quote', () => {
  const excerpt = sourceExcerpt('🚀 launch. Georgian ქართული evidence. Done.', {
    start: 10,
    end: 36,
    text: 'Georgian ქართული evidence.',
  });
  assert.equal(excerpt.matches, true);
  assert.equal(excerpt.highlight, 'Georgian ქართული evidence.');
  assert.equal(
    excerpt.before + excerpt.highlight + excerpt.after,
    '🚀 launch. Georgian ქართული evidence. Done.',
  );
  assert.equal(sourceExcerpt('changed text', { start: 0, end: 3, text: 'old' }).matches, false);
});
