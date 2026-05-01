import cytoscape from "cytoscape";
import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, type SimulationNodeDatum } from "d3-force";
import { useCallback, useEffect, useRef, useState } from "react";
import { useDeleteConcept, useEnrichConcept } from "../hooks/useApi";
import { useTheme } from "../hooks/useTheme";
import { slugify } from "../types";
import type { GraphData } from "../types";
import { addGroupLabels, bindEvents } from "./graphEvents";
import { graphStyles } from "./graphStyles";
export { CATEGORY_COLORS } from "./graphStyles";

interface Props { data: GraphData | undefined; onSelectNode: (id: string | null) => void; selectedId: string | null; categoryFilter: string | null; }
interface SimNode extends SimulationNodeDatum { id: string }

function structuralHash(d: GraphData, filter: string | null): string {
  const ids = filter ? d.nodes.filter((n) => n.category === filter).map((n) => n.id) : d.nodes.map((n) => n.id);
  return ids.sort().join(",") + "|" + d.edges.map((e) => e.id).sort().join(",") + "|" + (filter || "");
}

export default function GraphView({ data, onSelectNode, selectedId, categoryFilter }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const simRef = useRef<ReturnType<typeof forceSimulation<SimNode>> | null>(null);
  const lastStructHash = useRef("");
  const fitHandlerRef = useRef<(() => void) | null>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; nodeId: string } | null>(null);
  const [graphFind, setGraphFind] = useState<string | null>(null);
  const findRef = useRef<HTMLInputElement>(null);
  const deleteConcept = useDeleteConcept();
  const enrich = useEnrichConcept();
  const { resolved } = useTheme();
  const isDark = resolved === "dark";

  const filterEdges = useCallback((d: GraphData, nodeIds: Set<string>) => d.edges.filter((e) =>
    nodeIds.has(e.source_id) && nodeIds.has(e.target_id) && !(e.relationship === "related_to" && e.weight > 0 && e.weight < 0.68),
  ), []);

  const buildElements = useCallback((d: GraphData): cytoscape.ElementDefinition[] => {
    const nodes = categoryFilter ? d.nodes.filter((n) => n.category === categoryFilter) : d.nodes;
    const nodeIds = new Set(nodes.map((n) => n.id));
    const edges = filterEdges(d, nodeIds);
    const deg: Record<string, number> = {};
    edges.forEach((e) => { deg[e.source_id] = (deg[e.source_id] || 0) + 1; deg[e.target_id] = (deg[e.target_id] || 0) + 1; });
    return [
      ...nodes.map((n) => ({ data: {
        id: n.id, label: slugify(n.name), category: n.category || "other", sgroup: n.semantic_group || "",
        summary: n.summary || n.description || "", deg: deg[n.id] || 0, enriching: !!n.enrich_status,
      } })),
      ...edges.map((e) => ({ data: { id: e.id, source: e.source_id, target: e.target_id, label: e.relationship || "", rel: e.relationship || "" } })),
    ];
  }, [categoryFilter, filterEdges]);

  useEffect(() => () => {
    if (simRef.current) simRef.current.stop();
    if (fitHandlerRef.current) window.removeEventListener("nexus:fit", fitHandlerRef.current);
    if (cyRef.current) { cyRef.current.destroy(); cyRef.current = null; }
  }, []);

  useEffect(() => {
    const id = setInterval(() => cyRef.current?.nodes().forEach((n) => {
      n.data("enriching") ? n.toggleClass("enriching-pulse") : n.removeClass("enriching-pulse");
    }), 800);
    return () => clearInterval(id);
  }, []);

  useEffect(() => { if (cyRef.current) cyRef.current.style().fromJson(graphStyles(isDark)).update(); }, [isDark]);

  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.metaKey && e.key === "f") { e.preventDefault(); setGraphFind((v) => v === null ? "" : null); } };
    window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h);
  }, []);
  useEffect(() => { if (graphFind !== null) findRef.current?.focus(); }, [graphFind]);
  useEffect(() => {
    const cy = cyRef.current; if (!cy) return;
    cy.elements().removeClass("search-hit search-dim");
    if (!graphFind) return;
    const q = graphFind.toLowerCase();
    const hits = cy.nodes().filter((n: cytoscape.NodeSingular) => !n.hasClass("cat-label") && n.data("label")?.includes(q));
    if (hits.length) {
      hits.addClass("search-hit"); cy.elements().not(hits).not(".cat-label").addClass("search-dim");
      hits.connectedEdges().removeClass("search-dim");
      cy.animate({ fit: { eles: hits, padding: 80 }, duration: 400 });
    }
  }, [graphFind]);

  useEffect(() => {
    if (!containerRef.current || !data) return;
    const hash = structuralHash(data, categoryFilter);
    if (hash !== lastStructHash.current || !cyRef.current) {
      lastStructHash.current = hash;
      if (simRef.current) simRef.current.stop();
      if (fitHandlerRef.current) window.removeEventListener("nexus:fit", fitHandlerRef.current);
      if (cyRef.current) cyRef.current.destroy();
      const cy = cytoscape({
        container: containerRef.current, elements: buildElements(data),
        style: graphStyles(isDark), layout: { name: "preset" },
        minZoom: 0.3, maxZoom: 3, wheelSensitivity: 0.3,
      });
      const w = containerRef.current.clientWidth, h = containerRef.current.clientHeight;
      const filtered = categoryFilter ? data.nodes.filter((n) => n.category === categoryFilter) : data.nodes;
      const nIds = new Set(filtered.map((n) => n.id));
      const simNodes: SimNode[] = filtered.map((n) => ({
        id: n.id, x: w / 2 + (Math.random() - 0.5) * w * 0.3, y: h / 2 + (Math.random() - 0.5) * h * 0.3,
      }));
      const simLinks = filterEdges(data, nIds).map((e) => ({ source: e.source_id, target: e.target_id }));
      const nodeMap = new Map(simNodes.map((n) => [n.id, n]));
      let labelsAdded = false;
      const sim = forceSimulation(simNodes)
        .force("charge", forceManyBody().strength(-120))
        .force("link", forceLink(simLinks).id((d: any) => d.id).distance(70).strength(0.4))
        .force("center", forceCenter(w / 2, h / 2).strength(0.08))
        .force("collide", forceCollide(22))
        .alphaDecay(0.02)
        .on("tick", () => {
          cy.batch(() => simNodes.forEach((sn) => {
            if (sn.x != null && sn.y != null) cy.getElementById(sn.id).position({ x: sn.x, y: sn.y });
          }));
          if (!labelsAdded && sim.alpha() < 0.05) {
            cy.animate({ fit: { eles: cy.elements(), padding: 60 }, duration: 600 });
            addGroupLabels(cy); labelsAdded = true;
          }
        });
      bindEvents(cy, sim, nodeMap, onSelectNode, setTooltip, setCtxMenu);
      const fitHandler = () => cy.animate({ fit: { eles: cy.elements(), padding: 50 }, duration: 400 });
      window.addEventListener("nexus:fit", fitHandler);
      fitHandlerRef.current = fitHandler; simRef.current = sim; cyRef.current = cy;
    }
    const cy = cyRef.current;
    for (const n of data.nodes) {
      const node = cy.getElementById(n.id);
      if (node.length) {
        node.data("category", n.category); node.data("sgroup", n.semantic_group || "");
        node.data("summary", n.summary || n.description || ""); node.data("label", slugify(n.name));
        node.data("enriching", !!n.enrich_status);
      }
    }
  }, [data, onSelectNode, buildElements, categoryFilter, isDark]);

  useEffect(() => {
    const cy = cyRef.current; if (!cy) return; cy.nodes().unselect();
    if (selectedId) { const n = cy.getElementById(selectedId); if (n.length) { n.select(); cy.animate({ center: { eles: n }, duration: 300 }); } }
  }, [selectedId]);

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />
      {tooltip && <div className="absolute pointer-events-none px-2 py-1 bg-[var(--nx-surface)] border border-[var(--nx-border-strong)] rounded text-xs text-[var(--nx-text-2)] max-w-[220px] truncate z-10"
        style={{ left: tooltip.x, top: tooltip.y, transform: "translate(-50%, -100%)" }}>{tooltip.text}</div>}
      {ctxMenu && (
        <div className="absolute z-20 bg-[var(--nx-surface)] border border-[var(--nx-border-strong)] rounded-lg shadow-lg py-1 min-w-[120px]"
          style={{ left: ctxMenu.x, top: ctxMenu.y }}>
          {[
            { label: "enrich", action: () => { enrich.mutate({ id: ctxMenu.nodeId }); onSelectNode(ctxMenu.nodeId); setCtxMenu(null); } },
            { label: "connect", action: () => { onSelectNode(ctxMenu.nodeId); setCtxMenu(null); } },
            { label: "delete", action: () => { deleteConcept.mutate(ctxMenu.nodeId); onSelectNode(null); setCtxMenu(null); } },
          ].map((item) => (
            <button key={item.label} onClick={item.action}
              className={`block w-full text-left px-3 py-1.5 text-xs hover:bg-[var(--nx-hover)] ${item.label === "delete" ? "text-red-400" : "text-[var(--nx-text-2)]"}`}>
              {item.label}
            </button>
          ))}
        </div>
      )}
      {graphFind !== null && (
        <input ref={findRef} value={graphFind} onChange={(e) => setGraphFind(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Escape") { setGraphFind(null); } }}
          placeholder="Find in graph..." className="absolute top-3 left-1/2 -translate-x-1/2 z-20 w-64 px-3 py-1.5 bg-[var(--nx-surface)] border border-[var(--nx-border-strong)] rounded-lg text-sm text-[var(--nx-text)] outline-none placeholder:text-[var(--nx-text-4)]" />
      )}
      <div className="absolute bottom-3 right-3 flex gap-1.5">
        <FabBtn label="+" onClick={() => window.dispatchEvent(new CustomEvent("nexus:add"))} />
        <FabBtn label="?" onClick={() => window.dispatchEvent(new CustomEvent("nexus:chat"))} />
      </div>
    </div>
  );
}

const FabBtn = ({ label, onClick }: { label: string; onClick: () => void }) => (
  <button onClick={onClick} className="w-8 h-8 border border-[var(--nx-border-strong)] rounded-md bg-[var(--nx-bg)] text-[var(--nx-text-3)] hover:text-[var(--nx-text)] hover:border-[var(--nx-border-strong)] text-sm transition-colors">{label}</button>
);
