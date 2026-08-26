"use client";

import { useState } from "react";
import { useGuard } from "@/lib/store";
import { PageHeader } from "@/components/stat-card";
import { Card, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useToast } from "@/lib/toast";
import type { Category } from "@/lib/types";

interface Demo {
  label: string;
  note: string;
  requests: Array<{ agentId: string; product: string; merchant: string; amount: number; category: Category; sessionId?: string }>;
}

const DEMOS: Demo[] = [
  {
    label: "Normal purchase",
    note: "Sony headphones ₹14,499 → approval expected",
    requests: [
      { agentId: "claude-shopping-01", product: "Sony WH-1000XM5", merchant: "amazon", amount: 14499, category: "electronics" },
    ],
  },
  {
    label: "Over-limit attempt",
    note: "MacBook ₹42,000 vs ₹20,000 limit → auto-block",
    requests: [
      { agentId: "gemini-shopping-02", product: "MacBook Pro 14", merchant: "techmart", amount: 42000, category: "electronics" },
    ],
  },
  {
    label: "Intent mismatch",
    note: "Gift card purchase → category blocked",
    requests: [
      { agentId: "gpt-assistant-03", product: "Amazon Pay Gift Card ₹10,000", merchant: "flipkart", amount: 10000, category: "gift_cards" },
    ],
  },
  {
    label: "Splitting attack",
    note: "3× ~₹9.8K same session → third blocked as circumvention",
    requests: [0, 1, 2].map((i) => ({
      agentId: "claude-shopping-01",
      product: ["Logitech MX Master 3S", "Keychron K3 Keyboard", "Anker USB-C Hub"][i],
      merchant: i === 0 ? "reliancedigital" : "croma",
      amount: 9800 - i * 100,
      category: "electronics" as Category,
      sessionId: `sess_split_${Date.now()}`,
    })),
  },
  {
    label: "Compromised burst",
    note: "8 rapid requests → velocity anomaly on Risk page",
    requests: Array.from({ length: 8 }, (_, i) => ({
      agentId: "claude-shopping-01",
      product: `Flash deal item ${i + 1}`,
      merchant: `dealsite${i % 3}`,
      amount: 1500 + i * 700,
      category: (i % 2 === 0 ? "electronics" : "groceries") as Category,
      sessionId: `sess_burst_${Date.now()}_${i}`,
    })),
  },
];

export default function SettingsPage() {
  const { apiBase, setApiBase, connected, sendAgentRequest } = useGuard();
  const toast = useToast();
  const [draftUrl, setDraftUrl] = useState(apiBase);
  const [busy, setBusy] = useState(false);

  const runDemo = async (demo: Demo) => {
    setBusy(true);
    let last = null;
    for (const req of demo.requests) {
      last = await sendAgentRequest({ ...req, currency: "INR" });
    }
    setBusy(false);
    if (last) {
      toast.push(
        last.decision === "BLOCK" ? "danger" : "info",
        `${demo.label}: ${last.decision.replace("_", " ")}`
      );
    } else {
      toast.push("danger", "Request failed — is the backend running?");
    }
  };

  return (
    <div className="max-w-3xl">
      <PageHeader title="Settings" description="Backend connection, typography preferences, and real agent-request triggers." />

      {/* Typography & Font Info */}
      <Card className="mb-6">
        <CardHeader title="Base Typeface & Typography" />
        <div className="p-5">
          <div className="flex items-center justify-between p-3.5 rounded-xl border border-blue-200 bg-blue-50/50">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[14px] font-bold text-slate-900">Metropolis</span>
                <span className="bg-blue-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
                  Design Standard
                </span>
              </div>
              <div className="text-[12px] text-slate-600 mt-1">
                Modern, geometric sans-serif font applied project-wide for Razorpay aesthetic consistency.
              </div>
            </div>
          </div>
        </div>
      </Card>

      <Card className="mb-6">
        <CardHeader title="Backend connection" />
        <div className="p-5">
          <p className="text-[13px] leading-relaxed text-muted">
            This dashboard is a live view over the Guard backend — there is no local demo data.
            The phone (Android app) remains the trust anchor; the backend is the message bus.
          </p>
          <div className="mt-4 flex gap-2">
            <input
              value={draftUrl}
              onChange={(e) => setDraftUrl(e.target.value)}
              className="w-full rounded-sm border border-border bg-white px-3 py-2 font-mono text-[13px] outline-none focus:border-brand focus:ring-2 focus:ring-brand/20"
              placeholder="http://127.0.0.1:8000"
            />
            <Button
              variant="brand"
              onClick={() => {
                setApiBase(draftUrl.replace(/\/$/, ""));
                toast.push("info", "Reconnecting…");
              }}
            >
              CONNECT
            </Button>
          </div>
          <div className="mt-3 flex items-center gap-2 text-[12px] font-medium">
            <span className={connected ? "text-success-text" : "text-danger-text"}>
              ● {connected ? `CONNECTED — ${apiBase}` : "OFFLINE — start the backend (uvicorn app.main:app)"}
            </span>
          </div>
        </div>
      </Card>

      <Card className="mb-6">
        <CardHeader title="Real agent-request triggers" />
        <div className="divide-y divide-border">
          {DEMOS.map((demo) => (
            <div key={demo.label} className="flex items-center justify-between gap-4 px-5 py-3.5">
              <div>
                <div className="text-[13px] font-medium">{demo.label}</div>
                <div className="text-[12px] text-muted">{demo.note}</div>
              </div>
              <Button variant="outline" size="sm" disabled={busy || !connected} onClick={() => runDemo(demo)}>
                SEND
              </Button>
            </div>
          ))}
        </div>
        <p className="px-5 py-3 text-[12px] text-muted">
          These POST real payment requests to the backend — they hit the actual Guard engine,
          appear in Activity/Audit, and push approvals to the Android app via LiveSync.
        </p>
      </Card>
    </div>
  );
}
