import { useRecentConcepts, useStats } from "../hooks/useApi";
import { slugify } from "../types";

const CATEGORIES = ["devtool", "framework", "concept", "pattern", "language"];

interface Props {
  onSelectNode: (id: string) => void;
  selectedId: string | null;
  categoryFilter: string | null;
  onCategoryFilter: (cat: string | null) => void;
}

export default function LeftSidebar({ onSelectNode, selectedId, categoryFilter, onCategoryFilter }: Props) {
  const { data: stats } = useStats();
  const { data: recent } = useRecentConcepts();

  return (
    <div className="w-44 shrink-0 border-r border-[var(--nx-border)] flex flex-col overflow-hidden">
      <div className="px-3 pt-3 pb-2">
        <h3 className="text-[11px] text-[var(--nx-text-4)] uppercase tracking-wider mb-1.5">categories</h3>
        <button
          onClick={() => onCategoryFilter(null)}
          className={`flex items-center gap-1.5 w-full text-left text-xs py-0.5 px-1 rounded transition-colors ${
            categoryFilter === null ? "text-[var(--nx-text)] bg-[var(--nx-hover)]" : "text-[var(--nx-text-3)] hover:text-[var(--nx-text)]"
          }`}
        >
          <span>•</span>
          <span className="flex-1">all</span>
          <span className="text-[11px] text-[var(--nx-text-4)]">{stats?.concept_count ?? 0}</span>
        </button>
        {CATEGORIES.map((cat) => {
          const count = stats?.categories[cat] || 0;
          return (
            <button
              key={cat}
              onClick={() => onCategoryFilter(categoryFilter === cat ? null : cat)}
              className={`flex items-center gap-1.5 w-full text-left text-xs py-0.5 px-1 rounded transition-colors ${
                categoryFilter === cat ? "text-[var(--nx-text)] bg-[var(--nx-hover)]" : "text-[var(--nx-text-3)] hover:text-[var(--nx-text)]"
              }`}
            >
              <span>•</span>
              <span className="flex-1">{cat}</span>
              <span className="text-[11px] text-[var(--nx-text-4)]">{count}</span>
            </button>
          );
        })}
      </div>

      <div className="px-3 py-2">
        <h3 className="text-[11px] text-[var(--nx-text-4)] uppercase tracking-wider mb-1.5">recent</h3>
        {recent && recent.length > 0 ? (
          recent.slice(0, 5).map((c) => (
            <button
              key={c.id}
              onClick={() => onSelectNode(c.id)}
              className={`flex items-center gap-1.5 w-full text-left text-xs py-0.5 px-1 rounded transition-colors truncate ${
                c.id === selectedId ? "text-[var(--nx-text)] bg-[var(--nx-hover)]" : "text-[var(--nx-text-3)] hover:text-[var(--nx-text)]"
              }`}
            >
              <span>•</span>
              <span className="truncate">{slugify(c.name)}</span>
            </button>
          ))
        ) : (
          <p className="text-xs text-[var(--nx-text-4)] px-1">no concepts yet</p>
        )}
      </div>
    </div>
  );
}
