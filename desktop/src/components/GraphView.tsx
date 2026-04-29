import cytoscape from "cytoscape";
import { useCallback, useEffect, useRef, useState } from "react";
import { useDeleteConcept, useEnrichConcept } from "../hooks/useApi";
import { slugify } from "../types";
import type { GraphData } from "../types";

export const CATEGORY_COLORS: Record<string, string> = {
  devtool: "#8b7bb8", framework: "#5b8cb8", concept: "#5ba88b",
  pattern: "#b89060", language: "#b86b6b",
};
export const DEFAULT_COLOR = "#4a5568";

interface Props {
  data: GraphData | undefined;
  onSelectNode: (id: string | null) => void;
  selectedId: string | null;
  categoryFilter: string | null;
}

function structuralHash(d: GraphData, filter: string | null): string {
  const ids = filter ? d.nodes.filter((n) => n.category === filter).map((n) => n.id) : d.nodes.map((n) => n.id);
  return ids.sort().join(",") + "|" + d.edges.map((e) => e.id).sort().join(",") + "|" + (filter || "");
}

export default function GraphView({ data, onSelectNode, selectedId, categoryFilter }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const lastStructHash = useRef("");
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; nodeId: string } | null>(null);
  const deleteConcept = useDeleteConcept();
  const enrich = useEnrichConcept();

  const buildElements = useCallback((d: GraphData): cytoscape.ElementDefinition[] => {
    const nodes = categoryFilter ? d.nodes.filter((n) => n.category === categoryFilter) : d.nodes;
    const nodeIds = new Set(nodes.map((n) => n.id));
    const degree: Record<string, number> = {};
    d.edges.filter((e) => nodeIds.has(e.source_id) && nodeIds.has(e.target_id)).forEach((e) => {
      degree[e.source_id] = (degree[e.source_id] || 0) + 1;
      degree[e.target_id] = (degree[e.target_id] || 0) + 1;
    });
    return [
      ...nodes.map((n) => ({
        data: {
          id: n.id, label: " ●  " + slugify(n.name),
          category: n.category, summary: n.summary || n.description || "",
          deg: degree[n.id] || 0,
        },
      })),
      ...d.edges.filter((e) => nodeIds.has(e.source_id) && nodeIds.has(e.target_id)).map((e) => ({
        data: { id: e.id, source: e.source_id, target: e.target_id, label: e.relationship || "", rel: e.relationship || "" },
      })),
    ];
  }, [categoryFilter]);

  useEffect(() => {
    if (!containerRef.current || !data) return;
    const hash = structuralHash(data, categoryFilter);

    if (hash !== lastStructHash.current || !cyRef.current) {
      lastStructHash.current = hash;
      if (cyRef.current) cyRef.current.destroy();

      const cy = cytoscape({
        container: containerRef.current,
        elements: buildElements(data),
        style: graphStyles(),
        layout: {
          name: "cose", animate: true, animationDuration: 800, nodeDimensionsIncludeLabels: true,
          nodeRepulsion: () => 8000, idealEdgeLength: () => 140, gravity: 0.35, fit: true, padding: 50,
        },
        minZoom: 0.3, maxZoom: 3, wheelSensitivity: 0.3,
      });

      cy.on("tap", "node", (evt) => onSelectNode(evt.target.id()));
      cy.on("tap", (evt) => { if (evt.target === cy) onSelectNode(null); });
      cy.on("dbltap", "node", (evt) => window.dispatchEvent(new CustomEvent("nexus:edit", { detail: evt.target.id() })));
      cy.on("mouseover", "node", (evt) => {
        evt.target.addClass("hover");
        const summary = evt.target.data("summary");
        if (summary) {
          const pos = evt.target.renderedPosition();
          setTooltip({ x: pos.x, y: pos.y - 30, text: summary });
        }
      });
      cy.on("mouseout", "node", (evt) => { evt.target.removeClass("hover"); setTooltip(null); });
      cy.on("cxttap", "node", (evt) => {
        evt.originalEvent.preventDefault();
        const pos = evt.target.renderedPosition();
        setCtxMenu({ x: pos.x, y: pos.y, nodeId: evt.target.id() });
      });
      cy.on("tap", () => setCtxMenu(null));
      const fitHandler = () => cy.animate({ fit: { eles: cy.elements(), padding: 50 }, duration: 400 });
      window.addEventListener("nexus:fit", fitHandler);
      cyRef.current = cy;
      return () => { window.removeEventListener("nexus:fit", fitHandler); cy.destroy(); cyRef.current = null; };
    }

    const cy = cyRef.current;
    for (const n of data.nodes) {
      const node = cy.getElementById(n.id);
      if (node.length) {
        node.data("category", n.category);
        node.data("summary", n.summary || n.description || "");
        node.data("label", " ●  " + slugify(n.name));
      }
    }
  }, [data, onSelectNode, buildElements, categoryFilter]);

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
      {tooltip && (
        <div className="absolute pointer-events-none px-2 py-1 bg-[#1a1a1c] border border-white/[0.1] rounded text-[10px] text-gray-400 max-w-[200px] truncate z-10"
          style={{ left: tooltip.x, top: tooltip.y, transform: "translate(-50%, -100%)" }}>
          {tooltip.text}
        </div>
      )}
      {ctxMenu && (
        <div className="absolute z-20 bg-[#1a1a1c] border border-white/[0.1] rounded-lg shadow-lg py-1 min-w-[120px]"
          style={{ left: ctxMenu.x, top: ctxMenu.y }}>
          {[
            { label: "enrich", action: () => { enrich.mutate(ctxMenu.nodeId); onSelectNode(ctxMenu.nodeId); setCtxMenu(null); } },
            { label: "connect", action: () => { onSelectNode(ctxMenu.nodeId); setCtxMenu(null); } },
            { label: "delete", action: () => { deleteConcept.mutate(ctxMenu.nodeId); onSelectNode(null); setCtxMenu(null); } },
          ].map((item) => (
            <button key={item.label} onClick={item.action}
              className={`block w-full text-left px-3 py-1.5 text-[11px] hover:bg-white/[0.06] ${item.label === "delete" ? "text-red-400/80" : "text-gray-400"}`}>
              {item.label}
            </button>
          ))}
        </div>
      )}
      <div className="absolute bottom-3 right-3 flex gap-1.5">
        <FabBtn label="+" onClick={() => window.dispatchEvent(new CustomEvent("nexus:add"))} />
        <FabBtn label="?" onClick={() => window.dispatchEvent(new CustomEvent("nexus:chat"))} />
      </div>
    </div>
  );
}

function graphStyles(): cytoscape.StylesheetStyle[] {
  return [
    { selector: "node", style: {
      shape: "round-rectangle", label: "data(label)", "text-valign": "center", "text-halign": "center",
      "background-color": "#0a0a0b", "background-opacity": 0.8, "border-width": 1,
      "border-color": (ele: cytoscape.NodeSingular) => CATEGORY_COLORS[ele.data("category")] || DEFAULT_COLOR,
      "border-opacity": 0.6, color: "#9ca3af", "font-size": "10px",
      "font-family": "'SF Mono', 'Fira Code', monospace",
      width: "label", height: (ele: cytoscape.NodeSingular) => 28 + Math.min(ele.data("deg"), 8) * 2,
      padding: "6px", "overlay-opacity": 0,
    } as unknown as cytoscape.Css.Node },
    { selector: "node:active", style: { "overlay-opacity": 0 } as cytoscape.Css.Node },
    { selector: "edge", style: {
      "curve-style": "bezier", "target-arrow-shape": "triangle", "arrow-scale": 0.7,
      "line-color": "#2a3a4a", "target-arrow-color": "#2a3a4a", width: 1.2, "line-opacity": 0.6,
      label: "data(label)", "font-size": "8px", "font-family": "'SF Mono', 'Fira Code', monospace",
      color: "#4a5a6a", "text-rotation": "autorotate", "text-margin-y": -8,
      "text-background-color": "#0a0a0b", "text-background-opacity": 0.9, "text-background-padding": "2px",
      "overlay-opacity": 0,
    } as cytoscape.Css.Edge },
    { selector: "edge[rel='part_of'], edge[rel='similar_to']", style: { "line-style": "dashed", "line-dash-pattern": [6, 3] } as cytoscape.Css.Edge },
    { selector: "edge:hover", style: { "line-color": "#4a6a8a", "target-arrow-color": "#4a6a8a", color: "#6a8aaa" } as cytoscape.Css.Edge },
    { selector: "node:selected", style: {
      "border-width": 1.5, "border-color": "#e2e8f0", "border-opacity": 0.9, "background-opacity": 0.9, color: "#e2e8f0",
    } as cytoscape.Css.Node },
    { selector: "node.hover", style: { "border-opacity": 0.8, color: "#cbd5e1" } as cytoscape.Css.Node },
  ];
}

function FabBtn({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button onClick={onClick}
      className="w-8 h-8 border border-white/[0.1] rounded-md bg-[#0a0a0b]/80 text-gray-500 hover:text-gray-300 hover:border-white/[0.15] text-sm transition-colors">
      {label}
    </button>
  );
}
