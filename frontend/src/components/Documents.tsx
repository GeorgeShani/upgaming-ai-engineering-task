import { useEffect, useRef, useState } from 'react';
import { api, errorMessage, validateFile } from '../api.ts';
import type { DocumentPage, DocumentSummary, SourceTarget } from '../types.ts';
import { Icon } from './Icon.tsx';

type Props = {
  token: string;
  setToken: (token: string) => void;
  corpusVersion: number;
  onChanged: (message: string) => void;
  onOpen: (source: SourceTarget) => void;
  removedId: string | null;
};

export function Documents({ token, setToken, corpusVersion, onChanged, onOpen, removedId }: Props) {
  const [page, setPage] = useState<DocumentPage | null>(null);
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [uploadError, setUploadError] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [recent, setRecent] = useState<DocumentSummary | null>(null);
  const uploadForm = useRef<HTMLFormElement>(null);
  const cursor = cursors.at(-1) ?? null;
  useEffect(() => {
    setCursors([null]);
  }, [corpusVersion]);
  useEffect(() => {
    if (removedId) setRecent((current) => (current?.document_id === removedId ? null : current));
  }, [removedId]);
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setLoading(true);
    setError('');
    setPage(null);
    void api
      .list(cursor, controller.signal)
      .then(({ data }) => {
        if (active) setPage(data);
      })
      .catch((cause) => {
        if (active) setError(errorMessage(cause));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [cursor, refresh, corpusVersion]);

  async function upload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const invalid = validateFile(file);
    if (invalid || !file) {
      setUploadError(invalid);
      return;
    }
    if (!token.trim() || uploading) return;
    setUploading(true);
    setUploadError('');
    try {
      const { data } = await api.upload(file, token.trim());
      setRecent(data.document);
      setFile(null);
      uploadForm.current?.reset();
      setCursors([null]);
      onChanged(
        data.duplicate
          ? `Already stored: ${data.document.title}. Opened the existing source.`
          : `Uploaded and stored: ${data.document.title}.`,
      );
      onOpen({ id: data.document.document_id, title: data.document.title, manage: true });
    } catch (cause) {
      setUploadError(errorMessage(cause, true));
    } finally {
      setUploading(false);
    }
  }

  return (
    <section aria-labelledby="documents-title" className="workspace-section">
      <div className="section-heading">
        <div>
          <h2 id="documents-title" tabIndex={-1}>
            Documents
          </h2>
        </div>
        <button
          type="button"
          className="secondary"
          onClick={() => setRefresh((n) => n + 1)}
          disabled={loading}
        >
          Refresh sources
        </button>
      </div>
      <p className="muted">
        Inspect the extracted text, add a source, or manage its current revision.
      </p>
      <div className="document-tools">
        <details className="access-box">
          <summary>
            Manage access{' '}
            <span className="muted">
              {token ? '· Token entered' : '· Read-only until a token is entered'}
            </span>
          </summary>
          <div className="access-controls">
            <label htmlFor="admin-token">Demo admin token</label>
            <div className="input-action">
              <input
                id="admin-token"
                type="password"
                autoComplete="off"
                spellCheck={false}
                value={token}
                onChange={(event) => setToken(event.target.value)}
                aria-describedby="token-help"
              />
              <button
                type="button"
                className="secondary"
                disabled={!token || uploading}
                onClick={() => setToken('')}
              >
                Clear token
              </button>
            </div>
            <p id="token-help" className="muted small">
              Kept in memory for this page only. The server validates it on every write. Reading and
              asking questions need no token.
            </p>
          </div>
        </details>
        <form ref={uploadForm} onSubmit={upload} className="upload-form" aria-busy={uploading}>
          <label htmlFor="upload-file">Add a document</label>
          <div className="input-action">
            <input
              id="upload-file"
              type="file"
              accept=".pdf,.docx,.txt"
              disabled={uploading}
              aria-describedby="upload-help"
              onChange={(event) => {
                const chosen = event.target.files?.[0] ?? null;
                setFile(chosen);
                setUploadError(chosen ? validateFile(chosen) : '');
              }}
            />
            <button type="submit" disabled={uploading || !token.trim() || !file}>
              {uploading ? 'Uploading and indexing…' : 'Upload document'}
            </button>
          </div>
          <p id="upload-help" className="muted small">
            PDF, DOCX, or UTF-8 TXT · up to 5 MB · exact duplicates reuse the stored source. Use
            fictional or public documents in this shared demo.
          </p>
          {!token && (
            <p className="muted small">
              Enter the demo admin token under Manage access to upload, replace, or delete.
            </p>
          )}
          {uploadError && (
            <p role="alert" className="error">
              {uploadError}
            </p>
          )}
        </form>
      </div>
      {recent && (
        <div className="recent-source">
          <p className="muted small">Last upload · quick access across views</p>
          <button
            type="button"
            className="text-button"
            onClick={() => onOpen({ id: recent.document_id, title: recent.title, manage: true })}
          >
            Open last uploaded source: {recent.title}
          </button>
        </div>
      )}
      <div aria-busy={loading}>
        {loading && (
          <p role="status" className="empty-state loading-sources">
            Loading sources…
          </p>
        )}
        {error && (
          <div className="error-panel" role="alert">
            <p>{error}</p>
            <button type="button" className="secondary" onClick={() => setRefresh((n) => n + 1)}>
              Retry loading sources
            </button>
          </div>
        )}
        {page && page.items.length === 0 && (
          <div className="empty-state">
            <h3>No sources on this page</h3>
            <p>Add a document to start building your evidence library.</p>
          </div>
        )}
        {page && page.items.length > 0 && (
          <ul className="document-list" aria-label="Stored documents">
            {page.items.map((document) => (
              <li key={document.document_id}>
                <button
                  className="document-row"
                  type="button"
                  onClick={() =>
                    onOpen({ id: document.document_id, title: document.title, manage: true })
                  }
                >
                  <span className="document-label">
                    <strong>{document.title}</strong>
                    <span className="muted small">{document.filename}</span>
                  </span>
                  <span className="document-tags">
                    <span className="format-label">{document.format.toUpperCase()}</span>
                    <span className={`badge ${document.index_status === 'ready' ? 'ready' : ''}`}>
                      {document.index_status === 'ready' ? 'Searchable' : 'Index pending'}
                    </span>
                    <Icon name="arrow" />
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="pagination" aria-label="Document pagination">
        <button
          type="button"
          className="secondary"
          disabled={loading || cursors.length === 1}
          onClick={() => setCursors((old) => old.slice(0, -1))}
        >
          Previous page
        </button>
        <span className="muted small">
          Page {cursors.length}
          {page ? ` · ${page.items.length} sources shown` : ''}
        </span>
        <button
          type="button"
          className="secondary"
          disabled={loading || !page?.next_cursor}
          onClick={() => {
            if (page?.next_cursor) setCursors((old) => [...old, page.next_cursor]);
          }}
        >
          Next page
        </button>
      </div>
    </section>
  );
}
