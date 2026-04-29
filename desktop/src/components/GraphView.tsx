import cytoscape from "cytoscape";
import { useCallback, useEffect, useRef } from "react";
import type { GraphData } from "../types";

const CATEGORY_COLORS: Record<string, string> = {
  devtool: "#8b7bb8",
  framework: "#5b8cb8",
  concept: "#5ba88b",
  pattern: "#b89060",
  language: "#b86b6b",
};
const DEFAULT_COLOR = "#4a5568";

interface Props {
  data: GraphData | undefined;
  onSelectNode: (id: string | null) => void;
  selectedId: string | null;
  categoryFilter: string | null;
}

export default function GraphView({ data, onSelectNode, selectedId, categoryFilter }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const lastDataHash = useRef<string>("");

  const buildElements = useCallback((d: GraphData): cytoscape.ElementDefinition[] => {
    const nodes = categoryFilter
      ? d.nodes.filter((n) => n.category === categoryFilter)
      : d.nodes;
    const nodeIds = new Set(nodes.map((n) => n.id));
    return [
      ...nodes.map((n) => ({
        data: {
          id: n.id,
          label: " ●  " + n.name.toLowerCase().replace(/\s+/g, "_"),
          category: n.category,
          rel: "",
        },
      })),
      ...d.edges
        .filter((e) => nodeIds.has(e.source_id) && nodeIds.has(e.target_id))
        .map((e) => ({
          data: {
            id: e.id,
            source: e.source_id,
            target: e.target_id,
            label: e.relationship || "",
            rel: e.relationship || "",
          },
        })),
    ];
  }, [categoryFilter]);

  useEffect(() => {
    if (!containerRef.current || !data) return;
    const hash = data.nodes.map((n) => `${n.id}:${n.name}:${n.category || ""}:${n.updated_at}`).sort().join(",") + "|" + data.edges.map((e) => e.id).sort().join(",") + "|" + (categoryFilter || "");
    if (hash === lastDataHash.current && cyRef.current) return;
    lastDataHash.current = hash;
    if (cyRef.current) cyRef.current.destroy();

    const cy = cytoscape({
      container: containerRef.current,
      elements: buildElements(data),
      style: [
        {
          selector: "node",
          style: {
            shape: "round-rectangle",
            label: "data(label)",
            "text-valign": "center",
            "text-halign": "center",
            "background-color": "#0a0a0b",
            "background-opacity": 0.8,
            "border-width": 1,
            "border-color": (ele: cytoscape.NodeSingular) =>
              CATEGORY_COLORS[ele.data("category")] || DEFAULT_COLOR,
            "border-opacity": 0.6,
            color: "#9ca3af",
            "font-size": "10px",
            "font-family": "'SF Mono', 'Fira Code', monospace",
            width: "label",
            height: 28,
            padding: "6px",
            "overlay-opacity": 0,
          } as unknown as cytoscape.Css.Node,
        },
        { selector: "node:active", style: { "overlay-opacity": 0 } as cytoscape.Css.Node },
        {
          selector: "edge",
          style: {
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "arrow-scale": 0.7,
            "line-color": "#2a3a4a",
            "target-arrow-color": "#2a3a4a",
            width: 1.2,
            "line-opacity": 0.6,
            label: "data(label)",
            "font-size": "8px",
            "font-family": "'SF Mono', 'Fira Code', monospace",
            color: "#4a5a6a",
            "text-rotation": "autorotate",
            "text-margin-y": -8,
            "text-background-color": "#0a0a0b",
            "text-background-opacity": 0.9,
            "text-background-padding": "2px",
            "overlay-opacity": 0,
          } as cytoscape.Css.Edge,
        },
        {
          selector: "edge[rel='part_of'], edge[rel='similar_to']",
          style: { "line-style": "dashed", "line-dash-pattern": [6, 3] } as cytoscape.Css.Edge,
        },
        {
          selector: "edge:hover",
          style: { "line-color": "#4a6a8a", "target-arrow-color": "#4a6a8a", color: "#6a8aaa" } as cytoscape.Css.Edge,
        },
        {
          selector: "node:selected",
          style: {
            "border-width": 1.5, "border-color": "#e2e8f0", "border-opacity": 0.9,
            "background-opacity": 0.9, color: "#e2e8f0",
          } as cytoscape.Css.Node,
        },
        {
          selector: "node.hover",
          style: { "border-opacity": 0.8, color: "#cbd5e1" } as cytoscape.Css.Node,
        },
      ],
      layout: {
        name: "cose",
        animate: true,
        animationDuration: 800,
        nodeDimensionsIncludeLabels: true,
        nodeRepulsion: () => 8000,
        idealEdgeLength: () => 140,
        gravity: 0.35,
        fit: true,
        padding: 50,
      },
      minZoom: 0.3,
      maxZoom: 3,
      wheelSensitivity: 0.3,
    });

    cy.on("tap", "node", (evt) => onSelectNode(evt.target.id()));
    cy.on("tap", (evt) => { if (evt.target === cy) onSelectNode(null); });
    cy.on("mouseover", "node", (evt) => evt.target.addClass("hover"));
    cy.on("mouseout", "node", (evt) => evt.target.removeClass("hover"));

    const fitHandler = () => cy.animate({ fit: { eles: cy.elements(), padding: 50 }, duration: 400 });
    window.addEventListener("nexus:fit", fitHandler);
    cyRef.current = cy;
    return () => { window.removeEventListener("nexus:fit", fitHandler); cy.destroy(); cyRef.current = null; };
  }, [data, onSelectNode, buildElements]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().unselect();
    if (selectedId) {
      const node = cy.getElementById(selectedId);
      if (node.length) { node.select(); cy.animate({ center: { eles: node }, duration: 300 }); }
    }
  }, [selectedId]);

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />
      <div className="absolute bottom-3 right-3 flex gap-1.5">
        <FabBtn label="+" onClick={() => window.dispatchEvent(new CustomEvent("nexus:add"))} />
        <FabBtn label="?" onClick={() => window.dispatchEvent(new CustomEvent("nexus:chat"))} />
      </div>
    </div>
  );
}

function FabBtn({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-8 h-8 border border-white/[0.1] rounded-md bg-[#0a0a0b]/80 text-gray-500 hover:text-gray-300 hover:border-white/[0.15] text-sm transition-colors"
    >
      {label}
    </button>
  );
}
