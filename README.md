# Stixor Office Assistant: Backend & Frontend Integration Guide

A multi-agent assistant for Stixor's departments. A **supervisor** (GLM 5.2) routes each chat message to a
**department agent** (Qwen 3.5): **HR** (contracts), **DevOps** (IT data via SQL), **Finance** (PDF invoices),
**PM** (the user's Jira, sprint planning) and **Developer** (brainstorming).

This README is for **frontend developers building the new UI**. It covers how to run the backend, the full API
contract, TypeScript types, the screens to build and the flows that need special handling.

- How it was built and why: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Machine-readable contract: [`docs/openapi.json`](docs/openapi.json); live Swagger UI at `http://localhost:8000/docs`
- Reference UI: [`ui/user_app.py`](ui/user_app.py), [`ui/admin_app.py`](ui/admin_app.py). These Streamlit apps show every feature working; the new UI replaces them.

---

## 1. Run the backend

```bash
/opt/homebrew/bin/python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env                       # ask the team for the real values
.venv/bin/python scripts/seed_devops_db.py # demo IT database
.venv/bin/uvicorn app.api.main:app --port 8000
```

Optional reference UIs: `.venv/bin/streamlit run ui/user_app.py --server.port 8501` and `ui/admin_app.py --server.port 8502`.

The first start creates the admin user from `ADMIN_USERNAME`/`ADMIN_PASSWORD` in `.env`. Create test users in the
admin console or with `python scripts/create_user.py NAME PASSWORD --agents hr,finance`.

**Backend settings that matter to the frontend** (`.env`):

| Variable | Why the frontend cares |
|---|---|
| `USER_UI_URL` | Where the Jira OAuth flow sends the browser back to. Set it to the new user app's URL, e.g. `https://office.stixor.com`. |
| `JIRA_OAUTH_CLIENT_ID/SECRET` | When set, `/integrations/jira/status` returns `oauth_available: true`, so show the "Connect Jira" button. |
| CORS | Currently allows `*` (no cookies are used; auth is a bearer header). It will be locked to the frontend origin before production, so tell us your origin. |

---

## 2. Basics

- **Base URL**: `http://localhost:8000` (configurable). All bodies are JSON unless stated.
- **Auth**: `POST /auth/login` returns a JWT. Send `Authorization: Bearer <token>` on every request except `/auth/login` and `/health`. Tokens last **12 h**. Keep the token in memory or `sessionStorage`, and on any **401** clear it and show the login screen.
- **Roles**: `admin` and `user`. Show the admin app only when `user.role === "admin"`; the server enforces this anyway.
- **What a user can use**: build the assistant picker **only** from `user.available_agents` (allowed for the user and enabled by an admin).
- **Errors** look like `{ "detail": string }`. Validation errors (422) use FastAPI's `{ "detail": [{loc, msg, type}] }`.

| Status | Meaning | UI action |
|---|---|---|
| 400 | Bad input (e.g. non-.docx upload, bad Jira token) | Show `detail` |
| 401 | Missing or expired token, or bad login | Go to login |
| 403 | Admin-only endpoint | Hide or deny |
| 404 | Unknown, or not yours (e.g. someone else's thread) | Show not found |
| 409 | Username already exists | Show on form |
| 413 | Upload larger than 10 MB | Show message |
| 422 | Schema validation | Show field errors |
| 502 | An agent or the LLM failed | Show "Something went wrong, try again" |

- **Latency**: agent replies take **about 10–70 s**. Use client timeouts of at least **180 s** for `/chat`, show a busy state, and prefer `/chat/stream` so you can show *which* agent is working as soon as routing finishes.

---

## 3. TypeScript types

```ts
export type AgentName = "hr" | "devops" | "finance" | "pm" | "developer";
export type Department = "auto" | AgentName;          // "auto" = let the supervisor decide
export type Responder = AgentName | "supervisor";     // supervisor answers greetings and refusals itself

export interface AgentInfo { name: AgentName; label: string; icon: string; summary: string }

export interface Me {
  id: number;
  username: string;
  full_name: string;
  role: "admin" | "user";
  allowed_agents: AgentName[];
  available_agents: AgentInfo[];      // build the assistant picker from this
}

export interface LoginResponse { access_token: string; token_type: "bearer"; user: Me }

// ---------- chat ----------
export interface ChatRequest {
  message: string;                    // 1..20000 chars
  thread_id?: string | null;          // omit to start a new conversation; reuse the returned one after that
  department?: Department;            // default "auto"
  template_id?: string | null;        // HR only: the selected contract template
}

export interface ChatResponse {
  thread_id: string;
  reply: string;                      // GitHub-flavoured Markdown; may contain ```mermaid blocks and tables
  agent: Responder;
  route_reason: string | null;        // one sentence: why this agent was chosen (show as a subtle caption)
  artifacts: Artifact[];
}

export type Artifact = FileArtifact | SqlArtifact | TableArtifact;

export interface FileArtifact {       // contracts (.docx), invoices (.pdf), plans (.xlsx/.csv/.md)
  type: "file";
  file_id: string;                    // download with GET /files/{file_id}
  filename: string;                   // e.g. "STX-2026-0002.pdf"
  mime?: string;                      // may be missing for .docx; infer from the filename extension
  invoice_no?: string;                // Finance
  template_id?: string;               // HR
}

export interface SqlArtifact {        // DevOps query result
  type: "sql";
  query: string;                      // the SQL that ran (show in a collapsible code block)
  columns: string[];
  rows: (string | number | null)[][]; // up to 200 rows
}

export interface TableArtifact {      // e.g. PM sprint plan
  type: "table";
  title: string;
  columns: string[];
  rows: (string | number | null)[][];
}

// ---------- threads ----------
export interface ThreadSummary { thread_id: string; title: string; updated_at: string }
export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
  agent?: Responder | null;
  artifacts: Artifact[];              // re-render downloads and tables from history
}
export interface ThreadHistory { thread_id: string; messages: HistoryMessage[] }

// ---------- HR ----------
export interface TemplateInfo {
  template_id: string; name: string; description: string; placeholder_count: number; uploaded_at: string;
}

// ---------- Finance ----------
export interface ClientInfo { id: number; name: string; default_currency: string; email: string }
export interface InvoiceSummary {
  invoice_no: string; client: string; issue_date: string; total: number; currency: string;
  file_id: string; service_description: string;
}
export interface BankAccount { id: string; label: string; currency: string }

// ---------- PM / Jira ----------
export interface JiraStatus {
  oauth_available: boolean;           // true: show the "Connect Jira" (OAuth) button
  connected: boolean;
  site_url?: string; account?: string; auth_type?: "oauth" | "api_token" | "pat"; connected_at?: string;
}

// ---------- Admin ----------
export interface AdminStats {
  days: number; requests: number; requests_today: number; active_users: number; users_total: number;
  error_rate: number;                 // percent
  refused: number; avg_latency_ms: number; p95_latency_ms: number; tokens: number;
  per_agent: Record<string, { runs: number; errors: number; tokens: number; avg_latency_ms: number; p95_latency_ms: number }>;
  per_day: { date: string; agent: string; runs: number }[];
  per_user: { user: string; runs: number }[];
}
export interface TraceStep { thought: string; action: string; args: Record<string, unknown> }
export interface AgentRunRow {
  id: number; created_at: string; user: string; agent: Responder | "unknown";
  status: "ok" | "error" | "refused"; latency_ms: number; llm_calls: number; tool_calls: number; tokens: number;
  message: string; route_reason: string; trace: TraceStep[]; error: string; thread_id: string;
}
export interface AdminAgent {
  name: AgentName | "supervisor"; label: string; icon: string; summary: string; enabled: boolean;
  model: string; tools: string[]; runs_7d: number; errors_7d: number; avg_latency_ms: number;
}
export interface AdminUser {
  id: number; username: string; full_name: string; role: "admin" | "user"; allowed_agents: AgentName[];
  is_active: boolean; jira_connected: boolean; created_at: string;
}
export interface JiraConnectionRow {
  user_id: number; user: string; auth_type: string; site_url: string; account: string;
  connected_at: string; expires_at: string | null;
}
```

---

## 4. Endpoints

### Auth
| Method | Path | Body / params | Returns |
|---|---|---|---|
| POST | `/auth/login` | `{username, password}` | `LoginResponse` (401 on bad credentials) |
| GET | `/auth/me` | none | `Me` (refresh after an admin changes permissions) |
| GET | `/health` | none, no auth | `{status, supervisor_model, worker_model, worker_native_tools}` |

### Chat & conversations
| Method | Path | Body / params | Returns |
|---|---|---|---|
| POST | `/chat` | `ChatRequest` | `ChatResponse` |
| POST | `/chat/stream` | `ChatRequest` | `text/event-stream` (see §5.2) |
| GET | `/threads` | none | `ThreadSummary[]` (latest 30, newest first) |
| GET | `/threads/{thread_id}` | none | `ThreadHistory` (404 if not yours) |

### Files & HR templates
| Method | Path | Body / params | Returns |
|---|---|---|---|
| GET | `/files/{file_id}` | none | Binary file (needs the auth header, see §5.3) |
| GET | `/templates` | none | `TemplateInfo[]` |
| POST | `/templates` | multipart: `file` (.docx, max 10 MB), `name?`, `description?` | `TemplateInfo` (201) |
| GET | `/templates/{template_id}/placeholders` | none | Detected fields (debug/preview) |

### Finance
| Method | Path | Params | Returns |
|---|---|---|---|
| GET | `/clients` | none | `ClientInfo[]` |
| GET | `/invoices` | `client?`, `limit?` (default 20) | `InvoiceSummary[]` (newest first) |
| GET | `/finance/bank-accounts` | none | `BankAccount[]` |

Invoices are **created through chat** (the Finance agent), not through a form endpoint.

### Jira connector (PM)
| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/integrations/jira/status` | none | `JiraStatus` |
| GET | `/integrations/jira/connect` | none | `{authorize_url}` (400 if OAuth isn't configured) |
| POST | `/integrations/jira/token` | `{site_url, email, api_token, kind?: "api_token" \| "pat"}` | `{connected, site_url, account}` (400 if Jira rejects it) |
| DELETE | `/integrations/jira` | none | `{disconnected: boolean}` |
| GET | `/integrations/jira/callback` | used by Atlassian, not by your code | Redirects to `USER_UI_URL?jira=connected` or `?jira=error&detail=…` |

### Admin (role `admin` only)
| Method | Path | Body / params | Returns |
|---|---|---|---|
| GET | `/admin/stats` | `days` (1–90, default 7) | `AdminStats` |
| GET | `/admin/runs` | `agent?`, `user?` (username), `status?`, `limit?` (≤500) | `AgentRunRow[]` |
| GET | `/admin/agents` | none | `AdminAgent[]` (includes a read-only `supervisor` row) |
| PATCH | `/admin/agents/{name}` | `{enabled: boolean}` | `{name, enabled}` |
| GET | `/admin/users` | none | `AdminUser[]` |
| POST | `/admin/users` | `{username, password (≥4), full_name?, role?, allowed_agents?}` | `AdminUser` (201; 409 if the username is taken) |
| PATCH | `/admin/users/{id}` | any of `{full_name, role, allowed_agents, is_active, password}` | `AdminUser` (an admin can't demote or deactivate themselves) |
| GET | `/admin/integrations` | none | `JiraConnectionRow[]` |
| DELETE | `/admin/integrations/jira/{user_id}` | none | `{revoked: true}` |

---

## 5. Flows that need special handling

### 5.1 Chat (non-streaming)
```ts
const res = await api<ChatResponse>("/chat", { method: "POST", body: JSON.stringify({
  message, thread_id: currentThreadId ?? undefined, department: selected /* "auto" | AgentName */,
  template_id: department === "hr" ? selectedTemplateId : undefined,
})});
currentThreadId = res.thread_id;             // keep using it for follow-ups
```
- **Follow-ups**: agents ask clarifying questions (HR asks for a CNIC, Finance confirms totals). Send the answer in the **same `thread_id`**; the supervisor keeps the conversation with the same agent.
- **"Auto"**: let the supervisor decide. Picking a specific agent skips routing, which is slightly faster.
- **Agent badge**: show `agent` on each reply, with `route_reason` as a small caption.
- **Refusals**: if the user lacks access, the reply comes from `agent: "supervisor"` with a polite refusal. This is not an error.

### 5.2 Chat streaming (recommended)
`POST /chat/stream` returns Server-Sent Events. `EventSource` can't send a POST or headers, so read the stream with `fetch`:

```ts
const resp = await fetch(`${API}/chat/stream`, {
  method: "POST",
  headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
  body: JSON.stringify(req),
});
const reader = resp.body!.pipeThrough(new TextDecoderStream()).getReader();
let buf = "";
for (;;) {
  const { value, done } = await reader.read();
  if (done) break;
  buf += value;
  let i;
  while ((i = buf.indexOf("\n\n")) >= 0) {
    const chunk = buf.slice(0, i); buf = buf.slice(i + 2);
    const event = /^event: (.*)$/m.exec(chunk)?.[1];
    const data = JSON.parse(/^data: (.*)$/m.exec(chunk)?.[1] ?? "{}");
    handle(event, data);
  }
}
```

| Event | Data | When |
|---|---|---|
| `thread` | `{thread_id}` | First. Store it. |
| `route` | `{agent: Responder \| "supervisor", reason}` | After routing (about 2–6 s). Show e.g. "💵 Finance is working…". |
| `message` | `{agent, content, artifacts: Artifact[]}` | The final reply (the reply arrives in one piece, not token by token). |
| `error` | `{detail}` | The agent failed. |
| `done` | `{}` | Always last. |

### 5.3 Downloading files
`/files/{id}` needs the bearer header, so a plain `<a href>` won't work. Fetch it as a blob:
```ts
const r = await fetch(`${API}/files/${a.file_id}`, { headers: { Authorization: `Bearer ${token}` } });
const url = URL.createObjectURL(await r.blob());
Object.assign(document.createElement("a"), { href: url, download: a.filename }).click();
URL.revokeObjectURL(url);
```
For PDFs, you can also show the blob URL in an `<iframe>` as a preview.

### 5.4 Rendering assistant replies
- **Markdown**: GFM, with tables and code blocks (e.g. `react-markdown` + `remark-gfm`).
- **Diagrams**: ```` ```mermaid ```` blocks should be rendered with `mermaid` (the Developer agent uses them), with a "show source" toggle.
- **Artifacts**, rendered under the message text:
  - `file`: a download button, with a 📄 icon for PDF, 📝 for DOCX and 📊 for XLSX/CSV.
  - `sql`: a collapsible "Query used" code block, plus a data table (sortable; up to 200 rows).
  - `table`: a data table titled `title`. PM sprint plans group by the `Sprint` column; rows whose Sprint is `Overflow (after deadline)` should be highlighted.

### 5.5 HR template upload
`multipart/form-data` with `file` (.docx), plus optional `name` and `description`. After upload, refresh `/templates`
and pre-select the new `template_id`, then send it as `template_id` in HR chat requests.

### 5.6 Connect Jira (PM)
1. `GET /integrations/jira/status`.
2. If `connected`: show "Connected to {site_url} as {account}" and a **Disconnect** button (`DELETE /integrations/jira`).
3. If not connected:
   - If `oauth_available`: show **Connect Jira**. Call `GET /integrations/jira/connect` and set `window.location = authorize_url`. After the user approves, Atlassian sends them back to `USER_UI_URL?jira=connected` (or `?jira=error&detail=...`). Read the query string on load, show a toast, clear the parameter and refresh the status.
   - Always also offer the **API token form**: site (e.g. `stixor.atlassian.net`), Atlassian email and an API token (link to https://id.atlassian.com/manage-profile/security/api-tokens). Submit to `POST /integrations/jira/token`.
4. The PM agent is **read-only**. It never changes Jira, so don't offer "apply to Jira" actions. Offer the exported file instead.

---

## 6. Screens to build

### User app (all roles)
1. **Login**: username and password. Show errors from `detail`.
2. **Workspace layout**:
   - **Sidebar**:
     - user name and role, with Log out
     - **New conversation** (clears `thread_id`)
     - **Assistant picker**: "Auto" plus `available_agents`, with icon, label and summary as a tooltip
     - **Conversations**: `GET /threads`; clicking one loads `GET /threads/{id}`
   - **Context panel**, depending on the selected assistant (in Auto, show the panels for every assistant the user has):
     - **HR**: template dropdown (`/templates`) and an upload form.
     - **Finance**: recent invoices (`/invoices?limit=8`) with download buttons; clients (`/clients`) as quick-insert chips, optional.
     - **PM**: the Jira connection card (§5.6).
   - **Chat**: message list (user and assistant bubbles, agent badge, route reason, Markdown, Mermaid, artifacts), a composer (Enter to send, Shift+Enter for a new line), a busy state with the streaming `route` label, and retry on error.
   - **Empty state**: one card per available assistant, with its summary and 2–3 example prompts (see §7).
   - If the user has **no assistants**: "Ask an admin for access".

### Admin app (role `admin`)
1. **Overview**:
   - Period selector (1/7/14/30/90 days).
   - KPI tiles: requests today, requests in the period, active users vs total, error rate, average and p95 latency, tokens.
   - Charts: requests per day stacked by agent (`per_day`), routing share as a donut (`per_agent.runs`), average latency per agent, top users (`per_user`).
2. **Agents**: a card per agent with icon, label, summary, model, tools, 7-day runs, errors and average latency, and an **enabled toggle** (`PATCH /admin/agents/{name}`). The supervisor row is read-only.
3. **Activity**:
   - Filters: agent, user, status, limit.
   - Table: time, user, agent, status badge, latency, LLM calls, tool calls, tokens, message.
   - **Drill-down** drawer: route reason, error, and **trace** steps (step N: `action`, `thought`, `args` as JSON).
4. **Users**: table (role, allowed agents as chips, active, Jira connected), **Create user** form (username, full name, password, role, allowed agents as a multi-select), and an **Edit** drawer (role, allowed agents, active, reset password).
5. **Integrations**: Jira connections per user (site, account, auth type, connected at), each with a **Revoke** button.

---

## 7. Example prompts (for empty states and QA)
| Agent | Prompt |
|---|---|
| HR | "Draft the hourly consultant contract for Sara Malik, UI/UX Designer, USD 12/hour, 1 year, effective today. Write 6 job duties. Change notice to 15 days." |
| DevOps | "Which laptops have warranties expiring in the next 90 days, and who are they assigned to?" |
| Finance | "Invoice Isekaiverse for October: 40 h frontend at $15 and 25 h backend at $18, 5% tax, USD account." |
| PM | "For project QR, plan 2-week sprints to finish all open work by 15 December using the board's velocity." then "Export that plan as Excel." |
| Developer | "Help me shape an internal hackathon voting app, include a Mermaid architecture diagram." |

## 8. Integrating the new UI with this backend
1. Build the UI as a separate SPA (React, Next.js, etc.) against `API_BASE_URL`. No backend changes are needed for the screens above.
2. Point the backend's `USER_UI_URL` at the new user app (for the Jira OAuth return), and register that same callback host with Atlassian.
3. Send us the frontend origin(s) so CORS can be restricted.
4. Optional: we can serve the built static files from FastAPI under `/app` if you prefer a single deployment.
5. When the new UI covers everything, the Streamlit apps in `ui/` can be removed.

## 9. Backend notes for maintainers
- **Tests**: `.venv/bin/python -m pytest -q` (41 tests).
- **Finance settings**: `config/finance.yaml` holds bank accounts, the invoice number format, the signatory, and `apply_signature_image` (off by default).
- **New agent**: add its tools, a node in `app/agents/subagents.py`, a prompt in `app/prompts.py` and an entry in `app/agents/registry.py`. It then shows up automatically in routing, `/auth/me`, the admin endpoints and the UIs.
- **Regenerating the contract**: re-export `docs/openapi.json` after API changes with `curl localhost:8000/openapi.json > docs/openapi.json`.
