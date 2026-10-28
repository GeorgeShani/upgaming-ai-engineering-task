# UI refinement walkthrough

The interface keeps the existing green identity and improves the hierarchy and navigation.
The question is the primary action. The right column explains the workflow, while service
diagnostics, administrator access and search details stay behind disclosures.

## Follow one interaction

1. Type a question. `InvestigationPanel` holds the controlled textarea value in React state.
   The character counter counts Unicode code points, matching the existing question check.
2. Click **Browse documents**. `App` changes the active view and focuses its Documents heading.
   Both views stay mounted, so the draft survives the switch. No investigation is submitted.
3. Return to **Investigate**. An example only fills/focuses the field; **Investigate** submits.
   The existing `/api/investigations` client, pending lock and error handling still apply.
4. A completed result receives focus. Open a citation to read its quoted evidence and current
   canonical source. Close it with Escape; focus returns to the citation.
5. Expand **Search trace** for executed queries and evidence. It is a record of tool activity,
   not hidden model reasoning or a confidence probability.

The validation error is associated with the textarea using `aria-describedby` and
`aria-invalid`. The character counter is visual; the accessible help still gives the limit,
without announcing a changing number on every keystroke.

React's controlled form pattern is documented in the official
[textarea reference](https://react.dev/reference/react-dom/components/textarea).

## Choices and alternatives

| Choice | Reason | Alternative and drawback |
| --- | --- | --- |
| Refine the existing CSS and native controls | Keeps this slice easy to trace and avoids a migration | A component framework provides more widgets but adds dependencies, styles and concepts to learn |
| Two desktop columns, one mobile column | Separates task from help without putting help on another page | A permanent sidebar would consume reading space on small screens |
| Keep both views mounted | Drafts, answers and last-upload access survive navigation | Conditional mounting saves some DOM but would need lifted state to preserve work |
| Details for service/admin/trace | Makes advanced information available without interrupting the primary task | More dialogs add focus-management work and interrupt the flow |
| Small shared SVG component | Consistent icons with no download or package | An icon package offers broader coverage but is unnecessary for these three icons |

## Verify it yourself

From the repository root, run the API:

```powershell
uv run uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm run preview
```

Preview rebuilds the interface automatically; open the printed localhost URL. Check a draft
survives Browse documents → Investigate; fill the development example and confirm it does not
submit until you click Investigate. A real submitted question can incur API usage.

For free fixture checks, with ports 8001/4174 available:

```powershell
cd frontend
npm run test:unit
npm run test:browser
npm run format:check
```

The browser suite covers all document operations, conflicts/abstention/provider failures,
stale citations, token clearing, safe text, focus, axe and four responsive widths. Its providers
are in memory. Screenshots under ignored `artifacts/` show fixture data, not public answers.

On the hosted site, verify the same navigation at desktop and phone widths, inspect a source,
and expand service connections. Deployment readiness and cloud restart persistence are
separate checks; a polished UI does not prove them.
