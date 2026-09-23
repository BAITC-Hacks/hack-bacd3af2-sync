import { motion } from "motion/react";
import type { ReactNode } from "react";

import { baseTransition, fadeSlideUp } from "@/shared/config";

type RevealProps = {
  children: ReactNode;
  delay?: number;
  className?: string;
};

/** Fade + slide-in on mount. Used to stagger dashboard cards. */
export function Reveal({ children, delay = 0, className }: RevealProps) {
  return (
    <motion.div
      className={className}
      variants={fadeSlideUp}
      initial="hidden"
      animate="visible"
      transition={{ ...baseTransition, delay }}
    >
      {children}
    </motion.div>
  );
}
