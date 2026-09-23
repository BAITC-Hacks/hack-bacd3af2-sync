import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/shared/lib";

import { Spinner } from "./Spinner";

const buttonVariants = cva(
  "relative inline-flex select-none items-center justify-center gap-2 overflow-hidden rounded-xl font-medium whitespace-nowrap transition-[transform,box-shadow,background-color,opacity] duration-200 ease-out disabled:cursor-not-allowed disabled:opacity-60 active:scale-[0.98]",
  {
    variants: {
      variant: {
        primary:
          "bg-gradient-to-r from-cyan-400 via-sky-500 to-violet-500 text-slate-950 shadow-[0_10px_30px_-10px_rgb(34_211_238/0.7)] hover:shadow-[0_14px_40px_-10px_rgb(34_211_238/0.9)]",
        secondary: "border border-line bg-white/5 text-ink hover:bg-white/10",
        ghost: "text-ink-muted hover:bg-white/5 hover:text-ink",
      },
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-10 px-4 text-sm",
        lg: "h-12 px-6 text-[15px]",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    isLoading?: boolean;
    loadingText?: string;
    icon?: ReactNode;
  };

export function Button({
  className,
  variant,
  size,
  isLoading = false,
  loadingText,
  icon,
  children,
  disabled,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || isLoading}
      aria-busy={isLoading}
      {...props}
    >
      {isLoading ? <Spinner size="sm" /> : icon}
      <span>{isLoading && loadingText ? loadingText : children}</span>
    </button>
  );
}
