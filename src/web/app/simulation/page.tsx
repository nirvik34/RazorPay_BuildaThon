"use client";

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useGuard, type SimulationReport } from "@/lib/store";
import { PageHeader, StatCard } from "@/components/stat-card";
import { Card, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { formatCompactINR, formatINR } from "@/lib/format";
import { FlaskConical } from "lucide-react";

const REASON_LABELS: Record<string, string> = {
  CATEGORY_BLOCKED: "Category blocked",
  LIMIT_TRANSACTION_EXCEEDED: "Over transaction limit",
  LIMIT_DAILY_EXCEEDED: "Over daily limit",
  CIRCUMVENTION_DETECTED: "Circumvention",
  INTENT_MISMATCH: "Intent mismatch",
  AGENT_FROZEN: "Agent frozen",
  NEW_MERCHANT: "New merchant review",
  AMOUNT_REQUIRES_APPROVAL: "Amount approval",
  HIGH_RISK: "High risk review",
  AUTO_APPROVED: "Auto-approved"
};

const STAGES = ["Agent request", "Authority", "Policy", "Risk", "Decision"];

export default function SimulationPage() {
  const { policy, runSimulation } = useGuard();
  const [report, setReport] = useState<SimulationReport | null>(null);
  const [running, setRunning] = useState(false);

  const run = async () => {
    setRunning(true);
    const result = await runSimulation(10000, 42);
    setReport(result);
    setRunning(false);
  };

  const chartData = report
    ? (Object.entries(report.byReason) as [string, number][])
        .map(([code, count]) => ({ code: REASON_LABELS[code] ?? code, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 6)
    : [];

  return (
    <div>
      <PageHeader
        title="Policy simulation"
        description="Test your policy against 10,000 synthetic agent requests before trusting it with real money."
        action={
          <Button variant="brand" size="lg" onClick={() => run()} disabled={running}>
            <FlaskConical className="h-4 w-4" /> {running ? "EVALUATING…" : "RUN SIMULATION"}
          </Button>
        }
      />

      {running && (
        <Card className="max-w-3xl p-5">
          <div className="text-[13px] text-muted">Evaluating request…</div>
          <ul className="mt-3 space-y-1.5 font-mono text-[12px] text-muted">
            <li>✓ Agent identity</li>
            <li>✓ Authority</li>
            <li>✓ Policy</li>
            <li>● Risk analysis</li>
            <li>○ Decision</li>
          </ul>
        </Card>
      )}

      {!report && !running && (
        <Card className="max-w-3xl p-5">
          <p className="text-sm leading-relaxed text-muted">
            The simulator replays the current policy against a deterministic mix of legitimate purchases,
            over-limit attempts, intent mismatches, new merchants, transaction-splitting attacks and
            compromised-agent bursts. Results are computed locally — no data leaves this device.
          </p>
        </Card>
      )}

      {report && (
        <>
          <div className="grid max-w-none grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Requests" value={report.total.toLocaleString("en-IN")} />
            <StatCard label="Allowed" value={report.allowed.toLocaleString("en-IN")} tone="neutral" />
            <StatCard label="Approval required" value={report.approvalRequired.toLocaleString("en-IN")} tone="warning" />
            <StatCard label="Blocked" value={report.blocked.toLocaleString("en-IN")} tone="danger" />
          </div>

          <div className="mt-5 rounded-md border border-success-border border-l-4 border-l-success bg-card p-5 shadow-low md:max-w-md">
            <div className="text-[11px] font-bold uppercase tracking-wider text-success-text">Potential policy violations prevented</div>
            <div className="mt-1 font-mono text-2xl font-bold tabular-nums">{formatINR(report.preventedAmount)}</div>
            <div className="mt-1 text-[12px] text-muted">Synthetic dataset — not real savings.</div>
          </div>

          <div className="mt-6 grid max-w-none grid-cols-1 gap-6 xl:grid-cols-2">
            <Card>
              <CardHeader title="Decision pipeline" />
              <div className="space-y-0 p-5">
                {[
                  { label: STAGES[0], detail: `${report.stages.received} requests received` },
                  { label: STAGES[1], detail: `${report.stages.authority} stopped by agent authority` },
                  { label: STAGES[2], detail: `${report.stages.policy} stopped by hard policy` },
                  { label: STAGES[3], detail: `${report.stages.risk} stopped by risk/intent signals` },
                  { label: STAGES[4], detail: `${report.allowed} allowed · ${report.approvalRequired} approval · ${report.blocked} blocked` }
                ].map((stage, i) => (
                  <div key={stage.label}>
                    <div className="flex items-baseline gap-3">
                      <span className="font-mono text-[10px] font-bold text-brand">{String(i + 1).padStart(2, "0")}</span>
                      <span className="w-32 text-[13px] font-semibold">{stage.label}</span>
                      <span className="text-[12px] text-muted">{stage.detail}</span>
                    </div>
                    {i < STAGES.length - 1 && <div className="ml-[7px] h-4 w-px bg-border" />}
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <CardHeader title="Outcomes by reason" />
              <div className="h-72 p-4">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} layout="vertical" margin={{ left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E4E7EC" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 11, fill: "#667085" }} tickFormatter={(v) => formatCompactINR(v)} axisLine={{ stroke: "#E4E7EC" }} tickLine={false} />
                    <YAxis type="category" dataKey="code" width={150} tick={{ fontSize: 11, fill: "#667085" }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ borderRadius: 10, borderColor: "#E4E7EC", fontSize: 12 }} />
                    <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                      {chartData.map((entry) => (
                        <Cell
                          key={entry.code}
                          fill={entry.code.includes("blocked") || entry.code.includes("limit") || entry.code.includes("Circumvention") || entry.code.includes("mismatch") ? "#F04438" : "#2563EB"}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
