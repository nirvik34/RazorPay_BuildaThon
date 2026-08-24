"use client";

import { useGuard } from "@/lib/store";
import { PageHeader } from "@/components/stat-card";
import { Card, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useToast } from "@/lib/toast";
import type { Category } from "@/lib/types";

const DEMOS: Array<{ label: string; note: string; run: (ingest: ReturnType<typeof useGuard>["ingestRequest"]) => void }> = [
  {
    label: "Normal purchase",
    note: "Sony headphones ₹14,499 → user approval expected",
    run: (ingest) => {
      ingest({ agentId: "claude-shopping-01", product: "Sony WH-1000XM5", merchant: "amazon", amount: 14499, category: "electronics" });
    }
  },
  {
    label: "Over-limit attempt",
    note: "MacBook ₹42,000 vs ₹20,000 limit → auto-block",
    run: (ingest) => {
      ingest({ agentId: "gemini-shopping-02", product: "MacBook Pro 16", merchant: "techmart", amount: 42000, category: "electronics" });
    }
  },
  {
    label: "Intent mismatch",
    note: "Monitor requested · gift card bought → block",
    run: (ingest) => {
      ingest({ agentId: "gpt-assistant-03", product: "Amazon Pay Gift Card ₹10,000", merchant: "flipkart", amount: 10000, category: "gift_cards" });
    }
  },
  {
    label: "Splitting attack",
    note: "3× ~₹9.8K same session → third blocked as circumvention",
    run: (ingest) => {
      const session = `sess_split_${Math.floor(Math.random() * 900 + 100)}`;
      const items = ["Logitech MX Master 3S", "Keychron K3 Keyboard", "Anker USB-C Hub"];
      items.forEach((product, i) =>
        window.setTimeout(() => {
          ingest({
            agentId: "claude-shopping-01",
            product,
            merchant: i === 0 ? "reliancedigital" : "croma",
            amount: 9800 - i * 100,
            category: "electronics",
            sessionId: session
          });
        }, i * 250)
      );
    }
  },
  {
    label: "Compromised burst",
    note: "8 rapid requests → velocity anomaly raised",
    run: (ingest) => {
      for (let i = 0; i < 8; i += 1) {
        window.setTimeout(() => {
          ingest({
            agentId: "claude-shopping-01",
            product: `Flash sale item ${i + 1}`,
            merchant: `dealsite${i % 3}`,
            amount: 1500 + i * 700,
            category: pickCategory(i)
          });
        }, i * 120);
      }
    }
  }
];

function pickCategory(i: number): Category {
  const cats: Category[] = ["electronics", "groceries", "office_supplies", "fashion", "travel", "electronics", "fashion", "travel"];
  return cats[i] ?? "electronics";
}

export default function SettingsPage() {
  const { state, setApiBase, ingestRequest, resetDemo } = useGuard();
  const toast = useToast();

  return (
    <div className="max-w-3xl">
      <PageHeader title="Settings" description="Device configuration and demo controls." />

      <Card className="mb-6">
        <CardHeader title="Backend sync (optional)" />
        <div className="p-5">
          <p className="text-[13px] leading-relaxed text-muted">
            The phone is the trust anchor — the cloud backend is only for sync, analytics and the web APIs.
            Authorization keeps working when this is offline.
          </p>
          <div className="mt-4 flex gap-2">
            <input
              value={state.apiBase}
              onChange={(e) => setApiBase(e.target.value)}
              className="w-full rounded-sm border border-border bg-white px-3 py-2 font-mono text-[13px] outline-none focus:border-brand focus:ring-2 focus:ring-brand/20"
              placeholder="http://localhost:8000"
            />
            <Button
              variant="outline"
              onClick={async () => {
                try {
                  const res = await fetch(`${state.apiBase.replace(/\/$/, "")}/health`, { signal: AbortSignal.timeout(3000) });
                  if (res.ok) toast.push("success", "✓ Backend reachable");
                  else toast.push("danger", "Backend responded with an error");
                } catch {
                  toast.push("info", "Offline — local protection active");
                }
              }}
            >
              TEST CONNECTION
            </Button>
          </div>
        </div>
      </Card>

      <Card className="mb-6">
        <CardHeader title="Demo scenarios" />
        <div className="divide-y divide-border">
          {DEMOS.map((demo) => (
            <div key={demo.label} className="flex items-center justify-between gap-4 px-5 py-3.5">
              <div>
                <div className="text-[13px] font-medium">{demo.label}</div>
                <div className="text-[12px] text-muted">{demo.note}</div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  demo.run(ingestRequest);
                  toast.push("info", "Request sent to local Guard");
                }}
              >
                RUN
              </Button>
            </div>
          ))}
        </div>
      </Card>

      <Card className="border-danger-border">
        <CardHeader title="Danger zone" />
        <div className="flex items-center justify-between p-5">
          <p className="max-w-sm text-[13px] text-muted">Reset all local data back to the demo seed state.</p>
          <Button
            variant="danger"
            size="sm"
            onClick={() => {
              resetDemo();
              toast.push("info", "Local state reset to seed");
            }}
          >
            RESET DEMO DATA
          </Button>
        </div>
      </Card>
    </div>
  );
}

type IngestFn = ReturnType<typeof useGuard>["ingestRequest"];
