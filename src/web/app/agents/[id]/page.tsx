"use client";

import { useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { useGuard } from "@/lib/store";
import { PageHeader } from "@/components/stat-card";
import { Card, CardHeader } from "@/components/ui/card";
import { AgentStatusPill } from "@/components/status-pill";
import { ActivityTable } from "@/components/activity-table";
import { Button } from "@/components/ui/button";
import { useToast } from "@/lib/toast";
import { formatINR } from "@/lib/format";
import { Snowflake } from "lucide-react";

export default function AgentDetailPage() {
  const params = useParams<{ id: string }>();
  const agentId = params.id;
  const { state, freezeAgent, unfreezeAgent, revokeAgent } = useGuard();
  const toast = useToast();
  const [confirmFreeze, setConfirmFreeze] = useState(false);
  const [confirmRevoke, setConfirmRevoke] = useState(false);

  const agent = state.agents.find((a) => a.agentId === agentId);
  const policy = state.policies.find((p) => p.policyId === agent?.policyId);

  const history = useMemo(
    () =>
      state.transactions
        .filter((r) => r.request.agentId === agentId)
        .sort((a, b) => new Date(b.request.timestamp).getTime() - new Date(a.request.timestamp).getTime()),
    [state.transactions, agentId]
  );

  if (!agent) {
    return (
      <div>
        <PageHeader title="Agent not found" />
        <p className="text-sm text-muted font-mono">{agentId}</p>
      </div>
    );
  }

  const today = history.filter((r) => new Date(r.request.timestamp).toDateString() === new Date().toDateString());
  const spendToday = today.filter((r) => r.outcome === "CAPTURED").reduce((s, r) => s + r.request.amount, 0);
  const blockedCount = history.filter((r) => r.decision.decision === "BLOCK").length;

  return (
    <div>
      <PageHeader title={agent.name} />

      <div className="flex flex-wrap items-center gap-3">
        <AgentStatusPill status={agent.status} />
        <span className="font-mono text-xs text-muted">{agent.agentId}</span>
        <span className="font-mono text-xs text-muted">owner {agent.ownerId}</span>
        {agent.riskState !== "NORMAL" && (
          <span className="rounded-full bg-warning-bg px-2 py-0.5 text-[11px] font-bold text-warning-text">
            RISK STATE: {agent.riskState}
          </span>
        )}
      </div>

      <div className="mt-5 grid max-w-4xl grid-cols-2 gap-4 md:grid-cols-4">
        <Card className="p-4">
          <div className="text-[11px] uppercase tracking-wider text-muted">Trust</div>
          <div className="mt-1 font-mono text-xl font-bold tabular-nums">{agent.trustScore}</div>
        </Card>
        <Card className="p-4">
          <div className="text-[11px] uppercase tracking-wider text-muted">Today</div>
          <div className="mt-1 font-mono text-xl font-bold tabular-nums">
            {today.length} · {formatINR(spendToday)}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-[11px] uppercase tracking-wider text-muted">Authority</div>
          <div className="mt-1 font-mono text-sm font-semibold leading-5 tabular-nums">
            {policy ? `${formatINR(policy.transactionLimit)} / txn` : "—"}
            <br />
            {policy ? `${formatINR(policy.dailyLimit)} / day` : ""}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-[11px] uppercase tracking-wider text-muted">Blocked</div>
          <div className="mt-1 font-mono text-xl font-bold tabular-nums text-danger-text">{blockedCount}</div>
        </Card>
      </div>

      <div className="mt-6 flex gap-3">
        {agent.status === "FROZEN" ? (
          <Button variant="success" onClick={() => { unfreezeAgent(agent.agentId); toast.push("info", "Agent unfrozen"); }}>
            UNFREEZE AGENT
          </Button>
        ) : (
          <Button variant="danger" onClick={() => setConfirmFreeze(true)}>
            <Snowflake className="h-4 w-4" /> FREEZE AGENT
          </Button>
        )}
        {agent.status !== "REVOKED" && (
          <Button variant="outline" onClick={() => setConfirmRevoke(true)}>
            REVOKE ACCESS
          </Button>
        )}
      </div>

      <h3 className="mb-3 mt-8 text-[15px] font-semibold tracking-tight">Decision history</h3>
      <ActivityTable records={history} />

      {confirmFreeze && (
        <ConfirmDialog
          title={`Freeze ${agent.name}?`}
          body="New financial requests will be blocked immediately on this device. Existing payments are unaffected."
          confirmLabel="FREEZE AGENT"
          destructive
          onCancel={() => setConfirmFreeze(false)}
          onConfirm={() => {
            freezeAgent(agent.agentId);
            setConfirmFreeze(false);
            toast.push("danger", "✓ Agent frozen on this device");
          }}
        />
      )}
      {confirmRevoke && (
        <ConfirmDialog
          title={`Revoke access for ${agent.name}?`}
          body="The agent will be unable to submit any payment request until re-registered."
          confirmLabel="REVOKE ACCESS"
          destructive
          onCancel={() => setConfirmRevoke(false)}
          onConfirm={() => {
            revokeAgent(agent.agentId);
            setConfirmRevoke(false);
            toast.push("danger", "Agent access revoked");
          }}
        />
      )}
    </div>
  );
}

function ConfirmDialog({
  title,
  body,
  confirmLabel,
  destructive,
  onCancel,
  onConfirm
}: {
  title: string;
  body: string;
  confirmLabel: string;
  destructive?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy/40 p-4">
      <div className="w-full max-w-sm rounded-md border border-border bg-card p-5 shadow-high">
        <h3 className="text-[15px] font-semibold tracking-tight text-foreground">{title}</h3>
        <p className="mt-2 text-[13px] leading-relaxed text-muted">{body}</p>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={onCancel}>
            CANCEL
          </Button>
          <Button variant={destructive ? "danger" : "brand"} size="sm" onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
