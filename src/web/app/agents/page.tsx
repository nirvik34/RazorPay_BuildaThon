"use client";

import { useGuard } from "@/lib/store";
import { PageHeader } from "@/components/stat-card";
import { AgentCard } from "@/components/agent-card";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { Plus } from "lucide-react";

export default function AgentsPage() {
  const { agents, policy, transactions } = useGuard();
  

  return (
    <div>
      <PageHeader
        title="Agents"
        description="Registered AI agents with explicit identity and scoped authority."
        action={
          <Link href="/policies">
            <Button variant="outline" size="sm">
              <Plus className="h-4 w-4" /> Manage policies
            </Button>
          </Link>
        }
      />

      <div className="grid max-w-5xl grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
        {agents.map((agent) => (
          <AgentCard
            key={agent.agentId}
            agent={agent}
            policy={policy ?? undefined}
            transactions={transactions}
          />
        ))}
        <div className="rounded-md border border-dashed border-border bg-white p-5 text-[13px] text-muted">
          <div className="font-semibold text-foreground">Connect a new agent</div>
          <p className="mt-1.5 leading-relaxed">
            Register an agent identity with its public key and assign a policy. New agents start with least
            privilege.
          </p>
        </div>
      </div>

      <p className="mt-8 text-[12px] text-muted">
        Default policy: {policy ? `v${policy.version} · ${policy.transactionLimit}/txn · ${policy.dailyLimit}/day` : ""}
      </p>
    </div>
  );
}
