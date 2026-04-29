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
  const fitHandlerRef = useRef<(() => void) | null>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; nodeId: string } | null>(null);
  const deleteConcept = useDeleteConcept();
  const enrich = useEnrichConcept();

  const buildElements = useCallback((d: GraphData): cytoscape.ElementDefinition[] => {
    const nodes = categoryFilter ? d.nodes.filter((n) => n.category === categoryFilter) : d.nodes;
    const nodeIds = new Set(nodes.map((n) => n.id));
    const deg: Record<string, number> = {};
    d.edges.filter((e) => nodeIds.has(e.source_id) && nodeIds.has(e.target_id)).forEach((e) => {
      deg[e.source_id] = (deg[e.source_id] || 0) + 1; deg[e.target_id] = (deg[e.target_id] || 0) + 1;
    });
    return [
      ...nodes.map((n) => ({ data: {
        id: n.id, label: slugify(n.name), category: n.category,
        summary: n.summary || n.description || "", deg: deg[n.id] || 0, enriching: !!n.enrich_status,
      } })),
      ...d.edges.filter((e) => nodeIds.has(e.source_id) && nodeIds.has(e.target_id)).map((e) => ({
        data: { id: e.id, source: e.source_id, target: e.target_id, label: e.relationship || "", rel: e.relationship || "" },
      })),
    ];
  }, [categoryFilter]);

  useEffect(() => () => {
    if (fitHandlerRef.current) window.removeEventListener("nexus:fit", fitHandlerRef.current);
    if (cyRef.current) { cyRef.current.destroy(); cyRef.current = null; }
  }, []);

  useEffect(() => {
    const id = setInterval(() => cyRef.current?.nodes().forEach((n) => {
      n.data("enriching") ? n.toggleClass("enriching-pulse") : n.removeClass("enriching-pulse");
    }), 800);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!containerRef.current || !data) return;
    const hash = structuralHash(data, categoryFilter);

    if (hash !== lastStructHash.current || !cyRef.current) {
      lastStructHash.current = hash;
      if (fitHandlerRef.current) window.removeEventListener("nexus:fit", fitHandlerRef.current);
      if (cyRef.current) cyRef.current.destroy();

      const cy = cytoscape({
        container: containerRef.current,
        elements: buildElements(data),
        style: graphStyles(),
        layout: {
          name: "cose", animate: true, animationDuration: 1200, nodeDimensionsIncludeLabels: true,
          nodeRepulsion: () => 10000, idealEdgeLength: () => 120, gravity: 0.25,
          fit: true, padding: 60, randomize: false,
        },
        minZoom: 0.3, maxZoom: 3, wheelSensitivity: 0.3,
      });

      cy.on("tap", "node", (evt) => onSelectNode(evt.target.id()));
      cy.on("tap", (evt) => { if (evt.target === cy) onSelectNode(null); });
      cy.on("dbltap", "node", (evt) => window.dispatchEvent(new CustomEvent("nexus:edit", { detail: evt.target.id() })));
      cy.on("mouseover", "node", (evt) => {
        const n = evt.target;
        cy.elements().not(n.closedNeighborhood()).addClass("dimmed");
        n.addClass("hover");
        const summary = n.data("summary");
        if (summary) { const pos = n.renderedPosition(); setTooltip({ x: pos.x, y: pos.y - 30, text: summary }); }
      });
      cy.on("mouseout", "node", () => { cy.elements().removeClass("dimmed hover"); setTooltip(null); });
      cy.on("cxttap", "node", (evt) => {
        evt.originalEvent.preventDefault();
        const pos = evt.target.renderedPosition();
        setCtxMenu({ x: pos.x, y: pos.y, nodeId: evt.target.id() });
      });
      cy.on("tap", () => setCtxMenu(null));
      cy.on("drag", "node", (evt) => {
        const pos = evt.target.position();
        cy.nodes().not(evt.target).forEach((o: cytoscape.NodeSingular) => {
          const p = o.position(), dx = p.x - pos.x, dy = p.y - pos.y, d = Math.sqrt(dx * dx + dy * dy);
          if (d < 70 && d > 0) { const f = (70 - d) * 0.25; o.position({ x: p.x + dx / d * f, y: p.y + dy / d * f }); }
        });
      });
      cy.on("dragfree", "node", (evt) => {
        const pos = evt.target.position();
        evt.target.neighborhood("node").forEach((nb: cytoscape.NodeSingular) => {
          const p = nb.position();
          nb.animate({ position: { x: p.x + (pos.x - p.x) * 0.04, y: p.y + (pos.y - p.y) * 0.04 } } as any, { duration: 400 } as any);
        });
      });
      const fitHandler = () => cy.animate({ fit: { eles: cy.elements(), padding: 50 }, duration: 400 });
      window.addEventListener("nexus:fit", fitHandler);
      fitHandlerRef.current = fitHandler;
      cyRef.current = cy;
    }

    const cy = cyRef.current;
    for (const n of data.nodes) {
      const node = cy.getElementById(n.id);
      if (node.length) {
        node.data("category", n.category);
        node.data("summary", n.summary || n.description || "");
        node.data("label", slugify(n.name));
        node.data("enriching", !!n.enrich_status);
      }
    }
  }, [data, onSelectNode, buildElements, categoryFilter]);

  useEffect(() => {
    const cy = cyRef.current; if (!cy) return; cy.nodes().unselect();
    if (selectedId) { const n = cy.getElementById(selectedId); if (n.length) { n.select(); cy.animate({ center: { eles: n }, duration: 300 }); } }
  }, [selectedId]);

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />
      {tooltip && <div className="absolute pointer-events-none px-2 py-1 bg-[#1a1a1c] border border-white/[0.1] rounded text-[10px] text-gray-400 max-w-[200px] truncate z-10"
        style={{ left: tooltip.x, top: tooltip.y, transform: "translate(-50%, -100%)" }}>{tooltip.text}</div>}
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
    { selector: ".dimmed", style: { opacity: 0.1 } as any },
    { selector: "node.hover", style: { "border-opacity": 1, "border-width": 2, "background-opacity": 0.3, color: "#e2e8f0" } as cytoscape.Css.Node },
    { selector: "node.enriching-pulse", style: { "border-width": 3, "border-opacity": 1, "background-opacity": 0.35 } as cytoscape.Css.Node },
    { selector: "node:selected", style: { "border-width": 2, "border-color": "#e2e8f0", "border-opacity": 0.9, "background-opacity": 0.25, color: "#e2e8f0" } as cytoscape.Css.Node },
  ];
}

const FabBtn = ({ label, onClick }: { label: string; onClick: () => void }) => (
  <button onClick={onClick} className="w-8 h-8 border border-white/[0.1] rounded-md bg-[#0a0a0b]/80 text-gray-500 hover:text-gray-300 hover:border-white/[0.15] text-sm transition-colors">{label}</button>
);
