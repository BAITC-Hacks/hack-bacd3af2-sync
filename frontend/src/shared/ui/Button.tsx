import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/shared/lib";

import { Spinner } from "./Spinner";

const buttonVariants = cva(
  "relative inline-flex select-none items-center justify-center gap-2.5 overflow-hidden whitespace-nowrap transition-[transform,background-color,border-color,opacity,filter] duration-200 ease-out disabled:cursor-not-allowed disabled:opacity-60 active:scale-[0.985]",
  {
    variants: {
      variant: {
        primary:
          "rounded-[14px] bg-gradient-to-b from-cream-strong to-[#c9ad7e] font-display text-[#1b1a14] shadow-[inset_0_1px_0_rgb(255_255_255/0.45),0_10px_24px_-14px_rgb(0_0_0/0.9)] hover:brightness-[1.04]",
        secondary: "rounded-xl border border-line bg-panel-soft text-ink hover:border-line-strong",
        ghost: "rounded-xl text-ink-muted hover:bg-panel-soft hover:text-ink",
      },
      size: {
        sm: "h-8 px-3 text-[12.5px]",
        md: "h-10 px-4 text-sm",
        lg: "h-[60px] px-6 text-[17px]",
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
    trailingIcon?: ReactNode;
  };

export function Button({
  className,
  variant,
  size,
  isLoading = false,
  loadingText,
  icon,
  trailingIcon,
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
      {!isLoading ? trailingIcon : null}
    </button>
  );
}
