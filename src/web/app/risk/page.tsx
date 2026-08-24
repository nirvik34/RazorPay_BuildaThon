"use client";

import { useGuard } from "@/lib/store";
import { PageHeader, EmptyState } from "@/components/stat-card";
import { Card, CardHeader } from "@/components/ui/card";
import { RiskScale } from "@/components/risk-scale";
import { Button } from "@/components/ui/button";
import { useToast } from "@/lib/toast";
import { formatINR, formatTime } from "@/lib/format";
import { ShieldAlert, Snowflake } from "lucide-react";

export default function RiskPage() {
  const { state, freezeAgent, dismissAnomaly } = useGuard();
  const toast = useToast();
  const open = state.anomalies.filter((a) => !a.dismissed);
  const dismissed = state.anomalies.filter((a) => a.dismissed);

  return (
    <div>
      <PageHeader
        title="Risk"
        description="Why is the Guard concerned? Behavioural anomalies and security signals across your agents."
      />

      <Card className="mb-6 max-w-3xl p-5">
        <div className="text-[11px] font-bold uppercase tracking-wider text-muted">Score reference</div>
        <div className="mt-3">
          <RiskScale score={50} />
        </div>
      </Card>

      {open.length === 0 ? (
        <EmptyState title="No active risks." body="Your agents are behaving within their current baseline." />
      ) : (
        <div className="max-w-3xl space-y-5">
          {open.map((anomaly) => {
            const agent = state.agents.find((a) => a.agentId === anomaly.agentId);
            return (
              <div key={anomaly.anomalyId} className="rounded-md border border-danger-border border-l-4 border-l-danger bg-card shadow-low">
                <div className="p-5">
                  <div className="flex items-center justify-between">
                    <span className="inline-flex items-center gap-2 rounded-full bg-danger-bg px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-danger-text">
                      <ShieldAlert className="h-3.5 w-3.5" /> Critical agent anomaly
                    </span>
                    <span className="font-mono text-xs text-muted">{formatTime(anomaly.createdAt)}</span>
                  </div>

                  <h3 className="mt-4 text-[15px] font-semibold text-foreground">{agent?.name ?? anomaly.agentId}</h3>

                  <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
                    <Metric label="Current activity" value={`${anomaly.observedTxns} txns / ${anomaly.observedMinutes} min`} danger />
                    <Metric label="Normal baseline" value={`${anomaly.baselineTxnsPerDayMin}–${anomaly.baselineTxnsPerDayMax} txns / day`} />
                    <Metric label="Exposure" value={formatINR(anomaly.observedAmount)} danger />
                  </div>

                  <div className="mt-4 rounded-sm border border-border bg-background p-3">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-muted">Signals</div>
                    <ul className="mt-1.5 space-y-1 text-[13px] text-foreground">
                      {anomaly.signals.map((s) => (
                        <li key={s} className="flex items-center gap-2">
                          <span className="h-1 w-1 rounded-full bg-purple" /> {s}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="mt-4 flex items-center justify-between">
                    <span className="text-[13px] text-muted">
                      Recommendation: <span className="font-semibold text-danger-text">Freeze agent</span>
                    </span>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm" onClick={() => dismissAnomaly(anomaly.anomalyId)}>
                        DISMISS
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => {
                          freezeAgent(anomaly.agentId);
                          toast.push("danger", "✓ Agent frozen on this device");
                        }}
                      >
                        <Snowflake className="h-4 w-4" /> FREEZE AGENT
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {dismissed.length > 0 && (
        <Card className="mt-8 max-w-3xl">
          <CardHeader title="Handled events" />
          <div className="divide-y divide-border text-[13px]">
            {dismissed.map((a) => (
              <div key={a.anomalyId} className="flex items-center justify-between px-5 py-3 text-muted">
                <span className="font-mono text-xs">{a.agentId}</span>
                <span>
                  {a.observedTxns} txns in {a.observedMinutes} min · handled
                </span>
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
