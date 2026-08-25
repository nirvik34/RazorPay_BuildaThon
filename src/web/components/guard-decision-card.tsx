"use client";

import clsx from "clsx";
import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import type { Intent, RiskAssessment, TransactionRecord } from "@/lib/types";
import { formatINR, formatTime } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { RiskScale } from "@/components/risk-scale";
import { RiskPill } from "@/components/status-pill";

export function GuardDecisionCard({
  record,
  agentName,
  intent,
  risk,
  onAccept,
  onReject
}: {
  record: TransactionRecord;
  agentName?: string;
  intent?: Intent;
  risk?: RiskAssessment;
  onAccept?: () => void;
  onReject?: () => void;
}) {
  const { request, decision } = record;
  const checks = decision.reasonCodes.filter((r) => r.severity !== "block");
  const blockReason = decision.reasonCodes.find((r) => r.severity === "block");

  return (
    <article
      className={clsx(
        "overflow-hidden rounded-md border border-border bg-card shadow-low",
        decision.decision === "BLOCK" ? "border-l-4 border-l-danger" : "border-l-4 border-l-warning"
      )}
    >
      <div className="p-5">
        <div className="flex items-center justify-between">
          {decision.decision === "BLOCK" ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-danger-bg px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-danger-text">
              <XCircle className="h-3.5 w-3.5" /> Blocked by policy
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-warning-bg px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-warning-text">
              <AlertTriangle className="h-3.5 w-3.5" /> Action required
            </span>
          )}
          <span className="font-mono text-xs text-muted">{request.requestId}</span>
        </div>

        <div className="mt-4 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-purple-bg text-[12px] font-bold text-purple">
            AI
          </div>
          <div>
            <div className="text-sm font-semibold text-foreground">{agentName ?? record.request.agentId}</div>
            <div className="font-mono text-[11px] text-muted">{formatTime(request.timestamp)}</div>
          </div>
        </div>

        <div className="mt-4">
          <div className="text-[15px] font-semibold text-foreground">{request.product}</div>
          <div className="text-[13px] capitalize text-muted">{request.merchant}</div>
        </div>

        <div className="mt-3 font-mono text-3xl font-bold tracking-tight text-foreground tabular-nums">
          {formatINR(request.amount)}
        </div>

        <hr className="my-4 border-border" />

        {intent && (
          <div className="mb-4 rounded-sm border border-[#D6BBFB] bg-purple-bg p-3">
            <div className="text-[10px] font-bold uppercase tracking-wider text-purple">User intent</div>
            <div className="mt-1 text-[13px] italic text-foreground">“{intent.goal}”</div>
            <div className="mt-1.5 font-mono text-[11px] text-muted">
              budget {formatINR(intent.budget)} · category {intent.category}
            </div>
          </div>
        )}

        <div className="space-y-1.5">
          <div className="text-[10px] font-bold uppercase tracking-wider text-muted">
            {decision.decision === "BLOCK" ? "Why it was blocked" : "Guard checks"}
          </div>
          {(decision.decision === "BLOCK" && blockReason ? [blockReason, ...checks] : checks).map((reason) => (
            <div key={reason.code} className="flex items-start gap-2 text-[13px]">
              {reason.severity === "ok" ? (
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />
              ) : reason.severity === "warn" ? (
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" />
              ) : (
                <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-danger" />
              )}
              <span className={clsx(reason.severity === "block" ? "font-medium text-danger-text" : "text-foreground")}>
                {reason.label}
              </span>
            </div>
          ))}
        </div>

        <div className="mt-4 flex items-center justify-between gap-6 rounded-sm border border-border bg-background px-3 py-2.5">
          <div>
            <div className="text-[10px] font-bold uppercase tracking-wider text-muted">Risk</div>
            <RiskPill level={decision.riskScore < 25 ? "LOW" : decision.riskScore < 50 ? "MEDIUM" : decision.riskScore < 75 ? "HIGH" : "CRITICAL"} />
          </div>
          <RiskScale score={decision.riskScore} compact />
        </div>
        {risk && risk.signals.length > 0 && decision.decision !== "BLOCK" && (
          <ul className="mt-2 list-disc pl-5 text-[11px] leading-relaxed text-muted">
            {risk.signals.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        )}

        {(onAccept || onReject) && decision.decision === "USER_APPROVAL" && !record.userActionAt && (
          <div className="mt-5 grid grid-cols-2 gap-3">
            <Button variant="danger" size="lg" onClick={onReject}>
              REJECT
            </Button>
            <Button variant="success" size="lg" onClick={onAccept}>
              ACCEPT
            </Button>
          </div>
        )}
      </div>
    </article>
  );
}
