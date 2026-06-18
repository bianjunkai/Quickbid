# QuickBid Web Frontend

`web-next/` is the current QuickBid frontend: Next.js 15, React 19,
Tailwind 4, and Vercel AI SDK. The legacy Vue app under `web/` is retained
only for reference.

## Development

Start the FastAPI backend first:

```bash
cd ..
source .venv/bin/activate
python main.py
```

Then start the frontend:

```bash
npm install
npm run dev
```

The app runs at `http://localhost:3000`. API calls use `/api/*`, which
`next.config.ts` rewrites to `http://localhost:8000/*` in development.

## Main Routes

- `/projects` — project list and entry point.
- `/projects/[id]` — confirmation-driven chat workspace.
- `/projects/[id]?file=<path>` — full-screen Markdown viewer for generated
  tender files.
- `/materials` — material library table.

## Key Files

- `app/projects/[id]/page.tsx` — chat route plus Markdown viewer overlay.
- `components/chat-thread.tsx` — AI SDK chat transport binding.
- `components/message-list.tsx` — text and tool result renderer.
- `components/file-sidebar.tsx` — generated tender file tree.
- `components/markdown-viewer.tsx` — Markdown file reader/viewer.
- `components/tools/` — tool result UIs for parse, outline, match, generate.
- `lib/api.ts` — typed fetch client for FastAPI endpoints.

## Verification

```bash
npx tsc --noEmit
```

For SSE changes, also verify event order against the Vercel AI SDK Data Stream
Protocol: `start -> text-* -> tool-input-available -> tool-output-available ->
finish-step -> finish-message -> finish`.
