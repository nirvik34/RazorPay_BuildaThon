"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";
import { useGuard } from "@/lib/store";
import { PageHeader } from "@/components/stat-card";
import { Card, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useToast } from "@/lib/toast";
import type { Category, Policy } from "@/lib/types";

const ALL_CATEGORIES: Category[] = [
  "electronics",
  "groceries",
  "office_supplies",
  "fashion",
  "travel",
  "gift_cards",
  "gambling",
  "cryptocurrency"
];

export default function PoliciesPage() {
  const { policy: current, savePolicy } = useGuard();
  const toast = useToast();
  const [draft, setDraft] = useState<Policy | null>(current);
  const [showJson, setShowJson] = useState(false);

  useEffect(() => {
    if (current && !draft) setDraft(current);
  }, [current, draft]);

  if (!draft) {
    return (
      <div>
        <PageHeader title="Policies" />
        <p className="text-sm text-muted">
          {current === null ? "Loading policy from backend…" : "Backend offline — start it to manage policies."}
        </p>
      </div>
    );
  }

  const toggleCategory = (cat: Category) => {
    setDraft((prev) => {
      const blocked = prev.blockedCategories.includes(cat);
      return {
        ...prev,
        blockedCategories: blocked
          ? prev.blockedCategories.filter((c) => c !== cat)
          : [...prev.blockedCategories, cat]
      };
    });
  };

  return (
    <div>
      <PageHeader title="Policies" description="Hard constraints enforced locally on this device. No model can override them." />

      <div className="grid max-w-5xl grid-cols-1 gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader title="Spending authority" />
          <div className="space-y-4 p-5">
            <NumberField label="Per transaction" value={draft.transactionLimit} onChange={(v) => setDraft({ ...draft, transactionLimit: v })} />
            <NumberField label="Daily" value={draft.dailyLimit} onChange={(v) => setDraft({ ...draft, dailyLimit: v })} />
            <NumberField label="Monthly" value={draft.monthlyLimit} onChange={(v) => setDraft({ ...draft, monthlyLimit: v })} />
          </div>
        </Card>

        <Card>
          <CardHeader title="Category rules" />
          <div className="p-5">
            <div className="text-[11px] font-bold uppercase tracking-wider text-muted">Allowed categories</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {ALL_CATEGORIES.map((cat) => {
                const blocked = draft.blockedCategories.includes(cat);
                return (
                  <button
                    key={cat}
                    onClick={() => toggleCategory(cat)}
                    className={clsx(
                      "rounded-full px-3 py-1.5 text-[12px] font-medium capitalize",
                      blocked ? "border border-danger-border bg-danger-bg text-danger-text line-through" : "border border-success-border bg-success-bg text-success-text"
                    )}
                  >
                    {blocked ? "✕" : "✓"} {cat.replace("_", " ")}
                  </button>
                );
              })}
            </div>

            <div className="mt-6 text-[11px] font-bold uppercase tracking-wider text-muted">Require approval</div>
            <div className="mt-2 space-y-2.5">
              <CheckRow label="New merchant" checked={draft.approvalRules.newMerchant} onChange={(v) => setDraft({ ...draft, approvalRules: { ...draft.approvalRules, newMerchant: v } })} />
              <CheckRow label="International merchant" checked={draft.approvalRules.international} onChange={(v) => setDraft({ ...draft, approvalRules: { ...draft.approvalRules, international: v } })} />
              <CheckRow label="High risk requests" checked={draft.approvalRules.highRisk} onChange={(v) => setDraft({ ...draft, approvalRules: { ...draft.approvalRules, highRisk: v } })} />
              <NumberField label="Amount above (₹)" value={draft.approvalRules.amountAbove} onChange={(v) => setDraft({ ...draft, approvalRules: { ...draft.approvalRules, amountAbove: v } })} />
            </div>
          </div>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader
            title="Rule preview"
            action={
              <Button variant="ghost" size="sm" onClick={() => setShowJson(!showJson)}>
                {showJson ? "HIDE JSON" : "POLICY JSON"}
              </Button>
            }
          />
          <div className="space-y-3 p-5">
            <RuleRow when="Transaction amount" op="IS GREATER THAN" value={`₹${draft.transactionLimit}`} then="Block automatically" />
            <RuleRow when="Daily exposure" op="EXCEEDS" value={`₹${draft.dailyLimit}`} then="Block automatically" />
            <RuleRow when="Category" op="IS IN" value={draft.blockedCategories.map((c) => c.replace("_", " ")).join(", ") || "none"} then="Block automatically" />
            <RuleRow when="Merchant" op="IS NEW" value="" then="Require user approval" />
            <RuleRow when="Amount" op="IS AT LEAST" value={`₹${draft.approvalRules.amountAbove}`} then="Require user approval" />
            {showJson && (
              <pre className="overflow-x-auto rounded-sm border border-border bg-navy p-4 font-mono text-[11px] leading-relaxed text-[#D0D5DD]">
                {JSON.stringify(draft, null, 2)}
              </pre>
            )}
          </div>
        </Card>
      </div>

      <div className="sticky bottom-4 mt-6 flex max-w-5xl justify-end">
        <Button
          variant="brand"
          size="lg"
          className="shadow-medium"
          onClick={() => {
            savePolicy(draft);
            toast.push("success", `✓ Policy saved · active on this device`);
          }}
        >
          SAVE POLICY
        </Button>
      </div>
    </div>
  );
}

function NumberField({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <label className="block">
      <span className="text-[12px] font-medium capitalize text-muted">{label}</span>
      <input
        type="number"
        value={value}
        min={0}
        step={500}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-1 w-full rounded-sm border border-border bg-white px-3 py-2 font-mono text-sm tabular-nums outline-none focus:border-brand focus:ring-2 focus:ring-brand/20"
      />
    </label>
  );
}

function CheckRow({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-center gap-2.5 text-[13px] text-foreground">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded border-border accent-[#2563EB]"
      />
      {label}
    </label>
  );
}

function RuleRow({ when, op, value, then }: { when: string; op: string; value: string; then: string }) {
  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-sm border border-border bg-background px-3 py-2.5 text-[13px]">
      <span className="font-semibold uppercase tracking-wide text-[10px] text-brand">WHEN</span>
      <span>{when}</span>
      <span className="font-semibold uppercase tracking-wide text-[10px] text-brand">{op}</span>
      {value && <span className="font-mono font-medium">{value}</span>}
      <span className="ml-auto font-semibold uppercase tracking-wide text-[10px] text-purple">THEN</span>
      <span className="capitalize">{then.toLowerCase()}</span>
    </div>
  );
}
