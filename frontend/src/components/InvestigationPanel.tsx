import { useEffect, useRef, useState } from 'react';
import { api, errorMessage } from '../api.ts';
import type { Claim, Investigation, SourceTarget } from '../types.ts';
import { SearchTrace } from './SearchTrace.tsx';
import { Icon } from './Icon.tsx';

const statuses = {
  answered: {
    label: 'Answered',
    description: 'Review the cited passages to check how each claim is supported.',
  },
  insufficient_evidence: {
    label: 'Insufficient evidence',
    description:
      'The retrieved sources could not support an answer. Try a more specific question or add a relevant source.',
  },
  conflicting_evidence: {
    label: 'Conflicting evidence',
    description:
      'Sources disagree. Both reports are preserved below; no single value has been selected.',
  },
};
const example = 'What recovery time was documented for fictional incident NOVA-DEVELOPMENT-01?';
type Props = {
  corpusVersion: number;
  onOpen: (target: SourceTarget) => void;
  onBrowse: () => void;
};

export function InvestigationPanel({ corpusVersion, onOpen, onBrowse }: Props) {
  const [question, setQuestion] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<{ kind: 'validation' | 'request'; message: string } | null>(
    null,
  );
  const [answered, setAnswered] = useState<{
    result: Investigation;
    question: string;
    version: number;
  } | null>(null);
  const controller = useRef<AbortController | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  useEffect(() => () => controller.current?.abort(), []);

  async function investigate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = question.trim();
    if (pending) return;
    if (Array.from(text).length < 3 || Array.from(text).length > 1000) {
      setError({ kind: 'validation', message: 'Enter a question between 3 and 1,000 characters.' });
      return;
    }
    const request = new AbortController();
    controller.current = request;
    const timeout = window.setTimeout(() => request.abort(), 105_000);
    setPending(true);
    setError(null);
    setAnswered(null);
    try {
      const { data } = await api.investigate(text, request.signal);
      if (!request.signal.aborted) {
        setAnswered({ result: data, question: text, version: corpusVersion });
        requestAnimationFrame(() => heading.current?.focus());
      }
    } catch (cause) {
      setError({
        kind: 'request',
        message: request.signal.aborted
          ? 'The request timed out before a result was received. It may have incurred API usage. Try again only when you are ready to submit a new investigation.'
          : errorMessage(cause),
      });
    } finally {
      window.clearTimeout(timeout);
      setPending(false);
    }
  }

  const result = answered?.result;
  const byId = new Map(result?.evidence.map((hit) => [hit.evidence_id, hit]) ?? []);
  function claims(items: Claim[], conflict = false) {
    return (
      <ul className={`claim-list ${conflict ? 'conflict-claims' : ''}`}>
        {items.map((claim, index) => (
          <li key={index}>
            <p>{claim.text}</p>
            <div className="citation-links">
              {claim.citations.map((citation, citationIndex) => {
                const hit = byId.get(citation.evidence_id);
                return hit ? (
                  <button
                    className="citation"
                    type="button"
                    key={citationIndex}
                    aria-label={`Open citation ${citation.evidence_id}: ${hit.title}`}
                    onClick={() =>
                      onOpen({
                        id: hit.document_id,
                        title: hit.title,
                        evidence: hit,
                        quote: citation.quote,
                      })
                    }
                  >
                    [{citation.evidence_id}] <span>{hit.title}</span>
                  </button>
                ) : (
                  <span key={citationIndex}>Citation {citation.evidence_id} is unavailable.</span>
                );
              })}
            </div>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <section className="workspace-section" aria-labelledby="investigate-title">
      <div className="investigation-layout">
        <div className="question-workspace">
          <h2 id="investigate-title">What would you like to find out?</h2>
          <p className="muted section-intro">
            Find a fact, connect documents, or compare conflicting reports.
          </p>
          <form onSubmit={investigate} aria-busy={pending}>
            <div className="field-heading">
              <label htmlFor="question">Your question</label>
              <span
                className={`character-count ${Array.from(question).length > 1000 ? 'over-limit' : ''}`}
                aria-hidden="true"
              >
                {Array.from(question).length.toLocaleString()} / 1,000
              </span>
            </div>
            <textarea
              ref={input}
              id="question"
              rows={5}
              value={question}
              disabled={pending}
              aria-describedby={
                error?.kind === 'validation' ? 'question-help question-error' : 'question-help'
              }
              aria-invalid={error?.kind === 'validation' ? true : undefined}
              required
              minLength={3}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="What happened, and which sources support it?"
            />
            <div className="question-actions">
              <p id="question-help" className="muted small">
                Up to 1,000 characters. Uses the configured model API; each submitted question may
                incur a small charge.
              </p>
              <button type="submit" disabled={pending}>
                {pending ? 'Investigating…' : 'Investigate'}
              </button>
            </div>
            <button
              type="button"
              className="text-button small"
              disabled={pending}
              onClick={() => {
                setQuestion(example);
                input.current?.focus();
              }}
            >
              Use a development example
            </button>
            {pending && (
              <p role="status" className="working">
                Searching and checking sources. The bounded investigation can take up to 90 seconds.
              </p>
            )}
            {error && (
              <div id="question-error" className="error-panel" role="alert">
                <strong>
                  {error.kind === 'request'
                    ? 'Investigation could not finish'
                    : 'Check your question'}
                </strong>
                <p>{error.message}</p>
                <p className="small">
                  {error.kind === 'request'
                    ? 'This is an API error, not an insufficient-evidence result. Nothing is resubmitted automatically.'
                    : 'Nothing has been submitted.'}
                </p>
              </div>
            )}
          </form>
        </div>
        <aside className="investigation-guide" aria-label="Investigation guide">
          <h3>From question to evidence</h3>
          <ol className="guide-steps">
            <li>
              <strong>Ask something specific</strong>
              <p>Include a name, event, or service to help find relevant passages.</p>
            </li>
            <li>
              <strong>Check the sources</strong>
              <p>Open a citation to read the exact passage behind a claim.</p>
            </li>
            <li>
              <strong>Follow the search</strong>
              <p>Expand the search trace to see the queries and retrieved evidence.</p>
            </li>
          </ol>
          <div className="guide-library">
            <Icon name="documents" />
            <h3>Start with your sources</h3>
            <p>
              Browse the shared collection or add a PDF, DOCX, or TXT document with admin access.
            </p>
            <button type="button" className="text-button" onClick={onBrowse}>
              Browse documents <Icon name="arrow" />
            </button>
          </div>
        </aside>
      </div>
      {!pending && !error && !result && (
        <div className="empty-state investigation-empty">
          <Icon name="search" />
          <div>
            <h3>Your investigation starts here</h3>
            <p>
              Ask above to see an answer with clickable sources. If evidence is missing or
              conflicting, the result will say so.
            </p>
          </div>
        </div>
      )}
      {result && answered && (
        <article className="investigation-result" aria-labelledby="answer-title">
          <div className="result-heading">
            <h3 ref={heading} tabIndex={-1} id="answer-title">
              Investigation result
            </h3>
            <span className={`badge result-status ${result.status}`}>
              {statuses[result.status].label}
            </span>
          </div>
          <p className="asked-question">{answered.question}</p>
          <p className="muted small">{statuses[result.status].description}</p>
          {answered.version !== corpusVersion && (
            <p className="warning" role="status">
              A document operation completed since this answer. This result is a snapshot; submit a
              new investigation to check current evidence.
            </p>
          )}
          {result.status === 'insufficient_evidence' ? (
            <p className="abstention">{result.answer}</p>
          ) : (
            <>
              {result.claims.length > 0 && claims(result.claims)}
              {result.conflicting_claims.length > 0 && (
                <div>
                  <h4>Conflicting claims</h4>
                  {claims(result.conflicting_claims, true)}
                </div>
              )}
            </>
          )}
          <div className="answer-metrics">
            <span>{(result.latency_ms / 1000).toFixed(1)} s</span>
            <span>{result.evidence.length} evidence chunks</span>
            <span>Estimated API cost ${result.usage.estimated_total_cost_usd.toFixed(4)}</span>
          </div>
          <SearchTrace result={result} onOpen={onOpen} />
        </article>
      )}
    </section>
  );
}
