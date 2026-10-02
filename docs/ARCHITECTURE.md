# Stixor Office Multi-Agent System: Architecture & Build Record (as built, Oct 2026)

> This document records **what was built and how**, for anyone joining the project.
> To build a new frontend, use `README.md` (the API contract) and `docs/openapi.json`.

## 1. Purpose
One internal assistant for Stixor Technologies. Staff chat in natural language. A **supervisor** agent sends each
message to the right **department agent**, and that agent uses its own tools to do the work:

| Agent | Who uses it | What it does |
|---|---|---|
| HR | HR team | Drafts new-hire contracts from `.docx` templates (built-in hourly consultant contract, plus uploads). Fills placeholders and applies custom clause edits. |
| DevOps | IT / DevOps | Answers questions about the IT operations database with safe, read-only SQL. |
| Finance | Finance | Generates client invoices as PDF on the Stixor letterhead, rebuilt from the original Word/PDF invoice. |
| PM | Project managers | Reads the PM's **own Jira** (read-only). Reports status and velocity, plans sprints against a deadline, exports plans. |
| Developer | Developers | Brainstorming, architecture, specs, Mermaid diagrams. |

There are two kinds of users:
- **admin**: every agent, plus the admin console (stats, agents on/off, activity, users, integrations).
- **user**: only the agents an admin assigned to them.

## 2. Stack
- **Python 3.11**, in a venv at `.venv`. The system Python is 3.9, which is too old for LangChain 1.x.
- **LangGraph 1.2 / LangChain 1.4**: the agent graph. Checkpoints go to `data/checkpoints.db` through `AsyncSqliteSaver`.
- **FastAPI**: the backend API. Auth uses JWT (PyJWT), bcrypt passwords, and Fernet-encrypted secrets.
- **SQLAlchemy 2**:
  - app DB: `data/app.db` (users, threads, runs, agent settings, Jira connections, clients, invoices)
  - demo IT DB: `data/devops.db`, read-only
- **Documents**:
  - python-docx for contracts
  - ReportLab for invoice PDFs
  - pypdf, used once to pull the logo and signature out of the sample invoice
  - openpyxl for Excel exports
- **Jira**: httpx async client against Jira Cloud REST v3 and Agile 1.0, using OAuth 2.0 (3LO) or an API token.
- **Streamlit**: two reference UIs (`ui/user_app.py`, `ui/admin_app.py`). A new frontend will replace them.

## 3. LLMs: one OpenAI-compatible gateway (vLLM)
`LLM_BASE_URL=https://occgocg0g00g8wggko88kw8s.138.252.175.111.sslip.io/v1`. Each model has its own key, set in `.env`.

| Role | Model id | Verified gateway capabilities |
|---|---|---|
| Supervisor | `glm-5.2` | Chat ✔. JSON-schema output ✔. Forced tool calls are **unreliable**: they come back empty for some prompts, consistently for "delete …". |
| Department agents | `qwen3.5` (serves `qwen-35b-w8a8`) | Chat ✔. JSON-schema output ✔. **No tool calling**: vLLM runs without `--tool-call-parser`, so every `tool_choice` mode returns 400. |

These findings drove two design decisions:
- **Supervisor routing uses guided JSON** (`response_format: json_schema`), not tool calls.
- **Tool agents run a custom JSON-ReAct loop** (`app/agents/json_react.py`):
  - Each step, Qwen returns `{thought, action, args, answer}`, constrained by a schema whose `action` enum is the tool names plus `final_answer`.
  - The loop runs the named LangChain tool and feeds the result back as `Observation:`.
  - It is capped at 8–10 steps, and on the last step it forces `final_answer`.
  - Bad JSON or bad arguments are sent back to the model as an observation, so it can correct itself.
  - `WORKER_NATIVE_TOOLS=true` switches to `langchain.agents.create_agent`, for when the gateway enables tool calling.

## 4. Agent graph
```
START → supervisor ──► hr | devops | finance | pm | developer ──► END
                  └──► END   (respond: greeting/capabilities · refused: department not permitted)
```
- **Registry** (`app/agents/registry.py`): one `AgentSpec` per agent, with name, label, icon, routing description, UI summary, node and tools. The graph, the supervisor prompt, the admin "agents" endpoint and the UI all read from it. **To add an agent: add a node, its tools, a prompt and one registry entry.**
- **State** (`app/graph/state.py`): messages, `active_agent` (keeps follow-ups with the same agent), `department_hint` (UI override), `attached_template_id`, `available_agents` (enabled and allowed for this user), `user_id`/`username`, `route`, `route_reason`, `artifacts` and `trace` (the agent's steps).
- **Supervisor** (`app/graph/supervisor.py`):
  - If the UI picked an agent the user is allowed, the message goes straight there and no LLM is called.
  - If the UI picked an agent the user isn't allowed, the request is refused, again without an LLM call.
  - Otherwise GLM chooses from `available_agents`, `respond`, or `refused` (offered only if the user lacks access to something). It sees the last 6 messages.
  - If routing fails, it falls back to the active or first available agent.
- **Department nodes** (`app/agents/subagents.py`): each runs its loop over the last 20 messages, as plain text. It appends one AI message, `name=<agent>`, with `additional_kwargs.artifacts`, so history can re-render downloads.
- **Per-user tool context** (`app/agents/context.py`): a `ContextVar` passes the current user into tools. Finance uses it to record who created an invoice; PM uses it to pick that user's Jira connection.

## 5. Departments in detail
### HR: contracts (`tools/hr_tools.py`, `services/docx_filler.py`, `services/template_store.py`)
- **Detection**: positional `[●]`, `[insert …]`, `{{field}}`, `____`, and empty `Label:` lines are found and numbered, each with its section heading and surrounding text. This works across the body, tables, headers and footers.
- **Formatting-safe replacement**: even when a placeholder is split across several pieces of text in the Word file, the value is written into the first piece and keeps its formatting.
- **Empty bullets**: unused bullet placeholders are removed, and a multi-line value expands into several bullets.
- **Clause edits**: `replace`, `insert_after` and `delete` on paragraph indices support custom terms (for example, a 15-day notice period).
- **Missed fields**: the tool warns about unfilled body placeholders, and the agent fills them in on a second pass.
- **Template problems flagged, not silently changed**: "Monthly Salary … per hour" and "two [●] year(s)".

### DevOps: read-only SQL (`tools/sql_tools.py`, `services/db.py`, `scripts/seed_devops_db.py`)
- **Demo schema**: departments, employees, assets, servers, deployments, incidents, software_licenses, access_requests.
- **Guard**: sqlglot allows a single SELECT, CTE or UNION over known tables only. It rejects DML, DDL, PRAGMA and system tables, and adds `LIMIT 200`.
- **Connection**: read-only (SQLite `mode=ro` plus `query_only`; Postgres read-only session plus a timeout).
- **Other databases**: set `DEVOPS_DATABASE_URL`.

### Finance: invoices (`tools/finance_tools.py`, `services/invoice_pdf.py`, `services/invoice_store.py`, `config/finance.yaml`)
- **Layout**: copied from the sample PDF (US Letter):
  - logo, the spaced "S T I X O R" wordmark, address and top band
  - invoice number and date, a justified intro paragraph ("…services provided to "{client}" for {service}…")
  - bank table, INVOICE title, optional line items with subtotal, tax, discount and Payable Now
  - signature block and the purple footer with contact details
- **Config, not the LLM**: bank accounts, signatory, number format `STX-{year}-{seq:04d}`, payment terms and currency symbols all live in `config/finance.yaml`. The LLM picks a bank account by id only. **Totals are computed in code** (`calculate_invoice`).
- **Signature image**: the CEO's signature was extracted to `storage/invoice_assets/signature.png`, but `apply_signature_image: false` by default.
- **Data**: `clients` and `invoices` tables. Supports duplicating an invoice for recurring billing.

### PM: Jira (`integrations/jira/*`, `tools/pm_tools.py`, `services/sprint_planner.py`)
- **Connections, one per user, encrypted**:
  1. OAuth 2.0 (3LO) "Connect Jira". Scopes: `read:jira-work read:jira-user offline_access read:board-scope:jira-software read:sprint:jira-software read:project:jira read:issue-details:jira read:jql:jira`. Callback is `/integrations/jira/callback`, then a redirect to `USER_UI_URL?jira=connected`. Tokens refresh automatically.
  2. API token: site, email and token, checked with `/myself`.
  3. PAT, for Server/Data Center.
  - Dev bootstrap: the admin user is connected to `stixor.atlassian.net` through `JIRA_BOOTSTRAP_*`.
- **Client**: read-only by design (GET plus `POST /rest/api/3/search/jql`). Handles pagination, backs off on 429/5xx, and caches results for 5 minutes. It finds custom fields per site, so story points are read from both "Story Points" (company-managed) and "Story point estimate" (team-managed).
- **Velocity**: completed points and issues per closed sprint.
- **Planner** (deterministic):
  - Orders by priority, then rank, with blockers before what they block.
  - Fills sprints by capacity, with a buffer (default 15%), up to the deadline.
  - Reports overflow, extra sprints needed, projected completion and the capacity needed.
  - Flags risks: unestimated issues, oversized issues, blockers outside the scope, overloaded assignees, unassigned work.
  - **Automatically switches to issue counts** when fewer than 50% of issues are estimated. This is common in the Stixor Jira: only about 2% of QR issues are estimated.
- **Export**: XLSX (with a summary sheet), CSV or MD.

## 6. Users, auth, tracking
- **`users` table**: role `admin|user`, `allowed_agents`, `is_active`. The first admin comes from `ADMIN_USERNAME`/`ADMIN_PASSWORD` in `.env`; more can be added in the admin console or with `scripts/create_user.py`.
- **JWT**: HS256, `APP_SECRET_KEY`, 12-hour expiry. `require_admin` protects `/admin/*`.
- **Threads**: each belongs to its creator. Other users get 404.
- **Agent settings**: admins can turn agents on and off.
- **`agent_runs` table**: one row per chat, with agent, status (ok, error or refused), latency, LLM calls, tokens (from a `UsageCallbackHandler` on `usage_metadata`), tool-call count, route reason, the full trace and any error. This feeds `/admin/stats` and `/admin/runs`.

## 7. Repository map
```
app/config.py, llm.py, prompts.py, bootstrap.py
app/auth/{security.py, deps.py}          app/db/{models.py, session.py}
app/graph/{state.py, supervisor.py, builder.py}
app/agents/{registry.py, subagents.py, json_react.py, context.py}
app/tools/{hr_tools.py, sql_tools.py, finance_tools.py, pm_tools.py}
app/services/{docx_filler.py, template_store.py, db.py, invoice_pdf.py, invoice_store.py, sprint_planner.py, usage.py}
app/integrations/jira/{client.py, store.py, oauth.py}
app/api/{main.py, schemas.py, routes/{auth, chat, templates, finance, integrations, admin}.py}
config/finance.yaml      ui/{common.py, user_app.py, admin_app.py}      scripts/{seed_devops_db.py, create_user.py}
storage/{templates, outputs, invoice_assets}      data/ (generated DBs)      docs/{ARCHITECTURE.md, openapi.json}
tests/ (41 tests: docx filler, SQL guard, JSON loop and routing, auth and permissions, invoices, planner, Jira client)
```

## 8. Verified behaviour (live, against the real gateway and Jira)
- **Routing**: correct on mixed prompts, follow-ups stay with the same agent, greetings are answered directly, and disallowed departments are politely refused.
- **HR**: asks for missing CNIC and address, fills all 42 placeholders, applies the custom notice period, writes six job-duty bullets, and flags template issues.
- **DevOps**: correct joins and date filters, SQL shown, and delete/drop requests refused.
- **Finance**: "40h × $15 + 25h × $18 + 5% tax" gives **$1,102.50** and a PDF matching the letterhead.
- **PM**: QR project, deadline 15 Dec. Found 89 open issues, measured velocity of about 45 issues per sprint, produced a 2-sprint plan, flagged one assignee at about 80% load and 17 unassigned issues, and exported XLSX.
- **Admin console**: KPIs, charts, agent toggles, run drill-down with steps, user management and integrations.

## 9. Known limits / next steps
- **Downloads**: any logged-in user who has a file id can download that file. Files aren't yet tied to an owner (planned: add `owner_id` to outputs).
- **Speed**: each agent reply takes about 20–70 seconds on the gateway. `/chat/stream` sends a `route` event early, so the UI can show which agent is working.
- **CORS**: currently `*`. Restrict it to the new frontend's origin before deploying.
- **Connect Jira button**: needs the Atlassian OAuth app to be registered and `JIRA_OAUTH_CLIENT_ID`/`SECRET` set. Until then, PMs use API tokens.
- **Credentials**: the Jira token and admin password were shared in chat. Rotate them, and use strong values in production.
- **Bank details**: copied from the sample (a US bank with a Pakistani-format IBAN). Finance needs to confirm them.
