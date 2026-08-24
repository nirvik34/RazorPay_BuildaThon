import clsx from "clsx";

export function StatCard({
  label,
  value,
  sub,
  tone = "neutral",
  icon
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "neutral" | "warning" | "danger" | "brand";
  icon?: React.ReactNode;
}) {
  const accents: Record<string, string> = {
    neutral: "",
    warning: "border-l-4 border-l-warning",
    danger: "border-l-4 border-l-danger",
    brand: "border-l-4 border-l-brand"
  };
  return (
    <div className={clsx("rounded-md border border-border bg-card p-5 shadow-low", accents[tone])}>
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-muted">{label}</span>
        {icon}
      </div>
      <div className="mt-2 font-mono text-2xl font-bold tracking-tight text-foreground tabular-nums">{value}</div>
      {sub && <div className="mt-1 text-[13px] text-muted">{sub}</div>}
    </div>
  );
}

export function PageHeader({ title, description, action }: { title: string; description?: string; action?: React.ReactNode }) {
  return (
    <div className="mb-6 flex items-start justify-between">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
        {description && <p className="mt-1 max-w-xl text-sm text-muted">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-md border border-dashed border-border bg-white px-8 py-14 text-center">
      <p className="text-[15px] font-semibold text-foreground">{title}</p>
      <p className="mt-1.5 max-w-xs text-sm text-muted">{body}</p>
    </div>
  );
}
