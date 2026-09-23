import { animate, motion, useMotionValue, useReducedMotion, useTransform } from "motion/react";
import { useEffect } from "react";

import { EASE_OUT_EXPO } from "@/shared/config";

type AnimatedNumberProps = {
  value: number;
  /** Must be stable (module-level) — it is captured once by the motion transform. */
  format: (value: number) => string;
  duration?: number;
  className?: string;
};

export function AnimatedNumber({ value, format, duration = 1, className }: AnimatedNumberProps) {
  const shouldReduceMotion = useReducedMotion();
  const motionValue = useMotionValue(0);
  const text = useTransform(motionValue, format);

  useEffect(() => {
    if (shouldReduceMotion) {
      motionValue.set(value);
      return;
    }
    const controls = animate(motionValue, value, { duration, ease: EASE_OUT_EXPO });
    return () => controls.stop();
  }, [value, duration, motionValue, shouldReduceMotion]);

  return <motion.span className={className}>{text}</motion.span>;
}
