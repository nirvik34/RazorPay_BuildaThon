"use client";

import Link from "next/link";
import type { Agent, Policy, TransactionRecord } from "@/lib/types";
import { formatINR } from "@/lib/format";
import { AgentStatusPill } from "@/components/status-pill";
import { Button } from "@/components/ui/button";

export function AgentCard({ agent, policy, transactions }: { agent: Agent; policy?: Policy; transactions: TransactionRecord[] }) {
  const today = transactions.filter(
    (r) => r.request.agentId === agent.agentId && new Date(r.request.timestamp).toDateString() === new Date().toDateString()
  );
  const captured = today.filter((r) => r.outcome === "CAPTURED");
  const spend = captured.reduce((sum, r) => sum + r.request.amount, 0);

  return (
    <div className="rounded-md border border-border bg-card p-5 shadow-low">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-purple-bg text-[12px] font-bold text-purple">AI</div>
          <div>
            <div className="text-sm font-semibold text-foreground">{agent.name}</div>
            <div className="font-mono text-[11px] text-muted">{agent.agentId}</div>
          </div>
        </div>
        <AgentStatusPill status={agent.status} />
      </div>

      <div className="mt-4 flex items-center justify-between text-[13px]">
        <span className="text-muted">Trust score</span>
        <span className="font-mono font-semibold tabular-nums text-foreground">{agent.trustScore}</span>
      </div>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-background">
        <div
          className={agent.trustScore >= 85 ? "h-full rounded-full bg-success" : agent.trustScore >= 70 ? "h-full rounded-full bg-warning" : "h-full rounded-full bg-danger"}
          style={{ width: `${agent.trustScore}%` }}
        />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 rounded-sm border border-border bg-background p-3 text-[12px]">
        <div>
          <div className="text-muted">Today</div>
          <div className="font-mono font-semibold tabular-nums text-foreground">
            {today.length} txns · {formatINR(spend)}
          </div>
        </div>
        <div>
          <div className="text-muted">Authority</div>
          <div className="font-mono font-semibold tabular-nums text-foreground">
            {policy ? `${formatINR(policy.transactionLimit)} / txn` : "—"}
          </div>
          <div className="font-mono text-muted">{policy ? `${formatINR(policy.dailyLimit)} / day` : ""}</div>
        </div>
      </div>

      <Link href={`/agents/${agent.agentId}`} className="mt-4 block">
        <Button variant="outline" size="sm" className="w-full">
          VIEW AGENT
        </Button>
      </Link>
    </div>
  );
}
