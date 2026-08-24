"use client";

import { useGuard } from "@/lib/store";
import { PageHeader, EmptyState } from "@/components/stat-card";
import { GuardDecisionCard } from "@/components/guard-decision-card";
import { evaluateFull } from "@/lib/engine";
import { useToast } from "@/lib/toast";
import { ShieldCheck } from "lucide-react";

export default function ApprovalsPage() {
  const { state, decide } = useGuard();
  const toast = useToast();

  const pending = state.transactions
    .filter((r) => r.decision.decision === "USER_APPROVAL" && !r.userActionAt)
    .sort((a, b) => new Date(b.request.timestamp).getTime() - new Date(a.request.timestamp).getTime());

  return (
    <div className="max-w-2xl">
      <PageHeader title="Approvals" description="Requests waiting for your decision. Nothing is charged without you." />

      {pending.length === 0 ? (
        <div className="space-y-6">
          <EmptyState title="You're all caught up." body="No AI agent currently needs your approval." />
          <div className="flex items-center justify-center gap-2 text-[12px] text-muted">
            <ShieldCheck className="h-4 w-4 text-success" />
            Local Guard active — hard policy checks run on this device even when offline.
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {pending.map((rec) => {
            const agent = state.agents.find((a) => a.agentId === rec.request.agentId);
            const intent = state.intents.find((i) => i.intentId === rec.request.intentId);
            const evaluation = agent
              ? evaluateFull({
                  request: rec.request,
                  agent,
                  policy: state.policies[0],
                  history: state.transactions,
                  intents: state.intents,
                  now: new Date(rec.request.timestamp)
                })
              : null;
            return (
              <GuardDecisionCard
                key={rec.request.requestId}
                record={rec}
                agentName={agent?.name ?? rec.request.agentId}
                intent={intent}
                risk={evaluation?.risk}
                onAccept={() => {
                  decide(rec.request.requestId, true);
                  toast.push("success", "✓ Agent approved for this purchase");
                }}
                onReject={() => {
                  decide(rec.request.requestId, false);
                  toast.push("danger", "Transaction rejected and recorded");
                }}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
