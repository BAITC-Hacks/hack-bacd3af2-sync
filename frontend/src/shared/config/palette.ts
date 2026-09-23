/**
 * Colors consumed by charts (SVG attributes cannot read Tailwind classes).
 * Mirrors the tokens in app/styles/index.css.
 *
 * Series colors were checked with a CVD validator against the dark chart surface (#0d1424):
 * lightness band, chroma floor, deutan/protan/tritan ΔE ≥ 8, normal-vision ΔE ≥ 15, contrast ≥ 3:1.
 */
export const palette = {
  surface: "#0d1424",
  grid: "rgba(148, 163, 184, 0.10)",
  axis: "rgba(148, 163, 184, 0.28)",
  inkMuted: "#9aa6bd",
  inkSubtle: "#66728a",
  accent: "#22d3ee",
  series: ["#0a9cc0", "#8b5cf6"],
} as const;
