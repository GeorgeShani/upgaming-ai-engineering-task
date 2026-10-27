export type DocumentSummary = {
  document_id: string;
  revision_id: string;
  filename: string;
  title: string;
  format: 'pdf' | 'docx' | 'txt' | 'dataset';
  content_sha256: string;
  created_at: string;
  updated_at: string;
  index_status: 'pending' | 'ready';
};

export type SourceLocation = {
  kind: 'page' | 'paragraph' | 'table_row' | 'sentence';
  number: number;
  start: number;
  end: number;
};

export type DocumentView = DocumentSummary & {
  text: string;
  locations: (SourceLocation & { text: string })[];
  metadata: Record<string, string>;
};

export type DocumentPage = { items: DocumentSummary[]; next_cursor: string | null };
export type MutationResult = { document: DocumentSummary; duplicate: boolean };
export type Citation = { evidence_id: string; quote: string };
export type Claim = { text: string; citations: Citation[] };
export type Evidence = {
  evidence_id: string;
  chunk_id: string;
  document_id: string;
  revision_id: string;
  title: string;
  text: string;
  start: number;
  end: number;
  locations: SourceLocation[];
  metadata: Record<string, string>;
  fusion_score: number;
};

export type SearchTrace = {
  query: string;
  round: number;
  tool_call_id: string;
  executed: boolean;
  follow_up: { evidence_id: string; entity: string } | null;
  candidate_counts: { dense: number; bm25: number; active_dense: number; active_bm25: number };
  evidence: Evidence[];
};

export type Investigation = {
  status: 'answered' | 'insufficient_evidence' | 'conflicting_evidence';
  answer: string;
  claims: Claim[];
  conflicting_claims: Claim[];
  evidence: Evidence[];
  search_trace: SearchTrace[];
  latency_ms: number;
  execution: { retrieval_rounds: number; searches: number; llm_calls: number; stop_reason: string };
  usage: { estimated_total_cost_usd: number };
  configuration: { strategy: 'a' | 'b'; generation_model: string; prompt_version: string };
};

export type SourceTarget = {
  id: string;
  title: string;
  manage?: boolean;
  evidence?: Evidence;
  quote?: string;
};
