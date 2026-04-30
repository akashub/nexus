import type cytoscape from "cytoscape";
import type { forceSimulation, SimulationNodeDatum } from "d3-force";

interface SimNode extends SimulationNodeDatum { id: string }

export function addGroupLabels(cy: cytoscape.Core) {
  const centroids = new Map<string, { sx: number; sy: number; n: number }>();
  cy.nodes().forEach((node) => {
    const sg = node.data("sgroup"); if (!sg) return;
    const p = node.position(), c = centroids.get(sg) || { sx: 0, sy: 0, n: 0 };
    c.sx += p.x; c.sy += p.y; c.n++; centroids.set(sg, c);
  });
  centroids.forEach((c, sg) => {
    cy.add({ data: { id: `_lbl_${sg}`, label: sg.toLowerCase() }, position: { x: c.sx / c.n, y: c.sy / c.n - 40 },
      locked: true, grabbable: false, selectable: false, classes: "cat-label" });
  });
}

export function bindEvents(
  cy: cytoscape.Core, sim: ReturnType<typeof forceSimulation<SimNode>>, nodeMap: Map<string, SimNode>,
  onSelectNode: (id: string | null) => void, setTooltip: (t: { x: number; y: number; text: string } | null) => void,
  setCtxMenu: (m: { x: number; y: number; nodeId: string } | null) => void,
) {
  cy.on("tap", "node", (evt) => { if (!evt.target.hasClass("cat-label")) onSelectNode(evt.target.id()); });
  cy.on("tap", (evt) => { if (evt.target === cy) onSelectNode(null); });
  cy.on("dbltap", "node", (evt) => { if (!evt.target.hasClass("cat-label")) window.dispatchEvent(new CustomEvent("nexus:edit", { detail: evt.target.id() })); });
  cy.on("mouseover", "node", (evt) => {
    const n = evt.target; if (n.hasClass("cat-label")) return;
    const sg = n.data("sgroup");
    const sameGroup = sg ? cy.nodes().filter((nd: cytoscape.NodeSingular) => nd.data("sgroup") === sg) : cy.collection();
    const keep = n.closedNeighborhood().union(sameGroup);
    cy.elements().not(keep).not(".cat-label").addClass("dimmed");
    n.addClass("hover"); n.connectedEdges().addClass("edge-hover");
    if (sg) { sameGroup.not(n).addClass("cat-glow"); cy.getElementById(`_lbl_${sg}`).addClass("cat-label-show"); }
    const summary = n.data("summary");
    if (summary) { const pos = n.renderedPosition(); setTooltip({ x: pos.x, y: pos.y - 30, text: summary }); }
  });
  cy.on("mouseout", "node", () => { cy.elements().removeClass("dimmed hover edge-hover cat-glow cat-label-show"); setTooltip(null); });
  cy.on("mouseover", "edge", (evt) => evt.target.addClass("edge-hover"));
  cy.on("mouseout", "edge", () => cy.edges().removeClass("edge-hover"));
  cy.on("cxttap", "node", (evt) => {
    evt.originalEvent.preventDefault();
    const pos = evt.target.renderedPosition(); setCtxMenu({ x: pos.x, y: pos.y, nodeId: evt.target.id() });
  });
  cy.on("tap", () => setCtxMenu(null));
  cy.on("grab", "node", (evt) => {
    sim.alphaTarget(0.3).restart();
    const sn = nodeMap.get(evt.target.id()); if (sn) { sn.fx = evt.target.position().x; sn.fy = evt.target.position().y; }
  });
  cy.on("drag", "node", (evt) => { const sn = nodeMap.get(evt.target.id()); if (sn) { sn.fx = evt.target.position().x; sn.fy = evt.target.position().y; } });
  cy.on("free", "node", (evt) => { sim.alphaTarget(0); const sn = nodeMap.get(evt.target.id()); if (sn) { sn.fx = null; sn.fy = null; } });
}
