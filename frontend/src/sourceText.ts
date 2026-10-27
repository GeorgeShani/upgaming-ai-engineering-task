import type { Evidence } from './types.ts';

export function sourceExcerpt(text: string, evidence?: Pick<Evidence, 'start' | 'end' | 'text'>, full = false) {
  // Python offsets count Unicode code points. JS slice() counts UTF-16 units.
  const points = Array.from(text);
  const matches = Boolean(evidence && points.slice(evidence.start, evidence.end).join('') === evidence.text);
  const start = !full && matches && evidence ? Math.max(0, evidence.start - 200) : 0;
  const end = full ? points.length : matches && evidence ? Math.min(points.length, evidence.end + 200) : Math.min(points.length, 8000);
  const highlightStart = matches && evidence ? evidence.start : end;
  const highlightEnd = matches && evidence ? evidence.end : end;
  return {
    before: points.slice(start, highlightStart).join(''),
    highlight: matches ? points.slice(highlightStart, highlightEnd).join('') : '',
    after: matches ? points.slice(highlightEnd, end).join('') : '',
    matches, truncated: start > 0 || end < points.length, start, end, total: points.length,
  };
}
