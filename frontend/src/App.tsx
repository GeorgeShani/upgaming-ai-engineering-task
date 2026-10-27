import { useEffect, useState } from 'react';

type DependencyHealth = {
  status: 'unconfigured' | 'reachable' | 'unavailable';
  message: string;
};

type HealthReport = {
  status: 'ready' | 'degraded';
  app: 'running';
  dependencies: Record<string, DependencyHealth>;
};

const labels = { unconfigured: 'Needs setup', reachable: 'Connected', unavailable: 'Unavailable' };

export function App() {
  const [health, setHealth] = useState<HealthReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function refresh(signal?: AbortSignal) {
    setLoading(true);
    setError('');
    try {
      const response = await fetch('/api/health', { signal });
      if (!response.ok && response.status !== 503) {
        throw new Error(`Server returned HTTP ${response.status}.`);
      }
      const report: HealthReport = await response.json();
      setHealth(report);
    } catch (cause) {
      if (signal?.aborted) return;
      setError('Could not check the API. Make sure the Python server is running, then retry.');
      setHealth(null);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }

  useEffect(() => {
    const controller = new AbortController();
    void refresh(controller.signal);
    return () => controller.abort();
  }, []);

  return (
    <main>
      <header>
        <p className="eyebrow">APPLIED AI / SESSION 01</p>
        <h1>Investigation Engine</h1>
        <p className="intro">Find connections. Follow the evidence. Know where an answer comes from.</p>
      </header>

      <section aria-labelledby="setup-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">FOUNDATION CHECK</p>
            <h2 id="setup-title">Connect the pieces</h2>
          </div>
          <button type="button" onClick={() => void refresh()} disabled={loading}>
            {loading ? 'Checking…' : 'Check connections'}
          </button>
        </div>
        <div role="status" aria-live="polite" aria-busy={loading}>
          {error && <p className="error">{error}</p>}
          {loading && <p>Checking the Python API and configured services…</p>}
          {!loading && health && (
            <>
              <p className="summary">
                {health.status === 'ready'
                  ? 'API running. External access checks passed.'
                  : 'API running. External services still need attention.'}
              </p>
              <dl>
                <div className="service">
                  <dt>Python API</dt><dd><strong>Running</strong></dd>
                </div>
                {Object.entries(health.dependencies).map(([name, dependency]) => (
                  <div className="service" key={name}>
                    <dt>{name === 'openai' ? 'OpenAI' : 'Qdrant'}</dt>
                    <dd>
                      <strong>{labels[dependency.status]}</strong>
                      <span>{dependency.message}</span>
                    </dd>
                  </div>
                ))}
              </dl>
            </>
          )}
        </div>
        <p className="footnote">
          These checks read service metadata. They do not generate answers, create embeddings,
          or prove that indexing works. Add credentials only to the server environment.
        </p>
      </section>

      <aside aria-labelledby="next-title">
        <p className="eyebrow">ONE SLICE AT A TIME</p>
        <h2 id="next-title">First, understand the connection.</h2>
        <p>
          This page calls the Python API. The API checks external services and returns their
          status. Your browser never receives the API keys.
        </p>
        <p>Document management, retrieval, and investigations arrive in the next sessions.</p>
      </aside>
      <footer>Session 01 · Foundation · See the engineering journal for the walkthrough.</footer>
    </main>
  );
}
