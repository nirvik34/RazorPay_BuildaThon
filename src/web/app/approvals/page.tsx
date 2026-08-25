"use client";

import { useGuard } from "@/lib/store";
import { PageHeader, EmptyState } from "@/components/stat-card";
import { GuardDecisionCard } from "@/components/guard-decision-card";
import { useToast } from "@/lib/toast";
import { ShieldCheck } from "lucide-react";

export default function ApprovalsPage() {
  const { pending, decide, connected } = useGuard();
  const toast = useToast();

  return (
    <div className="max-w-2xl">
      <PageHeader title="Approvals" description="Requests waiting for your decision. Nothing is charged without you." />

      {pending.length === 0 ? (
        <div className="space-y-6">
          <EmptyState
            title={connected ? "You're all caught up." : "Backend offline."}
            body={
              connected
                ? "No AI agent currently needs your approval. Local protection stays active."
                : "Start the backend to receive live agent approval requests."
            }
          />
          <div className="flex items-center justify-center gap-2 text-[12px] text-muted">
            <ShieldCheck className="h-4 w-4 text-success" />
            Every request is re-checked against policy before it reaches this queue.
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {pending.map(({ request, decision }) => (
            <GuardDecisionCard
              key={request.requestId}
              record={{ request, decision, outcome: "NOT_ATTEMPTED", decidedBy: "user" }}
              onAccept={async () => {
                if (await decide(request.requestId, true)) {
                  toast.push("success", "✓ Approved — checkout link released to the agent");
                } else {
                  toast.push("danger", "Decision failed — is the backend running?");
                }
              }}
              onReject={async () => {
                if (await decide(request.requestId, false)) {
                  toast.push("danger", "Transaction rejected and recorded");
                } else {
                  toast.push("danger", "Decision failed — is the backend running?");
                }
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
