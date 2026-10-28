# Investigation workspace UI

Scope: refinement of the existing React document and investigation screens. The product is a
shared evidence investigation tool; it is not a chat history or a private file vault.

The existing forest green, warm neutral canvas and system sans are retained. The page should
feel like a quiet research workspace. Avoid a marketing hero, invented statistics, decorative
motion, external font downloads, and extra component dependencies.

- Primary action: enter a question, then submit explicitly. Examples fill the field without
  submitting a paid request. Keep cost guidance beside the action.
- Desktop: question form and a narrower help column; the result spans the reading area below.
  Focus moves to the result after completion so the user reaches the answer immediately.
- Mobile: single column, full-width submit button, shorter help area. Preserve the document
  shortcut; hide the longer instructional list. Do not shrink body type to fit a desktop grid.
- Documents: upload and management access are grouped separately from the source list. Admin
  access stays in a disclosure; never persist its token in browser storage.
- Sources: keep the native modal because reading a citation is a temporary, focused detour.
  Preserve Escape, return focus, revision warnings, exact excerpts and deletion confirmation.
- Typography: fixed rem headings, system sans, 65–75-character prose measure, tabular numerals
  for counts/costs. One h1 identifies the app; h2 identifies the active workspace.
- Color: `--accent` #1d5140, `--text` #202c28, `--muted` #52615a, `--border` #d5ddd5,
  `--surface` white, `--surface-subtle` #f1f4ef. States use both text and color.
- Controls: native buttons, inputs, textarea and details. Shared authored SVG icons use the
  same view box and stroke. Visible focus is blue; reduced motion disables transitions.
- States: API errors remain distinct from missing/conflicting evidence. Preserve loading,
  permission, stale-revision, validation and safe-text rendering behavior.

Verification uses the existing in-memory browser fixture with actual FastAPI routes. It does
not claim paid-model semantic correctness. Check 320, 768, 1024 and 1440 px, keyboard/dialog
focus, axe, and the full upload → answer → citation → trace → delete path.
