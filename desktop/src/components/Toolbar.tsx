import type { Project } from "../types";

interface Props {
  activeProject: Project | null;
  enrichPolling: boolean;
  enrichLabel: string | null | undefined;
  onSearch: () => void;
  onAdd: () => void;
  onChat: () => void;
  onEnrichAll: () => void;
  onJourney: () => void;
  onGaps: () => void;
  onFit: () => void;
}

export default function Toolbar({ activeProject, enrichPolling, enrichLabel, onSearch, onAdd, onChat, onEnrichAll, onJourney, onGaps, onFit }: Props) {
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 border-b border-[var(--nx-border)] shrink-0">
      <input readOnly onClick={onSearch} placeholder="search..."
        className="w-36 px-2 py-1 text-[11px] text-[var(--nx-text-3)] bg-[var(--nx-input)] border border-[var(--nx-border)] rounded cursor-pointer hover:bg-[var(--nx-hover)] transition-colors" />
      <span className="text-[11px] text-[var(--nx-text-4)] ml-0.5">⌘K</span>
      <Shortcut label="add" keys="⌘N" onClick={onAdd} />
      <Shortcut label="ask" keys="⌘/" onClick={onChat} />
      <div className="flex-1" />
      {enrichPolling && enrichLabel && (
        <span className={`text-[11px] ${enrichLabel === "done" ? "text-green-400" : "text-blue-400"}`}>{enrichLabel}</span>
      )}
      {activeProject && <Shortcut label="enrich all" onClick={onEnrichAll} />}
      {activeProject && <Shortcut label="export" onClick={() => downloadExport(activeProject.id, activeProject.name)} />}
      <Shortcut label="journey" onClick={onJourney} />
      {activeProject && <Shortcut label="gaps" onClick={onGaps} />}
      {activeProject && <Shortcut label="fit" onClick={onFit} />}
    </div>
  );
}

function Shortcut({ label, keys, onClick }: { label: string; keys?: string; onClick?: () => void }) {
  return (
    <button onClick={onClick}
      className="px-2 py-0.5 text-[11px] text-[var(--nx-text-3)] border border-[var(--nx-border)] rounded hover:bg-[var(--nx-hover)] hover:text-[var(--nx-text-2)] transition-colors">
      {keys && <span className="mr-1 text-[var(--nx-text-4)]">{keys}</span>}
      {label}
    </button>
  );
}

async function downloadExport(projectId: string, projectName: string) {
  const r = await fetch(`http://127.0.0.1:7777/api/graph/export?format=markdown&project_id=${projectId}`);
  const text = await r.text();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type: "text/markdown" }));
  a.download = `${projectName}-graph.md`;
  a.click();
  URL.revokeObjectURL(a.href);
}
