import type cytoscape from "cytoscape";

export const CATEGORY_COLORS: Record<string, string> = {
  devtool: "#a78bfa", framework: "#60a5fa", concept: "#4ade80",
  pattern: "#fbbf24", language: "#f87171",
};
export const DEFAULT_COLOR = "#94a3b8";

interface GTheme {
  nodeText: string; nodeTextHover: string; edgeLine: string;
  edgeText: string; edgeTextBg: string; dimOpacity: number;
}

const DARK: GTheme = {
  nodeText: "#e2e8f0", nodeTextHover: "#ffffff", edgeLine: "#475569",
  edgeText: "#94a3b8", edgeTextBg: "#0a0a0b", dimOpacity: 0.06,
};
const LIGHT: GTheme = {
  nodeText: "#1e293b", nodeTextHover: "#000000", edgeLine: "#94a3b8",
  edgeText: "#475569", edgeTextBg: "#fafafa", dimOpacity: 0.12,
};

export function graphStyles(dark = true): cytoscape.StylesheetStyle[] {
  const t = dark ? DARK : LIGHT;
  const cc = (e: cytoscape.NodeSingular) => CATEGORY_COLORS[e.data("category")] || DEFAULT_COLOR;
  const sz = (e: cytoscape.NodeSingular) => 14 + Math.min(e.data("deg"), 8) * 4;
  return [
    { selector: "node", style: {
      shape: "ellipse", label: "data(label)", "text-valign": "bottom", "text-halign": "center", "text-margin-y": 4,
      "background-color": cc, "background-opacity": 0.55, "border-width": 1.5, "border-color": cc,
      "border-opacity": 0.8, color: t.nodeText, "font-size": "11px", "text-opacity": 0.85, "font-family": "'SF Mono', 'Fira Code', monospace",
      width: sz, height: sz, "overlay-opacity": 0, "text-max-width": "100px", "text-wrap": "ellipsis",
      "transition-property": "opacity, border-color, border-opacity, border-width, background-opacity", "transition-duration": 200,
    } as unknown as cytoscape.Css.Node },
    { selector: "node:active", style: { "overlay-opacity": 0 } as cytoscape.Css.Node },
    { selector: "edge", style: {
      "curve-style": "bezier", "target-arrow-shape": "triangle", "arrow-scale": 0.6,
      "line-color": t.edgeLine, "target-arrow-color": t.edgeLine, width: 0.8, "line-opacity": 0.35,
      label: "data(label)", "font-size": "10px", "font-family": "'SF Mono', 'Fira Code', monospace",
      color: t.edgeText, "text-rotation": "autorotate", "text-margin-y": -8, "text-background-color": t.edgeTextBg,
      "text-background-opacity": 0.9, "text-background-padding": "2px", "overlay-opacity": 0, "text-opacity": 0,
      "transition-property": "opacity, line-color, target-arrow-color, text-opacity", "transition-duration": 200,
    } as cytoscape.Css.Edge },
    { selector: "edge[rel='part_of'], edge[rel='similar_to']", style: { "line-style": "dashed", "line-dash-pattern": [6, 3] } as cytoscape.Css.Edge },
    { selector: "edge[rel='tested_with']", style: { "line-style": "dashed", "line-color": "#4a8066", "target-arrow-color": "#4a8066" } as cytoscape.Css.Edge },
    { selector: "edge[rel='configured_by']", style: { "line-style": "dotted", width: 0.8 } as cytoscape.Css.Edge },
    { selector: "edge[rel='sends_data_to'], edge[rel='triggers']", style: { "line-style": "dashed", "line-dash-pattern": [4, 2], width: 1.2, "line-color": "#7c9dbd", "target-arrow-color": "#7c9dbd" } as cytoscape.Css.Edge },
    { selector: "edge[rel='builds_into']", style: { width: 1.5, "line-color": "#5b8cb8", "target-arrow-color": "#5b8cb8" } as cytoscape.Css.Edge },
    { selector: "edge[rel='wraps'], edge[rel='serves']", style: { width: 2 } as cytoscape.Css.Edge },
    { selector: "edge[rel='deployed_via']", style: { "line-style": "dotted", "line-color": "#b89060", "target-arrow-color": "#b89060" } as cytoscape.Css.Edge },
    { selector: "edge[rel='replaces']", style: { "line-style": "dashed", "line-color": "#b86b6b", "target-arrow-color": "#b86b6b" } as cytoscape.Css.Edge },
    { selector: ".dimmed", style: { opacity: t.dimOpacity } as any },
    { selector: "node.hover", style: { "border-opacity": 1, "border-width": 2.5, "background-opacity": 0.7, color: t.nodeTextHover, "text-opacity": 1 } as cytoscape.Css.Node },
    { selector: "node.enriching-pulse", style: { "border-width": 3, "border-opacity": 1, "background-opacity": 0.35 } as cytoscape.Css.Node },
    { selector: "node:selected", style: { "border-width": 2, "border-color": t.nodeTextHover, "border-opacity": 0.9, "background-opacity": 0.25, color: t.nodeTextHover } as cytoscape.Css.Node },
    { selector: ".edge-hover", style: { "text-opacity": 1, "line-opacity": 0.8, width: 1.5 } as cytoscape.Css.Edge },
    { selector: ".cat-glow", style: { "background-opacity": 0.25, "border-opacity": 0.8, "border-width": 2, "text-opacity": 0.8 } as cytoscape.Css.Node },
    { selector: "edge[rel='related_to']", style: { "line-opacity": 0.15, "line-style": "dotted", width: 0.5 } as cytoscape.Css.Edge },
    { selector: ".cat-label", style: {
      shape: "ellipse", width: 1, height: 1, "background-opacity": 0, "border-width": 0,
      label: "data(label)", "text-valign": "center", "text-halign": "center",
      "font-size": "15px", color: t.nodeText, "text-opacity": 0, "text-transform": "uppercase",
      "font-weight": "bold", "overlay-opacity": 0, events: "no",
      "transition-property": "text-opacity", "transition-duration": 300,
    } as unknown as cytoscape.Css.Node },
    { selector: ".cat-label.cat-label-show", style: { "text-opacity": 0.25 } as unknown as cytoscape.Css.Node },
    { selector: ".search-hit", style: {
      "border-width": 3, "border-opacity": 1, "background-opacity": 0.5, "text-opacity": 1,
      width: 32, height: 32, "font-size": "15px", color: "#ffffff",
      "transition-property": "border-width, background-opacity, width, height", "transition-duration": 300,
    } as unknown as cytoscape.Css.Node },
    { selector: ".search-dim", style: { opacity: 0.04, "transition-property": "opacity", "transition-duration": 300 } as any },
  ];
}

export function globalGraphStyles(dark = true) {
  const t = dark ? DARK : LIGHT;
  const PC = "#5b8cb8";
  return [
    { selector: "node", style: {
      shape: "ellipse", label: "data(label)", "text-valign": "bottom", "text-halign": "center", "text-margin-y": 6,
      "background-color": PC, "background-opacity": 0.15, "border-width": 1.5, "border-color": PC,
      "border-opacity": 0.6, color: t.nodeText, "font-size": "13px", "font-family": "'SF Mono', 'Fira Code', monospace",
      width: "data(size)", height: "data(size)", "overlay-opacity": 0, "text-max-width": "120px",
    } as unknown as cytoscape.Css.Node },
    { selector: "node:active", style: { "overlay-opacity": 0 } as cytoscape.Css.Node },
    { selector: "edge", style: {
      "curve-style": "bezier", width: "data(w)", "line-color": t.edgeLine, "line-opacity": 0.6,
      label: "data(label)", "font-size": "10px", color: t.edgeText, "text-rotation": "autorotate",
      "text-margin-y": -10, "text-background-color": t.edgeTextBg, "text-background-opacity": 0.9,
      "text-background-padding": "2px", "overlay-opacity": 0,
      "font-family": "'SF Mono', 'Fira Code', monospace",
    } as cytoscape.Css.Edge },
    { selector: "node.hover", style: {
      "border-opacity": 1, "border-width": 2.5, "background-opacity": 0.3, color: t.nodeTextHover,
    } as cytoscape.Css.Node },
  ];
}
