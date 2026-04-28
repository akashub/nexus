import { useRecentConcepts, useStats } from "../hooks/useApi";

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

  const totalCount = stats ? stats.concept_count : 0;

  return (
    <div className="w-44 shrink-0 border-r border-white/[0.06] flex flex-col overflow-hidden">
      <div className="px-3 pt-3 pb-2">
        <h3 className="text-[10px] text-gray-600 uppercase tracking-wider mb-1.5">categories</h3>
        <button
          onClick={() => onCategoryFilter(null)}
          className={`flex items-center gap-1.5 w-full text-left text-[11px] py-0.5 px-1 rounded transition-colors ${
            categoryFilter === null ? "text-gray-200 bg-white/[0.06]" : "text-gray-500 hover:text-gray-300"
          }`}
        >
          <span>•</span>
          <span className="flex-1">all</span>
          <span className="text-[10px] text-gray-700">{totalCount}</span>
        </button>
        {CATEGORIES.map((cat) => {
          const count = stats?.categories[cat] || 0;
          return (
            <button
              key={cat}
              onClick={() => onCategoryFilter(categoryFilter === cat ? null : cat)}
              className={`flex items-center gap-1.5 w-full text-left text-[11px] py-0.5 px-1 rounded transition-colors ${
                categoryFilter === cat ? "text-gray-200 bg-white/[0.06]" : "text-gray-500 hover:text-gray-300"
              }`}
            >
              <span>•</span>
              <span className="flex-1">{cat}</span>
              <span className="text-[10px] text-gray-700">{count}</span>
            </button>
          );
        })}
      </div>

      <div className="px-3 py-2">
        <h3 className="text-[10px] text-gray-600 uppercase tracking-wider mb-1.5">recent</h3>
        {recent && recent.length > 0 ? (
          recent.slice(0, 5).map((c) => (
            <button
              key={c.id}
              onClick={() => onSelectNode(c.id)}
              className={`flex items-center gap-1.5 w-full text-left text-[11px] py-0.5 px-1 rounded transition-colors truncate ${
                c.id === selectedId ? "text-gray-200 bg-white/[0.06]" : "text-gray-500 hover:text-gray-300"
              }`}
            >
              <span>•</span>
              <span className="truncate">{c.name.toLowerCase().replace(/\s+/g, "_")}</span>
            </button>
          ))
        ) : (
          <p className="text-[11px] text-gray-700 px-1">no concepts yet</p>
        )}
      </div>
    </div>
  );
}
