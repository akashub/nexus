import cytoscape from "cytoscape";
import { useCallback, useEffect, useRef } from "react";
import type { GlobalGraphData } from "../types";

interface Props {
  data: GlobalGraphData | undefined;
  onSelectProject: (id: string) => void;
}

const PROJECT_COLOR = "#5b8cb8";

function globalStyles(): cytoscape.StylesheetStyle[] {
  return [
    { selector: "node", style: {
      shape: "ellipse", label: "data(label)", "text-valign": "bottom", "text-halign": "center", "text-margin-y": 8,
      "background-color": PROJECT_COLOR, "background-opacity": 0.15, "border-width": 1.5, "border-color": PROJECT_COLOR,
      "border-opacity": 0.6, color: "#9ca3af", "font-size": "11px", "font-family": "'SF Mono', 'Fira Code', monospace",
      width: "data(size)", height: "data(size)", "overlay-opacity": 0,
    } as unknown as cytoscape.Css.Node },
    { selector: "node:active", style: { "overlay-opacity": 0 } as cytoscape.Css.Node },
    { selector: "edge", style: {
      "curve-style": "bezier", width: "data(w)", "line-color": "#1e3d4d", "line-opacity": 0.6,
      label: "data(label)", "font-size": "8px", color: "#4a6a7a", "text-rotation": "autorotate",
      "text-margin-y": -10, "text-background-color": "#0a0a0b", "text-background-opacity": 0.9,
      "text-background-padding": "2px", "overlay-opacity": 0,
      "font-family": "'SF Mono', 'Fira Code', monospace",
    } as cytoscape.Css.Edge },
    { selector: "node.hover", style: {
      "border-opacity": 1, "border-width": 2.5, "background-opacity": 0.3, color: "#e2e8f0",
    } as cytoscape.Css.Node },
  ];
}

export default function GlobalGraphView({ data, onSelectProject }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const selectRef = useRef(onSelectProject);
  selectRef.current = onSelectProject;

  const buildElements = useCallback((d: GlobalGraphData): cytoscape.ElementDefinition[] => {
    return [
      ...d.nodes.map((n) => ({
        data: {
          id: n.id, label: `${n.name}\n(${n.concept_count})`,
          size: 40 + Math.min(n.concept_count, 30) * 2,
        },
      })),
      ...d.edges.map((e) => ({
        data: {
          id: `ge-${e.source_id}-${e.target_id}`, source: e.source_id, target: e.target_id,
          label: `${e.weight} shared`, w: Math.min(1 + e.weight * 0.5, 5),
        },
      })),
    ];
  }, []);

  useEffect(() => {
    if (!containerRef.current || !data || data.nodes.length === 0) return;

    if (!cyRef.current) {
      cyRef.current = cytoscape({
        container: containerRef.current,
        style: globalStyles(),
        userZoomingEnabled: true, userPanningEnabled: true,
        boxSelectionEnabled: false, autoungrabify: false,
        minZoom: 0.3, maxZoom: 3,
      });

      cyRef.current.on("tap", "node", (evt) => selectRef.current(evt.target.id()));
      cyRef.current.on("mouseover", "node", (evt) => {
        evt.target.addClass("hover");
        containerRef.current!.style.cursor = "pointer";
      });
      cyRef.current.on("mouseout", "node", (evt) => {
        evt.target.removeClass("hover");
        containerRef.current!.style.cursor = "default";
      });
    }

    const cy = cyRef.current;
    cy.elements().remove();
    cy.add(buildElements(data));
    cy.layout({ name: "cose", animate: false, padding: 60, nodeRepulsion: () => 8000 } as any).run();
    cy.fit(undefined, 40);

    return () => { cyRef.current?.destroy(); cyRef.current = null; };
  }, [data, buildElements]);

  if (!data || data.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-600 text-sm">
        <div className="text-center">
          <p>no projects yet</p>
          <p className="text-xs text-gray-700 mt-1">
            run <code className="bg-white/[0.04] px-1.5 py-0.5 rounded">nexus scan /path/to/project</code>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />
      {data.unassigned_count > 0 && (
        <div className="absolute bottom-3 left-3 text-[10px] text-gray-600">
          {data.unassigned_count} unassigned concept{data.unassigned_count !== 1 ? "s" : ""}
        </div>
      )}
    </div>
  );
}
