import { useEffect, useState } from 'react';

type Health = {
  status: 'ready' | 'degraded';
  dependencies: Record<
    string,
    { status: 'unconfigured' | 'reachable' | 'unavailable'; message: string }
  >;
};
const labels = { unconfigured: 'Needs setup', reachable: 'Connected', unavailable: 'Unavailable' };

export function ConnectionStatus() {
  const [health, setHealth] = useState<Health | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setLoading(true);
    setError('');
    void (async () => {
      try {
        const response = await fetch('/api/health', {
          signal: controller.signal,
          cache: 'no-store',
        });
        if (!response.ok && response.status !== 503) throw new Error('Health request failed');
        const report: Health = await response.json();
        if (!report.dependencies) throw new Error('Unexpected health response');
        if (active) setHealth(report);
      } catch {
        if (active) {
          setHealth(null);
          setError('Cannot reach the API. Check the Python server.');
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
      controller.abort();
    };
  }, [refresh]);
  return (
    <details className="connections">
      <summary>
        Service connections{' '}
        <span className={`badge ${health?.status === 'ready' ? 'ready' : ''}`}>
          {loading
            ? 'Checking…'
            : error
              ? 'API unavailable'
              : health?.status === 'ready'
                ? 'Connected'
                : 'Needs attention'}
        </span>
      </summary>
      <div className="connection-body">
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {health && (
          <dl>
            {Object.entries(health.dependencies).map(([name, status]) => (
              <div className="metadata-row" key={name}>
                <dt>{name === 'openai' ? 'OpenAI' : 'Qdrant'}</dt>
                <dd>
                  <strong>{labels[status.status]}</strong> · {status.message}
                </dd>
              </div>
            ))}
          </dl>
        )}
        <p className="muted small">
          Read-only access checks. They do not generate answers or prove indexing is ready.
        </p>
        <button
          type="button"
          className="secondary"
          disabled={loading}
          onClick={() => setRefresh((n) => n + 1)}
        >
          Check connections
        </button>
      </div>
    </details>
  );
}
