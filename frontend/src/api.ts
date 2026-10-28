import type { DocumentPage, DocumentView, Investigation, MutationResult } from './types.ts';

export class ApiError extends Error {
  status: number;
  retryAfter: string | null;
  constructor(status: number, message: string, retryAfter: string | null = null) {
    super(message);
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

function detailMessage(payload: unknown): string | null {
  if (!payload || typeof payload !== 'object' || !('detail' in payload)) return null;
  const detail = payload.detail;
  if (typeof detail === 'string') return detail;
  if (
    detail &&
    typeof detail === 'object' &&
    'message' in detail &&
    typeof detail.message === 'string'
  ) {
    return detail.message;
  }
  return null;
}

async function request<T>(path: string, options: RequestInit = {}) {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      ...options,
      signal: options.signal ?? AbortSignal.timeout(120_000),
      cache: 'no-store',
    });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ApiError(
      0,
      'Cannot reach the API. Check that the Python server is running, then try again.',
    );
  }
  if (response.status === 204) return { data: undefined as T, etag: null };
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const fallback =
      response.status === 429
        ? 'The demo is busy. Please try again shortly.'
        : `The API returned HTTP ${response.status}.`;
    throw new ApiError(
      response.status,
      detailMessage(data) ?? fallback,
      response.headers.get('Retry-After'),
    );
  }
  if (!data || typeof data !== 'object')
    throw new ApiError(502, 'The API returned an unexpected response.');
  // Static contracts mirror the Python models; this is the one JSON-to-TypeScript boundary.
  // Hosting proxies can weaken the representation ETag when compressing JSON.
  // Keep the server's exact revision precondition independently of that representation.
  return {
    data: data as T,
    etag: response.headers.get('X-Document-ETag') ?? response.headers.get('ETag'),
  };
}

export const api = {
  list: (cursor: string | null, signal: AbortSignal) =>
    request<DocumentPage>(
      `/documents?limit=20${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`,
      { signal },
    ),
  read: (id: string, signal?: AbortSignal) =>
    request<DocumentView>(`/documents/${encodeURIComponent(id)}`, { signal }),
  upload: (file: File, token: string) => {
    const body = new FormData();
    body.append('file', file);
    return request<MutationResult>('/documents', {
      method: 'POST',
      body,
      headers: { Authorization: `Bearer ${token}` },
    });
  },
  replace: (id: string, file: File, token: string, etag: string) => {
    const body = new FormData();
    body.append('file', file);
    return request<MutationResult>(`/documents/${encodeURIComponent(id)}`, {
      method: 'PUT',
      body,
      headers: { Authorization: `Bearer ${token}`, 'If-Match': etag },
    });
  },
  delete: (id: string, token: string, etag: string) =>
    request<void>(`/documents/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}`, 'If-Match': etag },
    }),
  investigate: (question: string, signal: AbortSignal) =>
    request<Investigation>('/investigations', {
      method: 'POST',
      signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    }),
};

export function errorMessage(error: unknown, mutation = false) {
  const message =
    error instanceof Error ? error.message : 'Something went wrong. Please try again.';
  if (mutation && error instanceof ApiError && (error.status === 0 || error.status >= 500)) {
    return `${message} The write may have reached the server. Refresh sources before retrying.`;
  }
  if (error instanceof ApiError && error.status === 412)
    return 'This source changed. Reload it and review the current revision before trying again.';
  if (error instanceof ApiError && error.status === 429 && error.retryAfter)
    return `${message} Retry after ${error.retryAfter} seconds.`;
  return message;
}

export function validateFile(file: File | null): string {
  if (!file) return 'Choose a PDF, DOCX, or TXT file.';
  if (!/\.(pdf|docx|txt)$/i.test(file.name)) return 'Choose a PDF, DOCX, or TXT file.';
  if (file.size === 0) return 'The file is empty.';
  if (file.size > 5_000_000) return 'Files must be 5 MB or smaller (5,000,000 bytes).';
  return '';
}
