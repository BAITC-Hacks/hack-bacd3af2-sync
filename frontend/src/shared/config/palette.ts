/**
 * Colors consumed by charts (SVG attributes cannot read Tailwind classes).
 * Mirrors the tokens in app/styles/index.css.
 *
 * Series colors (cream / sage) were run through a CVD validator on the chart surface
 * (#16170f): pair separation passes — deutan/protan/tritan ΔE ≥ 11, normal-vision ΔE 15.7,
 * contrast ≥ 3:1. The muted brand palette intentionally sits above the lightness band and
 * below the chroma floor, so identity never relies on color alone: turbine 1 uses filled
 * markers, turbine 2 hollow rings, and every chart has a legend and a tooltip.
 */
export const palette = {
  surface: "#16170f",
  grid: "rgba(234, 218, 183, 0.07)",
  axis: "rgba(234, 218, 183, 0.16)",
  inkMuted: "#a9a090",
  inkSubtle: "#746f65",
  cream: "#e8d2aa",
  sage: "#9fbd93",
  series: ["#d9bf8f", "#7fa274"],
  bar: "rgba(159, 189, 147, 0.42)",
  barActive: "#e8d2aa",
} as const;
