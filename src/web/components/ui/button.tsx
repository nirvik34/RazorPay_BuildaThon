"use client";

import React from "react";
import clsx from "clsx";

type Variant = "brand" | "success" | "danger" | "outline" | "ghost" | "navy";
type Size = "sm" | "md" | "lg";

const variants: Record<Variant, string> = {
  brand: "bg-brand text-white hover:bg-brandDark",
  success: "bg-success text-white hover:bg-success/90",
  danger: "bg-danger text-white hover:bg-danger/90",
  outline: "border border-border bg-white text-foreground hover:bg-background",
  ghost: "text-muted hover:bg-background hover:text-foreground",
  navy: "bg-navy text-white hover:bg-navy-light"
};

const sizes: Record<Size, string> = {
  sm: "h-8 px-3 text-[13px]",
  md: "h-9 px-4 text-sm",
  lg: "h-11 px-5 text-sm"
};

export function Button({
  variant = "brand",
  size = "md",
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size }) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-sm font-medium tracking-tight transition-colors disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    />
  );
}
