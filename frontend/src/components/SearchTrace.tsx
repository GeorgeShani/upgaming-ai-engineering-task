import type { Investigation, SourceTarget } from '../types.ts';

export function SearchTrace({
  result,
  onOpen,
}: {
  result: Investigation;
  onOpen: (target: SourceTarget) => void;
}) {
  return (
    <details className="search-trace">
      <summary>
        Search trace{' '}
        <span className="muted">
          · {result.execution.searches} searches across {result.execution.retrieval_rounds} rounds
        </span>
      </summary>
      <p className="muted small">
        Queries and retrieved evidence. Ranking scores indicate relevance, not the probability that
        a claim is true.
      </p>
      <ol className="trace-list">
        {result.search_trace.map((trace) => (
          <li key={trace.tool_call_id}>
            <div className="trace-heading">
              <strong>Round {trace.round}</strong>
              <span className="badge">{trace.executed ? 'Searched' : 'Reused earlier search'}</span>
            </div>
            <p className="query-text">{trace.query}</p>
            {trace.query_adjusted && (
              <p className="muted small">
                Grounded entity added to the model's proposed query: “{trace.requested_query}”.
              </p>
            )}
            {trace.follow_up && (
              <p className="small">
                Followed “{trace.follow_up.entity}” from {trace.follow_up.evidence_id}.
              </p>
            )}
            <p className="muted small">
              Semantic: {trace.candidate_counts.active_dense}/{trace.candidate_counts.dense} active
              candidates · Keyword: {trace.candidate_counts.active_bm25}/
              {trace.candidate_counts.bm25} active candidates
            </p>
            {trace.evidence.length === 0 ? (
              <p className="muted small">No active evidence returned.</p>
            ) : (
              <ul className="trace-evidence">
                {trace.evidence.map((hit) => (
                  <li key={hit.chunk_id}>
                    <button
                      type="button"
                      className="text-button"
                      onClick={() =>
                        onOpen({ id: hit.document_id, title: hit.title, evidence: hit })
                      }
                    >
                      {hit.evidence_id} · {hit.title}
                    </button>
                    <span className="muted small"> RRF {hit.fusion_score.toFixed(5)}</span>
                    <details>
                      <summary className="small">Read retrieved text</summary>
                      <p className="source-text small">{hit.text}</p>
                    </details>
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ol>
      <details className="run-details">
        <summary>Run details</summary>
        <dl>
          <div className="metadata-row">
            <dt>Model</dt>
            <dd>{result.configuration.generation_model}</dd>
          </div>
          <div className="metadata-row">
            <dt>Chunking</dt>
            <dd>Configuration {result.configuration.strategy.toUpperCase()}</dd>
          </div>
          <div className="metadata-row">
            <dt>Prompt</dt>
            <dd>{result.configuration.prompt_version}</dd>
          </div>
          <div className="metadata-row">
            <dt>Calls</dt>
            <dd>
              {result.execution.llm_calls} language-model calls · stop:{' '}
              {result.execution.stop_reason.replaceAll('_', ' ')}
            </dd>
          </div>
          {result.verification && (
            <div className="metadata-row">
              <dt>Evidence review</dt>
              <dd>
                {result.verification.outcome === 'not_needed'
                  ? 'No claims to review'
                  : `${result.verification.outcome === 'passed' ? 'Passed' : 'Answer withheld'} · ${result.verification.reviewed_claims} claims reviewed · ${result.verification.comparisons_checked} numeric comparisons checked`}
                <p className="muted small">Model review can miss errors. Inspect the citations.</p>
              </dd>
            </div>
          )}
        </dl>
      </details>
    </details>
  );
}
