"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useGuard } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { ShieldCheck, Loader2 } from "lucide-react";

export default function LoginPage() {
  const { login, register, ownerExists, user, connected } = useGuard();
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user) router.replace("/");
  }, [user, router]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    const err =
      mode === "login"
        ? await login(email, password)
        : await register(name, email, password);
    setBusy(false);
    if (err) setError(err);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-navy">
            <ShieldCheck className="h-6 w-6 text-[#0D94FB]" />
          </div>
          <h1 className="mt-4 text-xl font-bold tracking-tight text-foreground">AgentPay Guard</h1>
          <p className="mt-1 text-[13px] text-muted">
            Sign in to manage your AI agents' spending authority.
          </p>
        </div>

        <div className="rounded-md border border-border bg-card p-6 shadow-low">
          {!ownerExists && mode === "login" && (
            <div className="mb-4 rounded-sm border border-info-border bg-info-bg px-3 py-2 text-[12px] text-info-text">
              No owner account yet — create one below.
            </div>
          )}

          <form onSubmit={submit} className="space-y-4">
            {mode === "register" && (
              <label className="block">
                <span className="text-[12px] font-medium text-muted">Name</span>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  minLength={1}
                  className="mt-1 w-full rounded-sm border border-border bg-white px-3 py-2 text-sm outline-none focus:border-brand focus:ring-2 focus:ring-brand/20"
                  placeholder="Your name"
                />
              </label>
            )}
            <label className="block">
              <span className="text-[12px] font-medium text-muted">Email</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="mt-1 w-full rounded-sm border border-border bg-white px-3 py-2 text-sm outline-none focus:border-brand focus:ring-2 focus:ring-brand/20"
                placeholder="you@example.com"
              />
            </label>
            <label className="block">
              <span className="text-[12px] font-medium text-muted">Password</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className="mt-1 w-full rounded-sm border border-border bg-white px-3 py-2 text-sm outline-none focus:border-brand focus:ring-2 focus:ring-brand/20"
                placeholder="min. 8 characters"
              />
            </label>

            {error && (
              <div className="rounded-sm border border-danger-border bg-danger-bg px-3 py-2 text-[12px] text-danger-text">
                {error}
              </div>
            )}

            <Button type="submit" variant="brand" size="lg" className="w-full" disabled={busy}>
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              {mode === "login" ? "SIGN IN" : "CREATE OWNER ACCOUNT"}
            </Button>
          </form>

          <div className="mt-4 text-center text-[12px] text-muted">
            {mode === "login" ? (
              <button
                className="font-medium text-brand hover:underline"
                onClick={() => {
                  setMode("register");
                  setError(null);
                }}
              >
                First time? Create the owner account
              </button>
            ) : (
              <button
                className="font-medium text-brand hover:underline"
                onClick={() => {
                  setMode("login");
                  setError(null);
                }}
              >
                Already have an account? Sign in
              </button>
            )}
          </div>
        </div>

        <p className="mt-4 text-center font-mono text-[11px] text-muted">
          {connected ? "● backend connected" : "● backend offline — start uvicorn first"}
        </p>
      </div>
    </div>
  );
}
