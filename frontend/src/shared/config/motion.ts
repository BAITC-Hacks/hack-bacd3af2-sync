import type { Transition, Variants } from "motion/react";

export const EASE_OUT_EXPO = [0.22, 1, 0.36, 1] as const;

export const baseTransition: Transition = { duration: 0.55, ease: EASE_OUT_EXPO };

export const fadeSlideUp: Variants = {
  hidden: { opacity: 0, y: 14 },
  visible: { opacity: 1, y: 0 },
};
