import { useEffect, useMemo, useRef, useState } from 'react';
import { api, ApiError, errorMessage, validateFile } from '../api.ts';
import { sourceExcerpt } from '../sourceText.ts';
import type { DocumentView, SourceTarget } from '../types.ts';

type Props = {
  target: SourceTarget | null;
  token: string;
  onClose: () => void;
  onClosed: () => void;
  onChanged: (message: string, removedId?: string) => void;
};

export function SourceDialog({ target, token, onClose, onClosed, onChanged }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const replaceForm = useRef<HTMLFormElement>(null);
  const [source, setSource] = useState<{ data: DocumentView; etag: string | null } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [refresh, setRefresh] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [needsReload, setNeedsReload] = useState(false);
  const [full, setFull] = useState(false);

  useEffect(() => {
    if (target) {
      if (!dialog.current?.open) dialog.current?.showModal();
    } else dialog.current?.close();
  }, [target]);
  useEffect(() => {
    setFile(null);
    replaceForm.current?.reset();
    setNotice('');
    setFull(false);
    setConfirmDelete(false);
  }, [target?.id]);
  useEffect(() => {
    if (!target) return;
    const controller = new AbortController();
    let active = true;
    setSource(null);
    setLoading(true);
    setError('');
    setNeedsReload(false);
    setConfirmDelete(false);
    setFile(null);
    replaceForm.current?.reset();
    void api
      .read(target.id, controller.signal)
      .then((result) => {
        if (active) setSource(result);
      })
      .catch((cause) => {
        if (active)
          setError(
            cause instanceof ApiError && cause.status === 404
              ? 'This source is no longer available. It may have been deleted. Retrieved evidence below remains a snapshot.'
              : errorMessage(cause),
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [target?.id, refresh]);

  const current = source?.data.document_id === target?.id ? source : null;
  const changed = Boolean(
    target?.evidence && current && current.data.revision_id !== target.evidence.revision_id,
  );
  const excerpt = useMemo(
    () => sourceExcerpt(current?.data.text ?? '', changed ? undefined : target?.evidence, full),
    [current?.data.text, target?.evidence, changed, full],
  );
  const editable = Boolean(
    target?.manage && token.trim() && current?.etag && !needsReload && !loading && !busy,
  );

  async function replace(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const invalid = validateFile(file);
    if (invalid || !file) {
      setError(invalid);
      return;
    }
    if (!editable || !current?.etag || !target) return;
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const { data } = await api.replace(target.id, file, token.trim(), current.etag);
      const message = data.duplicate
        ? 'The source already contains this text.'
        : 'Replacement saved. The new revision is active.';
      setNotice(message);
      onChanged(message);
      setFile(null);
      replaceForm.current?.reset();
      setSource(null);
      setRefresh((n) => n + 1);
    } catch (cause) {
      setError(errorMessage(cause, true));
      if (
        cause instanceof ApiError &&
        (cause.status === 412 || cause.status === 0 || cause.status >= 500)
      )
        setNeedsReload(true);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!editable || !current?.etag || !target) return;
    setBusy(true);
    setError('');
    try {
      await api.delete(target.id, token.trim(), current.etag);
      onChanged(`Deleted from retrieval: ${current.data.title}.`, target.id);
      onClose();
    } catch (cause) {
      setError(errorMessage(cause, true));
      if (
        cause instanceof ApiError &&
        (cause.status === 412 || cause.status === 0 || cause.status >= 500)
      )
        setNeedsReload(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <dialog
      ref={dialog}
      className="source-dialog"
      aria-labelledby="source-title"
      onClose={onClosed}
      onCancel={(event) => {
        if (busy) event.preventDefault();
        else onClose();
      }}
    >
      <div className="dialog-header">
        <div>
          <p className="eyebrow">{target?.evidence ? 'EVIDENCE / SOURCE' : 'DOCUMENT'}</p>
          <h2 id="source-title">{current?.data.title ?? target?.title ?? 'Source'}</h2>
        </div>
        <button type="button" className="secondary" onClick={onClose} disabled={busy}>
          Close source
        </button>
      </div>
      <div className="dialog-body">
        {target?.evidence && (
          <section className="evidence-snapshot" aria-label="Retrieved evidence">
            <h3>{target.evidence.evidence_id} · Retrieved evidence</h3>
            <p className="muted small">
              {target.evidence.locations
                .map((location) => `${location.kind.replace('_', ' ')} ${location.number}`)
                .join(' · ')}
            </p>
            <blockquote>{target.quote ?? target.evidence.text}</blockquote>
            <details>
              <summary>Entire retrieved chunk</summary>
              <p className="source-text">{target.evidence.text}</p>
            </details>
          </section>
        )}
        {loading && <p role="status">Loading canonical source…</p>}
        {notice && (
          <p role="status" className="notice">
            {notice}
          </p>
        )}
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        {!loading && (
          <button
            type="button"
            className="secondary"
            disabled={busy}
            onClick={() => setRefresh((n) => n + 1)}
          >
            Reload source
          </button>
        )}
        {changed && (
          <p className="warning" role="status">
            This source has a newer revision. The evidence above belongs to the earlier retrieved
            revision; the current text below is different.
          </p>
        )}
        {current && (
          <>
            <dl className="source-metadata">
              <div className="metadata-row">
                <dt>File</dt>
                <dd>
                  {current.data.filename} · {current.data.format.toUpperCase()}
                </dd>
              </div>
              <div className="metadata-row">
                <dt>Search status</dt>
                <dd>{current.data.index_status === 'ready' ? 'Searchable' : 'Index pending'}</dd>
              </div>
              <div className="metadata-row">
                <dt>Document ID</dt>
                <dd>
                  <code>{current.data.document_id}</code>
                </dd>
              </div>
              <div className="metadata-row">
                <dt>Revision</dt>
                <dd>
                  <code>{current.data.revision_id}</code>
                </dd>
              </div>
              {Object.entries(current.data.metadata).map(([name, value]) => (
                <div className="metadata-row" key={name}>
                  <dt>{name.replaceAll('_', ' ')}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
            <section aria-label="Canonical source text" className="canonical-source">
              <h3>Canonical source text</h3>
              <p className="muted small">
                Characters {excerpt.start + 1}–{excerpt.end} of {excerpt.total}
                {excerpt.matches ? ' · Highlight matches the retrieved chunk' : ''}
              </p>
              <p className="source-text">
                {excerpt.before}
                {excerpt.highlight && <mark>{excerpt.highlight}</mark>}
                {excerpt.after}
              </p>
              {excerpt.truncated && (
                <button type="button" className="secondary" onClick={() => setFull(true)}>
                  Show full source text
                </button>
              )}
              {full && excerpt.total > 8000 && (
                <button type="button" className="secondary" onClick={() => setFull(false)}>
                  Show excerpt
                </button>
              )}
            </section>
            {target?.manage && (
              <section className="source-actions" aria-labelledby="manage-source-title">
                <h3 id="manage-source-title">Manage this source</h3>
                {!token && (
                  <p className="muted">
                    Enter your token in Manage access on the Documents page to make changes.
                  </p>
                )}
                {!current.etag && (
                  <p className="error">
                    No revision tag was returned. Reload before making changes.
                  </p>
                )}
                {needsReload && <p className="warning">Reload the source before another write.</p>}
                <form onSubmit={replace} ref={replaceForm} aria-busy={busy}>
                  <label htmlFor="replace-file">Replacement file</label>
                  <input
                    id="replace-file"
                    type="file"
                    accept=".pdf,.docx,.txt"
                    disabled={!editable}
                    onChange={(event) => {
                      setFile(event.target.files?.[0] ?? null);
                      setConfirmDelete(false);
                    }}
                  />
                  <p className="muted small">
                    PDF, DOCX, or UTF-8 TXT · up to 5 MB. The document keeps its ID and receives a
                    new revision.
                  </p>
                  <button type="submit" disabled={!editable || !file}>
                    {busy ? 'Saving…' : 'Replace document'}
                  </button>
                </form>
                <div className="delete-area">
                  {confirmDelete ? (
                    <>
                      <p>
                        Delete this source from retrieval? Earlier answers keep their evidence
                        snapshots. Stored history is retained.
                      </p>
                      <div className="button-row">
                        <button
                          type="button"
                          className="danger"
                          disabled={!editable}
                          onClick={() => void remove()}
                        >
                          Confirm delete
                        </button>
                        <button
                          type="button"
                          className="secondary"
                          disabled={busy}
                          onClick={() => setConfirmDelete(false)}
                        >
                          Keep source
                        </button>
                      </div>
                    </>
                  ) : (
                    <button
                      type="button"
                      className="danger-outline"
                      disabled={!editable}
                      onClick={() => setConfirmDelete(true)}
                    >
                      Delete document
                    </button>
                  )}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </dialog>
  );
}
