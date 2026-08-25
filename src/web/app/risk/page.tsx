"use client";

import { useMemo } from "react";
import { useGuard } from "@/lib/store";
import { PageHeader, EmptyState } from "@/components/stat-card";
import { Card, CardHeader } from "@/components/ui/card";
import { RiskScale } from "@/components/risk-scale";
import { Button } from "@/components/ui/button";
import { useToast } from "@/lib/toast";
import { formatINR, formatTime } from "@/lib/format";
import { ShieldAlert, Snowflake } from "lucide-react";

interface DerivedAnomaly {
  agentId: string;
  observedTxns: number;
  observedMinutes: number;
  observedAmount: number;
  windowStart: string;
  signals: string[];
}

/** Live behavioural anomaly detection over the real transaction stream. */
function deriveAnomalies(
  transactions: ReturnType<typeof useGuard>["transactions"]
): DerivedAnomaly[] {
  const now = Date.now();
  const out: DerivedAnomaly[] = [];
  const byAgent = new Map<string, typeof transactions>();
  for (const t of transactions) {
    const list = byAgent.get(t.request.agentId) ?? [];
    list.push(t);
    byAgent.set(t.request.agentId, list);
  }
  byAgent.forEach((list, agentId) => {
    const recent = list
      .filter((t) => now - new Date(t.request.timestamp).getTime() <= 10 * 60_000)
      .sort((a, b) => new Date(a.request.timestamp).getTime() - new Date(b.request.timestamp).getTime());
    if (recent.length < 5) return;
    const amount = recent.reduce((s, t) => s + t.request.amount, 0);
    const merchants = new Set(recent.map((t) => t.request.merchant));
    const blocked = recent.filter((t) => t.decision.decision === "BLOCK").length;
    const signals: string[] = [
      `${recent.length} requests within 10 minutes`,
      `${merchants.size} distinct merchant(s)`,
    ];
    if (blocked > 0) signals.push(`${blocked} blocked by policy in window`);
    const hours = new Date().getHours();
    if (hours < 8 || hours >= 21) signals.push("Unusual spending time");
    out.push({
      agentId,
      observedTxns: recent.length,
      observedMinutes: 10,
      observedAmount: amount,
      windowStart: recent[0].request.timestamp,
      signals,
    });
  });
  return out;
}

export default function RiskPage() {
  const { transactions, agents, setAgentStatus } = useGuard();
  const toast = useToast();
  const anomalies = useMemo(() => deriveAnomalies(transactions), [transactions]);
  const frozenAgents = agents.filter((a) => a.status === "FROZEN" || a.status === "REVOKED");

  return (
    <div>
      <PageHeader
        title="Risk"
        description="Live behavioural monitoring across your agents — computed from the real transaction stream."
      />

      <Card className="mb-6 max-w-3xl p-5">
        <div className="text-[11px] font-bold uppercase tracking-wider text-muted">Score reference</div>
        <div className="mt-3">
          <RiskScale score={50} />
        </div>
      </Card>

      {anomalies.length === 0 ? (
        <EmptyState
          title="No active risks."
          body="No agent exceeds velocity thresholds right now. Bursts of 5+ requests in 10 minutes raise an anomaly here."
        />
      ) : (
        <div className="max-w-3xl space-y-5">
          {anomalies.map((anomaly) => {
            const agent = agents.find((a) => a.agentId === anomaly.agentId);
            return (
              <div key={anomaly.agentId} className="rounded-md border border-danger-border border-l-4 border-l-danger bg-card shadow-low">
                <div className="p-5">
                  <div className="flex items-center justify-between">
                    <span className="inline-flex items-center gap-2 rounded-full bg-danger-bg px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-danger-text">
                      <ShieldAlert className="h-3.5 w-3.5" /> High-velocity burst detected
                    </span>
                    <span className="font-mono text-xs text-muted">
                      since {formatTime(anomaly.windowStart)}
                    </span>
                  </div>

                  <h3 className="mt-4 text-[15px] font-semibold text-foreground">
                    {agent?.name ?? anomaly.agentId}
                  </h3>

                  <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
                    <Metric label="Current activity" value={`${anomaly.observedTxns} txns / ${anomaly.observedMinutes} min`} danger />
                    <Metric label="Exposure in window" value={formatINR(anomaly.observedAmount)} danger />
                    <Metric label="Agent status" value={agent?.status ?? "UNKNOWN"} />
                  </div>

                  <div className="mt-4 rounded-sm border border-border bg-background p-3">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-muted">Signals</div>
                    <ul className="mt-1.5 space-y-1 text-[13px] text-foreground">
                      {anomaly.signals.map((s) => (
                        <li key={s} className="flex items-center gap-2">
                          <span className="h-1 w-1 rounded-full bg-brand" /> {s}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="mt-4 flex items-center justify-between">
                    <span className="text-[13px] text-muted">
                      Recommendation: <span className="font-semibold text-danger-text">Freeze agent</span>
                    </span>
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={async () => {
                        await setAgentStatus(anomaly.agentId, "FROZEN");
                        toast.push("danger", "✓ Agent frozen — requests will be blocked");
                      }}
                    >
                      <Snowflake className="h-4 w-4" /> FREEZE AGENT
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {frozenAgents.length > 0 && (
        <Card className="mt-8 max-w-3xl">
          <CardHeader title="Contained agents" />
          <div className="divide-y divide-border text-[13px]">
            {frozenAgents.map((a) => (
              <div key={a.agentId} className="flex items-center justify-between px-5 py-3 text-muted">
                <span className="font-mono text-xs">{a.agentId}</span>
                <span className="font-semibold text-danger-text">{a.status}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function Metric({ label, value, danger }: { label: string; value: string; danger?: boolean }) {
  return (
    <div className="rounded-sm border border-border bg-background p-3">
      <div className="text-[10px] font-bold uppercase tracking-wider text-muted">{label}</div>
      <div className={`mt-1 font-mono text-sm font-semibold tabular-nums ${danger ? "text-danger-text" : "text-foreground"}`}>
        {value}
      </div>
    </div>
  );
}
