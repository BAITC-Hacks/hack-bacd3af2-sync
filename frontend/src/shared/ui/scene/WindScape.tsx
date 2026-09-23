import { useId } from "react";

import { cn } from "@/shared/lib";

/**
 * Cinematic wind-farm landscape, drawn as a static SVG: warm dusk light, fractal-noise clouds,
 * layered jagged ridges with valley fog, and lit turbines. Three crops (hero, sidebar, promo card).
 * Pure vector — no photo licensing, crisp at any size.
 */

type SceneVariant = "hero" | "sidebar" | "card";

type TurbineSpec = {
  x: number;
  hubY: number;
  height: number;
  blade: number;
  /** 1 = crisp, lit foreground turbine; 0 = dissolved in distant haze. */
  depth: number;
  phase: number;
};

type SceneSpec = {
  width: number;
  height: number;
  /** Where the low sun lights the sky from (fractions of width/height). */
  light: [number, number];
  /** Horizontal centre of the foreground hill carrying the main turbines (fraction of width). */
  hillX: number;
  turbines: TurbineSpec[];
};

const SCENES: Record<SceneVariant, SceneSpec> = {
  hero: {
    width: 1600,
    height: 560,
    light: [0.84, 0.5],
    hillX: 0.76,
    turbines: [
      { x: 880, hubY: 318, height: 92, blade: 38, depth: 0.25, phase: 12 },
      { x: 925, hubY: 326, height: 84, blade: 34, depth: 0.25, phase: 70 },
      { x: 1405, hubY: 268, height: 110, blade: 48, depth: 0.45, phase: 40 },
      { x: 1515, hubY: 250, height: 130, blade: 56, depth: 0.5, phase: 95 },
      { x: 1290, hubY: 205, height: 240, blade: 112, depth: 0.9, phase: 58 },
      { x: 1150, hubY: 178, height: 290, blade: 138, depth: 1, phase: 5 },
    ],
  },
  sidebar: {
    width: 240,
    height: 330,
    light: [0.15, 0.38],
    hillX: 0.45,
    turbines: [
      { x: 205, hubY: 228, height: 48, blade: 20, depth: 0.35, phase: 50 },
      { x: 112, hubY: 118, height: 170, blade: 64, depth: 1, phase: 20 },
    ],
  },
  card: {
    width: 320,
    height: 380,
    light: [0.28, 0.42],
    hillX: 0.72,
    turbines: [
      { x: 60, hubY: 268, height: 48, blade: 18, depth: 0.3, phase: 40 },
      { x: 112, hubY: 258, height: 62, blade: 24, depth: 0.4, phase: 95 },
      { x: 232, hubY: 112, height: 240, blade: 80, depth: 1, phase: 65 },
    ],
  },
};

/** Deterministic pseudo-random generator so the landscape is identical on every render. */
function seeded(seed: number): () => number {
  let state = seed % 2147483647;
  return () => {
    state = (state * 16807) % 2147483647;
    return state / 2147483647;
  };
}

/** Jagged mountain ridge: a few large peaks plus fine noise, closed down to the bottom edge. */
function ridgePath(w: number, h: number, base: number, amp: number, seed: number, peaks: number): string {
  const random = seeded(seed);
  const phases = [random() * Math.PI * 2, random() * Math.PI * 2, random() * Math.PI * 2];
  const steps = 90;
  const points: string[] = [];
  for (let i = 0; i <= steps; i += 1) {
    const t = i / steps;
    const shape =
      0.55 * Math.sin(t * peaks * Math.PI + phases[0]!) +
      0.3 * Math.sin(t * peaks * 2.3 * Math.PI + phases[1]!) +
      0.15 * Math.sin(t * peaks * 5.7 * Math.PI + phases[2]!);
    const y = base - amp * shape - amp * 0.1 * (random() - 0.5);
    points.push(`${(t * w).toFixed(1)},${y.toFixed(1)}`);
  }
  return `M0,${h} L${points.join(" L")} L${w},${h} Z`;
}

/** Foreground hill that rises under the main turbines. */
function hillPath(w: number, h: number, centre: number): string {
  const cx = centre * w;
  return `M0,${h} L0,${h * 0.93} C${cx - w * 0.45},${h * 0.9} ${cx - w * 0.2},${h * 0.8} ${cx},${h * 0.79}
          C${cx + w * 0.18},${h * 0.78} ${cx + w * 0.3},${h * 0.86} ${w},${h * 0.88} L${w},${h} Z`;
}

function bladePath(length: number, width: number): string {
  return `M ${-width * 0.5} 0 C ${-width * 0.62} ${-length * 0.35}, ${-width * 0.2} ${-length * 0.82}, 0 ${-length}
          C ${width * 0.16} ${-length * 0.72}, ${width * 0.55} ${-length * 0.32}, ${width * 0.5} 0 Z`;
}

function mix(a: [number, number, number], b: [number, number, number], t: number): string {
  const c = a.map((value, i) => Math.round(value + (b[i]! - value) * t));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}

const HAZE: [number, number, number] = [138, 128, 110];
const LIT: [number, number, number] = [226, 218, 202];
const SHADOW: [number, number, number] = [92, 87, 77];

function Turbine({ spec, id }: { spec: TurbineSpec; id: string }) {
  const { x, hubY, height, blade, depth, phase } = spec;
  const light = mix(HAZE, LIT, depth);
  const shade = mix(HAZE, SHADOW, depth);
  const gradientId = `tower-${id}-${x}`;
  const top = Math.max(0.8, height * 0.011);
  const base = Math.max(1.6, height * 0.026);
  const nacelle = Math.max(2.4, blade * 0.075);
  return (
    <g opacity={0.55 + depth * 0.45}>
      <defs>
        {/* Light comes from the right: the right side of the tower is lit. */}
        <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor={shade} />
          <stop offset="0.55" stopColor={light} />
          <stop offset="1" stopColor={light} />
        </linearGradient>
      </defs>
      <polygon
        points={`${x - top},${hubY} ${x + top},${hubY} ${x + base},${hubY + height} ${x - base},${hubY + height}`}
        fill={`url(#${gradientId})`}
      />
      <rect x={x - nacelle * 0.7} y={hubY - nacelle * 0.42} width={nacelle * 2.2} height={nacelle * 0.84} rx={nacelle * 0.35} fill={light} />
      <g transform={`translate(${x} ${hubY}) rotate(${phase})`}>
        {[0, 120, 240].map((angle) => (
          <path
            key={angle}
            d={bladePath(blade, Math.max(1.8, blade * 0.05))}
            fill={light}
            stroke={shade}
            strokeWidth={Math.max(0.3, blade * 0.004)}
            transform={`rotate(${angle})`}
          />
        ))}
        <circle r={Math.max(1.4, blade * 0.04)} fill={light} />
      </g>
    </g>
  );
}

type WindScapeProps = {
  variant: SceneVariant;
  className?: string;
};

export function WindScape({ variant, className }: WindScapeProps) {
  const id = useId().replace(/:/g, "");
  const { width: w, height: h, light, hillX, turbines } = SCENES[variant];
  // Cloud noise is defined in user units, so scale its frequency with the crop size.
  const scale = 1600 / w;
  const [lx, ly] = light;

  return (
    <svg aria-hidden viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="xMidYMid slice" className={cn("pointer-events-none select-none", className)}>
      <defs>
        <linearGradient id={`sky-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#141411" />
          <stop offset="0.3" stopColor="#332e26" />
          <stop offset="0.55" stopColor="#7d6d57" />
          <stop offset="0.75" stopColor="#9b8a70" />
          <stop offset="1" stopColor="#5a5244" />
        </linearGradient>
        <radialGradient id={`sun-${id}`} cx={lx} cy={ly} r="0.75" gradientTransform={`translate(${lx} ${ly}) scale(1 ${w / h / 2.2}) translate(${-lx} ${-ly})`}>
          <stop offset="0" stopColor="#f3dfbb" stopOpacity="0.85" />
          <stop offset="0.25" stopColor="#d9bd92" stopOpacity="0.45" />
          <stop offset="0.6" stopColor="#8c7658" stopOpacity="0.12" />
          <stop offset="1" stopColor="#8c7658" stopOpacity="0" />
        </radialGradient>

        {/* Clouds: fractal noise → alpha. Two passes: shadowed bodies and sun-lit tops. */}
        <filter id={`clouds-${id}`} x="0" y="0" width="100%" height="100%" colorInterpolationFilters="sRGB">
          <feTurbulence type="fractalNoise" baseFrequency={`${0.0024 * scale} ${0.0095 * scale}`} numOctaves={5} seed={11} />
          <feColorMatrix type="matrix" values="0 0 0 0 0.2  0 0 0 0 0.19  0 0 0 0 0.16  2.6 0 0 0 -1.12" />
        </filter>
        <filter id={`cloudtops-${id}`} x="0" y="0" width="100%" height="100%" colorInterpolationFilters="sRGB">
          <feTurbulence type="fractalNoise" baseFrequency={`${0.0024 * scale} ${0.0095 * scale}`} numOctaves={5} seed={11} />
          <feColorMatrix type="matrix" values="0 0 0 0 0.9  0 0 0 0 0.8  0 0 0 0 0.66  2.8 0 0 0 -1.46" />
        </filter>
        <linearGradient id={`cloudband-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0.05" stopColor="#fff" stopOpacity="0" />
          <stop offset="0.22" stopColor="#fff" stopOpacity="0.9" />
          <stop offset="0.42" stopColor="#fff" stopOpacity="0.75" />
          <stop offset="0.56" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
        <mask id={`cloudmask-${id}`}>
          <rect width={w} height={h} fill={`url(#cloudband-${id})`} />
        </mask>

        <linearGradient id={`fog-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#e6dac3" stopOpacity="0" />
          <stop offset="0.5" stopColor="#e6dac3" stopOpacity="0.28" />
          <stop offset="1" stopColor="#e6dac3" stopOpacity="0" />
        </linearGradient>
        <filter id={`soft-${id}`} x="-5%" y="-60%" width="110%" height="220%">
          <feGaussianBlur stdDeviation={h * 0.018} />
        </filter>
      </defs>

      {/* Sky and low sun */}
      <rect width={w} height={h} fill={`url(#sky-${id})`} />
      <rect width={w} height={h} fill={`url(#sun-${id})`} />

      {/* Clouds, confined to a band above the ridges */}
      <g mask={`url(#cloudmask-${id})`}>
        <rect width={w} height={h} filter={`url(#clouds-${id})`} transform={`translate(0 ${h * 0.012})`} />
        <rect width={w} height={h} filter={`url(#cloudtops-${id})`} opacity="0.85" />
      </g>

      {/* Ridges, far → near, with fog pooling in the valleys */}
      <path d={ridgePath(w, h, h * 0.5, h * 0.07, 7, 3.2)} fill="#7d7464" opacity="0.8" />
      <rect y={h * 0.48} width={w} height={h * 0.12} fill={`url(#fog-${id})`} filter={`url(#soft-${id})`} />
      <path d={ridgePath(w, h, h * 0.57, h * 0.075, 19, 2.6)} fill="#5f594d" opacity="0.92" />
      <rect y={h * 0.56} width={w} height={h * 0.12} fill={`url(#fog-${id})`} filter={`url(#soft-${id})`} />
      <path d={ridgePath(w, h, h * 0.65, h * 0.07, 31, 3.6)} fill="#46433a" />
      <rect y={h * 0.64} width={w} height={h * 0.1} fill={`url(#fog-${id})`} opacity="0.8" filter={`url(#soft-${id})`} />
      <path d={ridgePath(w, h, h * 0.74, h * 0.06, 43, 2.2)} fill="#302f28" />
      <rect y={h * 0.72} width={w} height={h * 0.1} fill={`url(#fog-${id})`} opacity="0.55" filter={`url(#soft-${id})`} />

      {turbines.map((spec) => (
        <Turbine key={`${spec.x}-${spec.hubY}`} spec={spec} id={id} />
      ))}

      {/* Foreground hill (olive-dark) and a thin ground haze */}
      <path d={hillPath(w, h, hillX)} fill="#1d1e17" />
      <rect y={h * 0.84} width={w} height={h * 0.16} fill={`url(#fog-${id})`} opacity="0.35" filter={`url(#soft-${id})`} />
    </svg>
  );
}
