import type cytoscape from "cytoscape";

export const CATEGORY_COLORS: Record<string, string> = {
  devtool: "#8b7bb8", framework: "#5b8cb8", concept: "#5ba88b",
  pattern: "#b89060", language: "#b86b6b",
};
export const DEFAULT_COLOR = "#4a5568";

export function graphStyles(): cytoscape.StylesheetStyle[] {
  const cc = (e: cytoscape.NodeSingular) => CATEGORY_COLORS[e.data("category")] || DEFAULT_COLOR;
  const sz = (e: cytoscape.NodeSingular) => 22 + Math.min(e.data("deg"), 8) * 3.5;
  return [
    { selector: "node", style: {
      shape: "ellipse", label: "data(label)", "text-valign": "bottom", "text-halign": "center", "text-margin-y": 5,
      "background-color": cc, "background-opacity": 0.15, "border-width": 1.5, "border-color": cc,
      "border-opacity": 0.6, color: "#9ca3af", "font-size": "9px", "font-family": "'SF Mono', 'Fira Code', monospace",
      width: sz, height: sz, "overlay-opacity": 0,
      "transition-property": "opacity, border-color, border-opacity, border-width, background-opacity", "transition-duration": 200,
    } as unknown as cytoscape.Css.Node },
    { selector: "node:active", style: { "overlay-opacity": 0 } as cytoscape.Css.Node },
    { selector: "edge", style: {
      "curve-style": "bezier", "target-arrow-shape": "triangle", "arrow-scale": 0.6,
      "line-color": "#1e2d3d", "target-arrow-color": "#1e2d3d", width: 1, "line-opacity": 0.5,
      label: "data(label)", "font-size": "7px", "font-family": "'SF Mono', 'Fira Code', monospace",
      color: "#3a4a5a", "text-rotation": "autorotate", "text-margin-y": -8, "text-background-color": "#0a0a0b",
      "text-background-opacity": 0.9, "text-background-padding": "2px", "overlay-opacity": 0,
      "transition-property": "opacity, line-color, target-arrow-color", "transition-duration": 200,
    } as cytoscape.Css.Edge },
    { selector: "edge[rel='part_of'], edge[rel='similar_to']", style: { "line-style": "dashed", "line-dash-pattern": [6, 3] } as cytoscape.Css.Edge },
    { selector: "edge[rel='tested_with']", style: { "line-style": "dashed", "line-color": "#4a8066", "target-arrow-color": "#4a8066" } as cytoscape.Css.Edge },
    { selector: "edge[rel='configured_by']", style: { "line-style": "dotted", width: 0.8 } as cytoscape.Css.Edge },
    { selector: "edge[rel='builds_into']", style: { width: 1.5, "line-color": "#5b8cb8", "target-arrow-color": "#5b8cb8" } as cytoscape.Css.Edge },
    { selector: "edge[rel='wraps'], edge[rel='serves']", style: { width: 2 } as cytoscape.Css.Edge },
    { selector: "edge[rel='deployed_via']", style: { "line-style": "dotted", "line-color": "#b89060", "target-arrow-color": "#b89060" } as cytoscape.Css.Edge },
    { selector: "edge[rel='replaces']", style: { "line-style": "dashed", "line-color": "#b86b6b", "target-arrow-color": "#b86b6b" } as cytoscape.Css.Edge },
    { selector: ".dimmed", style: { opacity: 0.1 } as any },
    { selector: "node.hover", style: { "border-opacity": 1, "border-width": 2, "background-opacity": 0.3, color: "#e2e8f0" } as cytoscape.Css.Node },
    { selector: "node.enriching-pulse", style: { "border-width": 3, "border-opacity": 1, "background-opacity": 0.35 } as cytoscape.Css.Node },
    { selector: "node:selected", style: { "border-width": 2, "border-color": "#e2e8f0", "border-opacity": 0.9, "background-opacity": 0.25, color: "#e2e8f0" } as cytoscape.Css.Node },
  ];
}
