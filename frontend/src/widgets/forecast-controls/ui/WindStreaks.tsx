import { motion } from "motion/react";

const STREAKS = [
  { d: "M-40 70 C 180 30, 360 110, 620 60 S 980 20, 1240 80", delay: 0, opacity: 0.5 },
  { d: "M-40 120 C 220 90, 420 160, 700 110 S 1040 70, 1240 130", delay: 1.2, opacity: 0.35 },
  { d: "M-40 170 C 160 150, 380 200, 640 160 S 1000 130, 1240 180", delay: 2.4, opacity: 0.25 },
] as const;

/** Decorative wind flow lines behind the hero. */
export function WindStreaks() {
  return (
    <svg
      aria-hidden
      className="pointer-events-none absolute inset-x-0 top-0 h-full w-full"
      viewBox="0 0 1200 240"
      preserveAspectRatio="none"
      fill="none"
    >
      <defs>
        <linearGradient id="streak" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stopColor="#22d3ee" stopOpacity="0" />
          <stop offset="0.5" stopColor="#22d3ee" />
          <stop offset="1" stopColor="#8b5cf6" stopOpacity="0" />
        </linearGradient>
      </defs>
      {STREAKS.map((streak) => (
        <motion.path
          key={streak.d}
          d={streak.d}
          stroke="url(#streak)"
          strokeWidth={1.2}
          strokeLinecap="round"
          initial={{ pathLength: 0.25, pathOffset: 0, opacity: 0 }}
          animate={{ pathOffset: [0, 1], opacity: [0, streak.opacity, 0] }}
          transition={{ duration: 7, delay: streak.delay, repeat: Infinity, ease: "easeInOut" }}
        />
      ))}
    </svg>
  );
}
