import clsx from "clsx";
import type { AgentStatus, DecisionType, PaymentOutcome, RiskLevel } from "@/lib/types";

type PillTone = "success" | "danger" | "warning" | "info" | "neutral";

const tones: Record<PillTone, string> = {
  success: "bg-success-bg text-success-text border border-success-border",
  danger: "bg-danger-bg text-danger-text border border-danger-border",
  warning: "bg-warning-bg text-warning-text border border-warning-border",
  info: "bg-info-bg text-info-text border border-info-border",
  neutral: "bg-background text-muted border border-border"
};

export function Pill({ tone, children }: { tone: PillTone; children: React.ReactNode }) {
  return (
    <span className={clsx("inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold tracking-wide", tones[tone])}>
      {children}
    </span>
  );
}

export function StatusPill({ decision, outcome }: { decision: DecisionType; outcome?: PaymentOutcome }) {
  if (decision === "BLOCK") return <Pill tone="danger">BLOCKED</Pill>;
  if (decision === "ALLOW") return <Pill tone="success">APPROVED</Pill>;
  if (!outcome || outcome === "NOT_ATTEMPTED") return <Pill tone="warning">PENDING</Pill>;
  if (outcome === "DENIED") return <Pill tone="danger">REJECTED</Pill>;
  if (outcome === "CAPTURED") return <Pill tone="success">APPROVED</Pill>;
  return <Pill tone="info">PROCESSING</Pill>;
}

export function AgentStatusPill({ status }: { status: AgentStatus }) {
  if (status === "ACTIVE") return <Pill tone="info">ACTIVE</Pill>;
  if (status === "FROZEN") return <Pill tone="danger">FROZEN</Pill>;
  return <Pill tone="danger">REVOKED</Pill>;
}

export function RiskPill({ level }: { level: RiskLevel }) {
  const tone: PillTone =
    level === "LOW" ? "success" : level === "MEDIUM" ? "warning" : "danger";
  return <Pill tone={tone}>{level}</Pill>;
}
