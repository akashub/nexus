import { useScanProject } from "../hooks/useApi";
import type { Project } from "../types";

interface Props {
  project: Project;
  onClose: () => void;
  onOpenProject: (p: Project) => void;
  onReplicate: (p: Project) => void;
}

export default function ProjectPanel({ project, onClose, onOpenProject, onReplicate }: Props) {
  const scan = useScanProject();

  return (
    <div className="w-80 shrink-0 border-l border-[var(--nx-border-strong)] bg-[var(--nx-surface)] p-4 overflow-y-auto flex flex-col">
      <div className="flex items-start justify-between mb-2">
        <h2 className="text-base font-medium text-[var(--nx-text)]">{project.name}</h2>
        <button onClick={onClose} className="text-[var(--nx-text-4)] hover:text-[var(--nx-text)] text-lg leading-none">&times;</button>
      </div>

      <Sec title="path">
        <p className="text-xs text-[var(--nx-text-2)] break-all">{project.path ?? "no path set"}</p>
      </Sec>

      {project.description && (
        <Sec title="description">
          <p className="text-xs text-[var(--nx-text-2)] leading-relaxed">{project.description}</p>
        </Sec>
      )}

      <Sec title="stats">
        <div className="flex flex-col gap-1">
          <div className="flex justify-between text-xs">
            <span className="text-[var(--nx-text-4)]">concepts</span>
            <span className="text-[var(--nx-text-2)]">{project.concept_count ?? 0}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-[var(--nx-text-4)]">last scanned</span>
            <span className="text-[var(--nx-text-2)]">{project.last_scanned_at ? timeAgo(project.last_scanned_at) : "never"}</span>
          </div>
        </div>
      </Sec>

      <div className="mt-auto pt-3 flex flex-col gap-1.5">
        <button onClick={() => onOpenProject(project)}
          className="w-full px-3 py-1.5 text-xs text-[var(--nx-text-2)] border border-[var(--nx-border-strong)] rounded hover:bg-[var(--nx-hover)] transition-colors">
          open graph
        </button>
        <button onClick={() => scan.mutate(project.id)} disabled={scan.isPending}
          className="w-full px-3 py-1.5 text-xs text-[var(--nx-text-2)] border border-[var(--nx-border-strong)] rounded hover:bg-[var(--nx-hover)] disabled:opacity-50 transition-colors">
          {scan.isPending ? "scanning..." : "scan now"}
        </button>
        <button onClick={() => onReplicate(project)}
          className="w-full px-3 py-1.5 text-xs text-[var(--nx-text-2)] border border-[var(--nx-border-strong)] rounded hover:bg-[var(--nx-hover)] transition-colors">
          replicate
        </button>
      </div>
    </div>
  );
}

function Sec({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="mb-3"><h3 className="text-[11px] text-[var(--nx-text-4)] uppercase tracking-wider mb-1">{title}</h3>{children}</div>;
}

function timeAgo(d: string): string {
  const m = Math.floor((Date.now() - new Date(d).getTime()) / 60000);
  if (m < 60) return `${m}m ago`;
  return m < 1440 ? `${Math.floor(m / 60)}h ago` : `${Math.floor(m / 1440)}d ago`;
}
