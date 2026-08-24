import clsx from "clsx";

export function Card({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={clsx("rounded-md border border-border bg-card shadow-low", className)}>{children}</div>
  );
}

export function CardHeader({ title, action }: { title: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
      <h2 className="text-[15px] font-semibold tracking-tight text-foreground">{title}</h2>
      {action}
    </div>
  );
}
