# Cadre web app

The Next.js 16 frontend for Cadre, Stixor's AI workspace. It talks to the FastAPI backend in the parent folder.

## Run

```bash
npm install
cp .env.example .env.local     # BACKEND_URL=http://localhost:8000
npm run dev                    # http://localhost:3000
```

Production: `npm run build && npm run start`. Checks: `npx tsc --noEmit && npm run lint`.

The backend must be running (`uvicorn app.api.main:app --port 8000` from the repo root).

## How it connects to the backend

```
Browser ──► Next.js (:3000) ──► FastAPI (:8000)
            │
            ├─ /api/auth/login    POST credentials → backend /auth/login → sets httpOnly cookie `cadre_token`
            ├─ /api/auth/logout   clears the cookie
            └─ /api/backend/*     forwards any method to FastAPI with `Authorization: Bearer <cookie>`
                                   (streams SSE and file downloads through unchanged)
```

- `src/proxy.ts`: redirects to `/login` when there is no session cookie (Next 16 "Proxy", formerly middleware).
- The JWT never reaches browser JavaScript. All authorization is enforced by FastAPI.
- `BACKEND_URL` is read **server-side only**.

## Structure

```
src/
  app/
    login/                       sign-in page
    (app)/layout.tsx             shell: sidebar + top bar + session + toasts
    (app)/page.tsx               Home: greeting, composer, suggestions, agent cards, recents
    (app)/chat/[threadId]/       chat with streaming, artifacts, context panel
    (app)/agents | conversations | documents | activity | settings
    (app)/admin/                 overview (charts) | users | agents | integrations
    api/auth/{login,logout}      cookie handling
    api/backend/[...path]        BFF proxy to FastAPI
    icon.png, apple-icon.png     favicon (Cadre mark)
  components/
    layout/   sidebar, topbar (search ⌘K, system status, user menu), logo, session
    chat/     composer (agent picker), message, markdown (+ Mermaid), artifacts, context panel
    agents/   agent card, Jira connection card
    admin/    runs table + run drawer, admin guard
    ui/       buttons, inputs, modal, drawer, tabs, toggle, toast, data table
  lib/
    api.ts     fetch wrapper (+ SWR fetcher, file URLs, logout)
    stream.ts  SSE reader for /chat/stream
    agents.ts  per-agent colours, icons, capabilities, example prompts
    types.ts   API types (mirror ../README.md §3)
public/brand/  cadre-logo.png, cadre-mark.png
```

## Brand

- Navy `#1C344A` (`bg-brand`), teal accent `#00A2AD` (`text-accent`). Tokens live in `src/app/globals.css`.
- Agent accents: HR violet, DevOps blue, Finance orange, PM teal, Solution Engineer green.
- Font: Inter (UI), JetBrains Mono (code).
