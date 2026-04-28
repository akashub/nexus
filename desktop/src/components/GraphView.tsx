import cytoscape from "cytoscape";
import { useCallback, useEffect, useRef } from "react";
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
  selectedId: string | null;
}

export default function GraphView({ data, onSelectNode, selectedId }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  const buildElements = useCallback((d: GraphData): cytoscape.ElementDefinition[] => [
    ...d.nodes.map((n) => ({
      data: {
        id: n.id,
        label: n.name,
        category: n.category,
        summary: n.summary || n.description?.slice(0, 80) || "",
      },
    })),
    ...d.edges.map((e) => ({
      data: { id: e.id, source: e.source_id, target: e.target_id, label: e.relationship },
    })),
  ], []);

  useEffect(() => {
    if (!containerRef.current || !data) return;
    if (cyRef.current) cyRef.current.destroy();

    const cy = cytoscape({
      container: containerRef.current,
      elements: buildElements(data),
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "background-color": (ele: cytoscape.NodeSingular) =>
              CATEGORY_COLORS[ele.data("category")] || DEFAULT_COLOR,
            "background-opacity": 0.9,
            "border-width": 2,
            "border-color": (ele: cytoscape.NodeSingular) =>
              CATEGORY_COLORS[ele.data("category")] || DEFAULT_COLOR,
            "border-opacity": 0.3,
            color: "#d1d5db",
            "font-size": "11px",
            "font-weight": 500,
            "text-valign": "bottom",
            "text-margin-y": 8,
            "text-background-color": "#0a0a0b",
            "text-background-opacity": 0.7,
            "text-background-padding": "2px",
            width: (ele: cytoscape.NodeSingular) => Math.max(24, 16 + ele.degree(false) * 6),
            height: (ele: cytoscape.NodeSingular) => Math.max(24, 16 + ele.degree(false) * 6),
            "overlay-opacity": 0,
          } as cytoscape.Css.Node,
        },
        {
          selector: "node:active",
          style: { "overlay-opacity": 0 } as cytoscape.Css.Node,
        },
        {
          selector: "edge",
          style: {
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "arrow-scale": 0.7,
            "line-color": "#1e293b",
            "target-arrow-color": "#1e293b",
            width: 1.5,
            "line-opacity": 0.6,
            "overlay-opacity": 0,
          } as cytoscape.Css.Edge,
        },
        {
          selector: "edge:hover",
          style: {
            label: "data(label)",
            "font-size": "9px",
            color: "#64748b",
            "text-rotation": "autorotate",
            "line-color": "#334155",
            "target-arrow-color": "#334155",
            "line-opacity": 1,
          } as cytoscape.Css.Edge,
        },
        {
          selector: "node:selected",
          style: {
            "border-width": 3,
            "border-color": "#f59e0b",
            "border-opacity": 1,
            "background-opacity": 1,
          } as cytoscape.Css.Node,
        },
        {
          selector: "node.hover",
          style: {
            "border-width": 2,
            "border-opacity": 0.8,
            "background-opacity": 1,
          } as cytoscape.Css.Node,
        },
      ],
      layout: {
        name: "cose",
        animate: true,
        animationDuration: 800,
        nodeDimensionsIncludeLabels: true,
        nodeRepulsion: () => 8000,
        idealEdgeLength: () => 120,
        gravity: 0.3,
      },
      minZoom: 0.3,
      maxZoom: 3,
      wheelSensitivity: 0.3,
    });

    cy.on("tap", "node", (evt) => onSelectNode(evt.target.id()));
    cy.on("tap", (evt) => {
      if (evt.target === cy) onSelectNode(null);
    });
    cy.on("mouseover", "node", (evt) => evt.target.addClass("hover"));
    cy.on("mouseout", "node", (evt) => evt.target.removeClass("hover"));

    cyRef.current = cy;
    return () => { cy.destroy(); };
  }, [data, onSelectNode, buildElements]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().unselect();
    if (selectedId) {
      const node = cy.getElementById(selectedId);
      if (node.length) {
        node.select();
        cy.animate({ center: { eles: node }, duration: 300 });
      }
    }
  }, [selectedId]);

  const handleFit = () => {
    const cy = cyRef.current;
    if (cy) cy.animate({ fit: { eles: cy.elements(), padding: 40 }, duration: 400 });
  };
  const handleZoomIn = () => {
    const cy = cyRef.current;
    if (cy) cy.animate({ zoom: { level: cy.zoom() * 1.3, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } }, duration: 200 });
  };
  const handleZoomOut = () => {
    const cy = cyRef.current;
    if (cy) cy.animate({ zoom: { level: cy.zoom() / 1.3, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } }, duration: 200 });
  };

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />
      <div className="absolute bottom-4 right-4 flex flex-col gap-1">
        <button onClick={handleZoomIn} className="w-8 h-8 bg-gray-900/80 backdrop-blur border border-gray-700/50 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800/80 text-sm font-bold">+</button>
        <button onClick={handleZoomOut} className="w-8 h-8 bg-gray-900/80 backdrop-blur border border-gray-700/50 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800/80 text-sm font-bold">&minus;</button>
        <button onClick={handleFit} className="w-8 h-8 bg-gray-900/80 backdrop-blur border border-gray-700/50 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800/80 text-xs">Fit</button>
      </div>
    </div>
  );
}
