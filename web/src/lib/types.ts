// Mirrors the FastAPI contract (see ../README.md §3 and docs/openapi.json).
export type AgentName = "hr" | "devops" | "finance" | "pm" | "developer";
export type Department = "auto" | AgentName;
export type Responder = AgentName | "supervisor";

export interface AgentInfo { name: AgentName; label: string; icon: string; summary: string }

export interface Me {
  id: number;
  username: string;
  full_name: string;
  role: "admin" | "user";
  allowed_agents: AgentName[];
  available_agents: AgentInfo[];
}

export interface FileArtifact {
  type: "file";
  file_id: string;
  filename: string;
  mime?: string;
  invoice_no?: string;
  template_id?: string;
}
export interface SqlArtifact { type: "sql"; query: string; columns: string[]; rows: (string | number | null)[][] }
export interface TableArtifact { type: "table"; title: string; columns: string[]; rows: (string | number | null)[][] }
export type Artifact = FileArtifact | SqlArtifact | TableArtifact;

export interface ChatRequest { message: string; thread_id?: string | null; department?: Department; template_id?: string | null }
export interface ChatResponse { thread_id: string; reply: string; agent: Responder; route_reason: string | null; artifacts: Artifact[] }

export interface ThreadSummary {
  thread_id: string;
  title: string;
  updated_at: string;
  created_at: string;
  agent: AgentName | null;
  turns: number;
}
export interface HistoryMessage { role: "user" | "assistant"; content: string; agent?: Responder | null; artifacts: Artifact[] }
export interface ThreadHistory { thread_id: string; messages: HistoryMessage[] }

export interface TemplateInfo { template_id: string; name: string; description: string; placeholder_count: number; uploaded_at: string }
export interface ClientInfo { id: number; name: string; default_currency: string; email: string }
export interface InvoiceSummary {
  invoice_no: string; client: string; issue_date: string; total: number; currency: string; file_id: string; service_description: string;
}
export interface DocumentInfo {
  file_id: string; filename: string; mime: string; kind: "contract" | "invoice" | "plan" | "file";
  agent: string; thread_id: string; owner: string; created_at: string;
}

export interface JiraStatus {
  oauth_available: boolean; connected: boolean; site_url?: string; account?: string;
  auth_type?: "oauth" | "api_token" | "pat"; connected_at?: string;
}

export interface AdminStats {
  days: number; requests: number; requests_today: number; active_users: number; users_total: number;
  error_rate: number; refused: number; avg_latency_ms: number; p95_latency_ms: number; tokens: number;
  per_agent: Record<string, { runs: number; errors: number; tokens: number; avg_latency_ms: number; p95_latency_ms: number }>;
  per_day: { date: string; agent: string; runs: number }[];
  per_user: { user: string; runs: number }[];
}
export interface TraceStep { thought: string; action: string; args: Record<string, unknown> }
export interface AgentRunRow {
  id: number; created_at: string; user: string; agent: string; status: "ok" | "error" | "refused";
  latency_ms: number; llm_calls: number; tool_calls: number; tokens: number; message: string;
  route_reason: string; trace: TraceStep[]; error: string; thread_id: string;
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
  user_id: number; user: string; auth_type: string; site_url: string; account: string; connected_at: string; expires_at: string | null;
}
export interface Health { status: string; supervisor_model: string; worker_model: string; worker_native_tools: boolean }
