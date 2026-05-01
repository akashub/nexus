import { useState } from "react";
import { useJourney, type JourneyWeek } from "../hooks/useApi";

const CATEGORY_DOTS: Record<string, string> = {
  devtool: "#a78bfa", framework: "#60a5fa", concept: "#4ade80",
  pattern: "#fbbf24", language: "#f87171",
};

interface Props {
  projectId: string | null;
  onClose: () => void;
  onSelectConcept?: (id: string) => void;
}

export default function JourneyPanel({ projectId, onClose, onSelectConcept }: Props) {
  const [days, setDays] = useState(90);
  const { data: weeks, isLoading } = useJourney(projectId, days);

  const total = weeks?.reduce((n, w) => n + w.concepts.length, 0) ?? 0;

  return (
    <div className="w-72 shrink-0 border-l border-[var(--nx-border)] flex flex-col overflow-hidden bg-[var(--nx-bg)]">
      <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--nx-border)]">
        <h3 className="text-xs font-medium text-[var(--nx-text-2)]">Learning Journey</h3>
        <button onClick={onClose} className="text-[var(--nx-text-4)] hover:text-[var(--nx-text)] text-sm">&times;</button>
      </div>

      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-[var(--nx-border)]">
        {[30, 90, 180, 365].map((d) => (
          <button key={d} onClick={() => setDays(d)}
            className={`text-[10px] px-1.5 py-0.5 rounded transition-colors ${
              days === d ? "bg-[var(--nx-hover)] text-[var(--nx-text)]" : "text-[var(--nx-text-4)] hover:text-[var(--nx-text-3)]"
            }`}>
            {d}d
          </button>
        ))}
        <span className="flex-1" />
        <span className="text-[10px] text-[var(--nx-text-4)]">{total} concepts</span>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-2">
        {isLoading && <p className="text-xs text-[var(--nx-text-4)]">loading...</p>}
        {weeks && weeks.length === 0 && <p className="text-xs text-[var(--nx-text-4)]">no concepts in this range</p>}
        {weeks && weeks.map((w) => <WeekGroup key={w.week} week={w} onSelect={onSelectConcept} />)}
      </div>
    </div>
  );
}

function WeekGroup({ week, onSelect }: { week: JourneyWeek; onSelect?: (id: string) => void }) {
  const dt = new Date(week.week_start);
  const label = dt.toLocaleDateString("en-US", { month: "short", day: "numeric" });

  return (
    <div className="mb-3">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[10px] text-[var(--nx-text-4)] uppercase tracking-wider">Week of {label}</span>
        <span className="text-[10px] text-[var(--nx-text-4)]">&middot; {week.concepts.length}</span>
      </div>
      {week.concepts.map((c, i) => {
        const isLast = i === week.concepts.length - 1;
        const color = CATEGORY_DOTS[c.category ?? ""] ?? "#94a3b8";
        return (
          <button key={c.id} onClick={() => onSelect?.(c.id)}
            className="flex items-start gap-2 w-full text-left py-0.5 pl-2 hover:bg-[var(--nx-hover)] rounded transition-colors group">
            <span className="text-[var(--nx-text-4)] text-[10px] mt-0.5 shrink-0">{isLast ? "└" : "├"}</span>
            <div className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ backgroundColor: color }} />
            <div className="min-w-0">
              <span className="text-xs text-[var(--nx-text-2)] group-hover:text-[var(--nx-text)] transition-colors">{c.name}</span>
              {c.summary && (
                <p className="text-[10px] text-[var(--nx-text-4)] truncate">{c.summary}</p>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}
