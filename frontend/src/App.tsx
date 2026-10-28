import { useRef, useState } from 'react';
import { ConnectionStatus } from './components/ConnectionStatus.tsx';
import { Documents } from './components/Documents.tsx';
import { InvestigationPanel } from './components/InvestigationPanel.tsx';
import { SourceDialog } from './components/SourceDialog.tsx';
import type { SourceTarget } from './types.ts';

export function App() {
  const [view, setView] = useState<'investigate' | 'documents'>('investigate');
  const [target, setTarget] = useState<SourceTarget | null>(null);
  const [token, setToken] = useState('');
  const [corpusVersion, setCorpusVersion] = useState(0);
  const [notice, setNotice] = useState('');
  const [removedId, setRemovedId] = useState<string | null>(null);
  const opener = useRef<HTMLElement | null>(null);
  function openSource(source: SourceTarget) {
    opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setTarget(source);
  }
  function closeSource() {
    setTarget(null);
  }
  function restoreSourceFocus() {
    // Native close fires after the modal releases its focus trap.
    if (opener.current?.isConnected) opener.current.focus();
    else document.getElementById('documents-nav')?.focus();
  }
  function changed(message: string, removed?: string) {
    if (removed) opener.current = null;
    setNotice(message);
    setRemovedId(removed ?? null);
    setCorpusVersion((n) => n + 1);
  }
  return (
    <>
      <a className="skip-link" href="#workspace">
        Skip to workspace
      </a>
      <div className="app-shell">
        <header className="app-header">
          <div>
            <p className="eyebrow">APPLIED AI / INVESTIGATION WORKSPACE</p>
            <h1>Investigation Engine</h1>
            <p className="intro">Ask a question. Follow the sources.</p>
          </div>
          <ConnectionStatus />
        </header>
        <nav aria-label="Workspace views" className="view-navigation">
          <button
            type="button"
            aria-pressed={view === 'investigate'}
            onClick={() => setView('investigate')}
          >
            Investigate
          </button>
          <button
            id="documents-nav"
            type="button"
            aria-pressed={view === 'documents'}
            onClick={() => setView('documents')}
          >
            Documents
          </button>
        </nav>
        <main id="workspace">
          {notice && (
            <p role="status" className="operation-notice">
              {notice}
            </p>
          )}
          <div hidden={view !== 'investigate'}>
            <InvestigationPanel corpusVersion={corpusVersion} onOpen={openSource} />
          </div>
          <div hidden={view !== 'documents'}>
            <Documents
              token={token}
              setToken={setToken}
              corpusVersion={corpusVersion}
              onChanged={changed}
              onOpen={openSource}
              removedId={removedId}
            />
          </div>
        </main>
        <footer>
          Evidence from a shared document collection. Source text is public; original files are not
          retained.
        </footer>
      </div>
      <SourceDialog
        target={target}
        token={token}
        onClose={closeSource}
        onClosed={restoreSourceFocus}
        onChanged={changed}
      />
    </>
  );
}
