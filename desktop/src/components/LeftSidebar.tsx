import { useProjects, useStats } from "../hooks/useApi";
import { useRecentConcepts } from "../hooks/useApiExtra";
import type { Project } from "../types";
import { slugify } from "../types";

const CATEGORIES = ["devtool", "framework", "concept", "pattern", "language"];

interface Props {
  activeProject: Project | null;
  onSelectProject: (project: Project) => void;
  onBackToGlobal: () => void;
  onAddProject: () => void;
  onSelectNode: (id: string) => void;
  selectedId: string | null;
  categoryFilter: string | null;
  onCategoryFilter: (cat: string | null) => void;
}

export default function LeftSidebar(props: Props) {
  return (
    <div className="w-48 shrink-0 border-r border-[var(--nx-border)] flex flex-col overflow-hidden">
      {props.activeProject ? <ProjectView {...props} /> : <GlobalView {...props} />}
    </div>
  );
}

function GlobalView({ onSelectProject, onAddProject }: Props) {
  const { data: projects } = useProjects();

  return (
    <>
      <div className="px-3 pt-3 pb-2">
        <div className="flex items-center justify-between mb-1.5">
          <h3 className="text-[11px] text-[var(--nx-text-4)] uppercase tracking-wider">projects</h3>
          <button onClick={onAddProject} className="text-xs text-[var(--nx-text-4)] hover:text-[var(--nx-text)] transition-colors">+</button>
        </div>
        {projects && projects.length > 0 ? (
          projects.map((p) => (
            <button key={p.id} onClick={() => onSelectProject(p)}
              className="flex items-center gap-1.5 w-full text-left text-xs py-1 px-1 rounded text-[var(--nx-text-2)] hover:text-[var(--nx-text)] hover:bg-[var(--nx-hover)] transition-colors group">
              <span className="text-[var(--nx-text-4)]">/</span>
              <span className="flex-1 truncate">{p.name}</span>
              <span className="text-[10px] text-[var(--nx-text-4)]">{p.concept_count ?? 0}</span>
            </button>
          ))
        ) : (
          <p className="text-xs text-[var(--nx-text-4)] px-1">no projects yet</p>
        )}
      </div>

      <div className="px-3 py-2 border-t border-[var(--nx-border)]">
        <h3 className="text-[11px] text-[var(--nx-text-4)] uppercase tracking-wider mb-1.5">quick start</h3>
        <div className="space-y-1.5 text-[10px] text-[var(--nx-text-4)]">
          <CmdHint cmd="nexus project add &quot;name&quot; --path /path" label="add a project" />
          <CmdHint cmd="nexus scan /path/to/project" label="scan a project" />
          <CmdHint cmd="nexus add &quot;react&quot;" label="add a concept" />
          <CmdHint cmd="nexus ask &quot;what is MCP?&quot;" label="ask a question" />
        </div>
      </div>
    </>
  );
}

function CmdHint({ cmd, label }: { cmd: string; label: string }) {
  return (
    <button onClick={() => navigator.clipboard.writeText(cmd)}
      className="block w-full text-left group">
      <span className="text-[var(--nx-text-3)]">{label}</span>
      <code className="block mt-0.5 text-[var(--nx-text-4)] group-hover:text-[var(--nx-text-3)] font-mono truncate transition-colors">
        $ {cmd}
      </code>
    </button>
  );
}

function ProjectView({ activeProject, onBackToGlobal, onSelectNode, selectedId, categoryFilter, onCategoryFilter }: Props) {
  const { data: stats } = useStats();
  const { data: recent } = useRecentConcepts();

  return (
    <>
      <div className="px-3 pt-2.5 pb-1.5 border-b border-[var(--nx-border)]">
        <button onClick={onBackToGlobal}
          className="flex items-center gap-1 text-xs text-[var(--nx-text-3)] hover:text-[var(--nx-text)] transition-colors mb-1">
          <span>&larr;</span> <span>all projects</span>
        </button>
        <p className="text-xs text-[var(--nx-text)] font-medium truncate">{activeProject!.name}</p>
        {activeProject!.path && (
          <p className="text-[10px] text-[var(--nx-text-4)] truncate mt-0.5" title={activeProject!.path}>{activeProject!.path}</p>
        )}
      </div>

      <div className="px-3 pt-2 pb-2">
        <h3 className="text-[11px] text-[var(--nx-text-4)] uppercase tracking-wider mb-1.5">categories</h3>
        <CatButton label="all" count={stats?.concept_count ?? 0} active={categoryFilter === null} onClick={() => onCategoryFilter(null)} />
        {CATEGORIES.map((cat) => (
          <CatButton key={cat} label={cat} count={stats?.categories[cat] || 0}
            active={categoryFilter === cat} onClick={() => onCategoryFilter(categoryFilter === cat ? null : cat)} />
        ))}
      </div>

      <div className="px-3 py-2">
        <h3 className="text-[11px] text-[var(--nx-text-4)] uppercase tracking-wider mb-1.5">recent</h3>
        {recent && recent.length > 0 ? (
          recent.slice(0, 5).map((c) => (
            <button key={c.id} onClick={() => onSelectNode(c.id)}
              className={`flex items-center gap-1.5 w-full text-left text-xs py-0.5 px-1 rounded transition-colors truncate ${
                c.id === selectedId ? "text-[var(--nx-text)] bg-[var(--nx-hover)]" : "text-[var(--nx-text-3)] hover:text-[var(--nx-text)]"
              }`}>
              <span>·</span>
              <span className="truncate">{slugify(c.name)}</span>
            </button>
          ))
        ) : (
          <p className="text-xs text-[var(--nx-text-4)] px-1">no concepts yet</p>
        )}
      </div>
    </>
  );
}

function CatButton({ label, count, active, onClick }: { label: string; count: number; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick}
      className={`flex items-center gap-1.5 w-full text-left text-xs py-0.5 px-1 rounded transition-colors ${
        active ? "text-[var(--nx-text)] bg-[var(--nx-hover)]" : "text-[var(--nx-text-3)] hover:text-[var(--nx-text)]"
      }`}>
      <span>·</span>
      <span className="flex-1">{label}</span>
      <span className="text-[11px] text-[var(--nx-text-4)]">{count}</span>
    </button>
  );
}
