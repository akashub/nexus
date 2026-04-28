import cytoscape from "cytoscape";
import { useEffect, useRef } from "react";
import type { GraphData } from "../types";

const CATEGORY_COLORS: Record<string, string> = {
  devtool: "#a78bfa",
  framework: "#60a5fa",
  concept: "#34d399",
  pattern: "#fb923c",
  language: "#f87171",
};
const DEFAULT_COLOR = "#6b7280";

interface Props {
  data: GraphData | undefined;
  onSelectNode: (id: string | null) => void;
}

export default function GraphView({ data, onSelectNode }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    if (!containerRef.current || !data) return;

    const elements: cytoscape.ElementDefinition[] = [
      ...data.nodes.map((n) => ({
        data: { id: n.id, label: n.name, category: n.category },
      })),
      ...data.edges.map((e) => ({
        data: {
          id: e.id,
          source: e.source_id,
          target: e.target_id,
          label: e.relationship,
        },
      })),
    ];

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "background-color": (ele: cytoscape.NodeSingular) =>
              CATEGORY_COLORS[ele.data("category")] || DEFAULT_COLOR,
            color: "#e5e7eb",
            "font-size": "12px",
            "text-valign": "bottom",
            "text-margin-y": 8,
            width: (ele: cytoscape.NodeSingular) => 20 + ele.degree(false) * 5,
            height: (ele: cytoscape.NodeSingular) => 20 + ele.degree(false) * 5,
          } as cytoscape.Css.Node,
        },
        {
          selector: "edge",
          style: {
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "arrow-scale": 0.8,
            "line-color": "#374151",
            "target-arrow-color": "#374151",
            width: 1.5,
            label: "data(label)",
            "font-size": "9px",
            color: "#6b7280",
            "text-rotation": "autorotate",
          } as cytoscape.Css.Edge,
        },
        {
          selector: "node:selected",
          style: {
            "border-width": 3,
            "border-color": "#f59e0b",
          } as cytoscape.Css.Node,
        },
      ],
      layout: { name: "cose", animate: true, nodeDimensionsIncludeLabels: true },
    });

    cy.on("tap", "node", (evt) => onSelectNode(evt.target.id()));
    cy.on("tap", (evt) => {
      if (evt.target === cy) onSelectNode(null);
    });

    cyRef.current = cy;
    return () => {
      cy.destroy();
    };
  }, [data, onSelectNode]);

  return <div ref={containerRef} className="w-full h-full" />;
}
