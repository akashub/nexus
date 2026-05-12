import cytoscape from "cytoscape";
import { useCallback, useEffect, useRef, useState } from "react";
import { useAddProject, useDetectProjects, useScanProject } from "../hooks/useApi";
import { useTheme } from "../hooks/useTheme";
import type { GlobalGraphData } from "../types";
import { globalGraphStyles } from "./graphStyles";

interface Props {
  data: GlobalGraphData | undefined;
  onSelectProject: (id: string) => void;
}

export default function GlobalGraphView({ data, onSelectProject }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const selectRef = useRef(onSelectProject);
  selectRef.current = onSelectProject;
  const { resolved } = useTheme();
  const isDark = resolved === "dark";

  const buildElements = useCallback((d: GlobalGraphData): cytoscape.ElementDefinition[] => {
    return [
      ...d.nodes.map((n) => ({
        data: {
          id: n.id, label: n.name, count: n.concept_count,
          size: 20 + Math.min(n.concept_count, 20) * 1,
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
    if (cyRef.current) cyRef.current.style().fromJson(globalGraphStyles(isDark)).update();
  }, [isDark]);

  useEffect(() => {
    if (!containerRef.current || !data || data.nodes.length === 0) return;
    if (!cyRef.current) {
      cyRef.current = cytoscape({
        container: containerRef.current,
        style: globalGraphStyles(isDark),
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
  }, [data, buildElements, isDark]);

  if (!data || data.nodes.length === 0) {
    return <EmptyState />;
  }

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />
      {data.unassigned_count > 0 && (
        <div className="absolute bottom-3 left-3 text-[11px] text-[var(--nx-text-4)]">
          {data.unassigned_count} unassigned concept{data.unassigned_count !== 1 ? "s" : ""}
        </div>
      )}
    </div>
  );
}

function EmptyState() {
  const { data: detected } = useDetectProjects();
  const addProject = useAddProject();
  const scanProject = useScanProject();
  const [adding, setAdding] = useState<string | null>(null);

  async function handleAdd(d: { name: string; path: string }) {
    setAdding(d.path);
    addProject.mutate({ name: d.name, path: d.path }, {
      onSuccess: (p) => scanProject.mutate(p.id),
      onSettled: () => setAdding(null),
    });
  }

  return (
    <div className="flex items-center justify-center h-full text-[var(--nx-text-3)] text-sm">
      <div className="w-full max-w-md px-4">
        <p className="text-center mb-4">no projects yet</p>
        {detected && detected.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-[11px] text-[var(--nx-text-4)] uppercase tracking-wide mb-2">
              detected on your machine
            </p>
            {detected.map((d) => (
              <div key={d.path}
                className="flex items-center justify-between px-3 py-2 bg-[var(--nx-surface)] border border-[var(--nx-border)] rounded-lg">
                <div className="min-w-0">
                  <p className="text-sm text-[var(--nx-text)] truncate">{d.name}</p>
                  <p className="text-[10px] text-[var(--nx-text-4)] truncate">{d.path}</p>
                </div>
                <button onClick={() => handleAdd(d)} disabled={adding === d.path}
                  className="ml-3 px-3 py-1 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded-md disabled:opacity-50 shrink-0">
                  {adding === d.path ? "Adding..." : "Add & Scan"}
                </button>
              </div>
            ))}
          </div>
        )}
        <p className="text-xs text-[var(--nx-text-4)] mt-4 text-center">
          or run <code className="bg-[var(--nx-input)] px-1.5 py-0.5 rounded">nexus scan /path/to/project</code>
        </p>
      </div>
    </div>
  );
}
