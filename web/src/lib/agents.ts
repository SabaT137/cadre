import {
  Compass, Database, KanbanSquare, Receipt, Sparkles, Users, type LucideIcon,
} from "lucide-react";
import type { AgentName, Responder } from "./types";

export interface AgentTheme {
  name: Responder;
  label: string;
  title: string;          // card title, e.g. "HR Agent"
  tagline: string;        // sidebar one-liner
  icon: LucideIcon;
  accent: string;         // top border / solid accent
  tint: string;           // icon tile background
  text: string;           // icon / accent text
  ring: string;
  capabilities: string[];
  examples: string[];
}

export const AGENT_THEME: Record<Responder, AgentTheme> = {
  hr: {
    name: "hr", label: "HR", title: "HR Agent", tagline: "Contracts, onboarding paperwork",
    icon: Users, accent: "bg-violet-500", tint: "bg-violet-50", text: "text-violet-600", ring: "ring-violet-200",
    capabilities: ["Contract drafting", "New-hire details", "Custom clauses", "Job descriptions"],
    examples: [
      "Draft the hourly consultant contract for Sara Malik, UI/UX Designer, USD 12/hour, 1 year, effective today.",
      "Which contract templates do we have?",
    ],
  },
  devops: {
    name: "devops", label: "DevOps", title: "DevOps Agent", tagline: "IT assets, servers, incidents",
    icon: Database, accent: "bg-blue-500", tint: "bg-blue-50", text: "text-blue-600", ring: "ring-blue-200",
    capabilities: ["SQL queries", "IT assets & warranties", "Servers & cloud cost", "Incidents & deployments"],
    examples: [
      "Which laptops have warranties expiring in the next 90 days, and who are they assigned to?",
      "Which servers cost the most per month?",
    ],
  },
  finance: {
    name: "finance", label: "Finance", title: "Finance Agent", tagline: "Invoices and billing",
    icon: Receipt, accent: "bg-orange-500", tint: "bg-orange-50", text: "text-orange-600", ring: "ring-orange-200",
    capabilities: ["Client invoices (PDF)", "Hours × rate billing", "Tax & discounts", "Recurring invoices"],
    examples: [
      "Invoice Isekaiverse for October: 40 h frontend at $15 and 25 h backend at $18, 5% tax.",
      "Show our recent invoices.",
    ],
  },
  pm: {
    name: "pm", label: "PM", title: "PM Agent", tagline: "Jira insights, sprint planning",
    icon: KanbanSquare, accent: "bg-teal-500", tint: "bg-teal-50", text: "text-teal-600", ring: "ring-teal-200",
    capabilities: ["Jira project status", "Team velocity", "Sprint planning", "Deadline risk"],
    examples: [
      "For project QR, plan 2-week sprints to finish all open work by 15 December using the board's velocity.",
      "What's in the active sprint for the QR board?",
    ],
  },
  developer: {
    name: "developer", label: "Developer", title: "Solution Engineer Agent", tagline: "Research, architecture, ideas",
    icon: Compass, accent: "bg-emerald-500", tint: "bg-emerald-50", text: "text-emerald-600", ring: "ring-emerald-200",
    capabilities: ["Technical research", "Architecture exploration", "Solution design", "Diagrams (Mermaid)"],
    examples: [
      "Help me shape an internal hackathon voting app, include a Mermaid architecture diagram.",
      "Compare Postgres and MongoDB for an event-sourcing system.",
    ],
  },
  supervisor: {
    name: "supervisor", label: "Orchestrator", title: "Orchestrator", tagline: "Routes your request",
    icon: Sparkles, accent: "bg-brand", tint: "bg-accent-soft", text: "text-accent", ring: "ring-accent/30",
    capabilities: [], examples: [],
  },
};

export const AGENT_ORDER: AgentName[] = ["hr", "devops", "finance", "pm", "developer"];

export function agentTheme(name?: string | null): AgentTheme {
  return AGENT_THEME[(name as Responder) ?? "supervisor"] ?? AGENT_THEME.supervisor;
}

export const HOME_SUGGESTIONS: { text: string; agent: AgentName }[] = [
  { text: "Draft an employment contract for a senior software engineer.", agent: "hr" },
  { text: "Which laptops have warranties expiring this quarter?", agent: "devops" },
  { text: "Create an invoice for Isekaiverse for $500 of website work.", agent: "finance" },
  { text: "Plan sprints for project QR to finish by 15 December.", agent: "pm" },
  { text: "We need to build a new employee onboarding platform.", agent: "developer" },
];

