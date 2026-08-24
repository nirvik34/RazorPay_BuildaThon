"use client";

import { useParams } from "next/navigation";
import { useGuard } from "@/lib/store";
import { Card, CardHeader } from "@/components/ui/card";
import { StatusPill } from "@/components/status-pill";
import { formatClock, formatDay, formatINR } from "@/lib/format";

export default function AuditDetailPage() {
  const params = useParams<{ id: string }>();
  const requestId = params.id;
  const { state } = useGuard();

  const record = state.transactions.find((r) => r.request.requestId === requestId);
  const events = (state.audit[requestId] ?? []).slice().sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime());
  const agent = state.agents.find((a) => a.agentId === record?.request.agentId);

  if (!record) {
    return (
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Transaction not found</h1>
        <p className="mt-2 font-mono text-sm text-muted">{requestId}</p>
      </div>
    );
  }

  const blockReason = record.decision.reasonCodes.find((r) => r.severity === "block");

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <h1 className="font-mono text-xl font-semibold tracking-tight">{record.request.requestId}</h1>
        <StatusPill decision={record.decision.decision} outcome={record.outcome} />
      </div>

      <Card className="max-w-3xl">
        <CardHeader title="Transaction" />
        <div className="grid grid-cols-2 gap-6 p-5 md:grid-cols-4">
          <Meta label="Amount" value={formatINR(record.request.amount)} big mono />
          <Meta label="Merchant" value={record.request.merchant} big />
          <Meta label="Agent" value={agent?.name ?? record.request.agentId} big />
          <Meta label="Product" value={record.request.product} big />
          <Meta label="Session" value={record.request.sessionId} mono />
          <Meta label="Policy" value={`v${record.decision.policyVersion}`} mono />
          <Meta label="Risk score" value={`${record.decision.riskScore}/100`} mono />
          <Meta
            label="Authorization"
            value={record.authorization?.authorizationId ?? (record.decision.decision === "BLOCK" ? "not issued" : "—")}
            mono
          />
        </div>
        {record.decision.decision === "USER_APPROVAL" && (
          <div className="border-t border-border px-5 py-4">
            {record.request.intentId && (
              <p className="text-[13px] italic text-muted">
                Intent: “{state.intents.find((i) => i.intentId === record.request.intentId)?.goal}”
              </p>
            )}
            <p className="mt-1 text-[12px] font-mono text-muted">
              intent match {record.decision.intentScore} · circumvention {record.decision.circumventionScore}
            </p>
          </div>
        )}
        {blockReason && (
          <div className="border-t border-border px-5 py-4">
            <p className="text-[13px] font-medium text-danger-text">{blockReason.label}</p>
            <p className="mt-0.5 font-mono text-[11px] uppercase tracking-wide text-muted">{blockReason.code}</p>
          </div>
        )}
      </Card>

      <h3 className="mb-3 mt-8 text-[15px] font-semibold tracking-tight max-w-3xl">
        Timeline — {formatDay(record.request.timestamp)}
      </h3>
      <Card className="max-w-3xl p-5">
        <ol className="relative space-y-4 border-l border-border pl-5">
          {events.map((event) => (
            <li key={event.eventId} className="relative">
              <span className="absolute -left-[23.5px] top-1 h-2 w-2 rounded-full bg-brand" />
              <div className="flex items-baseline gap-3">
                <span className="font-mono text-xs tabular-nums text-muted">{formatClock(event.at)}</span>
                <span className="text-[13px] font-medium text-foreground">{event.label}</span>
              </div>
              {event.detail && <div className="ml-[68px] font-mono text-[11px] text-muted">{event.detail}</div>}
            </li>
          ))}
        </ol>
      </Card>

      <p className="mt-4 max-w-3xl font-mono text-[11px] leading-relaxed text-muted">
        reason_codes: [{record.decision.reasonCodes.map((r) => r.code).join(", ")}]
      </p>
    </div>
  );
}

function Meta({ label, value, big, mono }: { label: string; value: string; big?: boolean; mono?: boolean }) {
  return (
    <div>
      <div className="text-[10px] font-bold uppercase tracking-wider text-muted">{label}</div>
      <div className={`mt-1 ${mono ? "font-mono" : ""} ${big ? "text-[15px] font-semibold" : "text-[13px]"} capitalize-first`}>
        {value}
      </div>
    </div>
  );
}
