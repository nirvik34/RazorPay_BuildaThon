"use client";

import React, { createContext, useCallback, useContext, useState } from "react";
import { CheckCircle2, Info, XCircle } from "lucide-react";

type Variant = "success" | "danger" | "info";

interface Toast {
  id: number;
  variant: Variant;
  message: string;
}

interface ToastContextValue {
  push: (variant: Variant, message: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const styles: Record<Variant, string> = {
  success: "bg-white border-success-border text-foreground",
  danger: "bg-white border-danger-border text-foreground",
  info: "bg-white border-info-border text-foreground"
};

const icons: Record<Variant, React.ReactNode> = {
  success: <CheckCircle2 className="h-4 w-4 text-success" />,
  danger: <XCircle className="h-4 w-4 text-danger" />,
  info: <Info className="h-4 w-4 text-info" />
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const push = useCallback((variant: Variant, message: string) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, variant, message }]);
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3500);
  }, []);

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div className="fixed bottom-6 right-6 z-50 flex w-80 flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`flex items-center gap-2 rounded-md border px-3 py-2.5 text-sm shadow-medium ${styles[t.variant]}`}
          >
            {icons[t.variant]}
            <span>{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside ToastProvider");
  return ctx;
}
