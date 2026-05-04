import { useGaps, type GapResult } from "../hooks/useApiExtra";

interface Props {
  projectId: string;
  projectName: string;
  onClose: () => void;
}

export default function GapsPanel({ projectId, projectName, onClose }: Props) {
  const { data: gaps, isLoading } = useGaps(projectId);

  return (
    <div className="w-72 shrink-0 border-l border-[var(--nx-border)] flex flex-col overflow-hidden bg-[var(--nx-bg)]">
      <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--nx-border)]">
        <h3 className="text-xs font-medium text-[var(--nx-text-2)]">Gap Detection</h3>
        <button onClick={onClose} className="text-[var(--nx-text-4)] hover:text-[var(--nx-text)] text-sm">&times;</button>
      </div>

      <div className="px-3 py-1.5 border-b border-[var(--nx-border)]">
        <span className="text-[10px] text-[var(--nx-text-4)]">{projectName}</span>
        {gaps && (
          <span className="text-[10px] text-[var(--nx-text-4)] ml-2">
            &middot; {gaps.length === 0 ? "no gaps" : `${gaps.length} gap${gaps.length > 1 ? "s" : ""}`}
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-2">
        {isLoading && <p className="text-xs text-[var(--nx-text-4)]">analyzing...</p>}
        {gaps && gaps.length === 0 && (
          <div className="text-center py-8">
            <p className="text-xs text-[var(--nx-text-3)]">no gaps detected</p>
            <p className="text-[10px] text-[var(--nx-text-4)] mt-1">your stack looks complete</p>
          </div>
        )}
        {gaps && gaps.map((g) => <GapCard key={g.category} gap={g} />)}
      </div>
    </div>
  );
}

function GapCard({ gap }: { gap: GapResult }) {
  return (
    <div className="mb-3 p-2.5 rounded-lg border border-[var(--nx-border)] bg-[var(--nx-input)]">
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-[rgba(251,191,36,0.1)] text-[#fbbf24] uppercase tracking-wider font-medium">
          {gap.missing_type}
        </span>
      </div>
      <p className="text-xs text-[var(--nx-text-2)] mb-1">{gap.reason}</p>
      <div className="text-[10px] text-[var(--nx-text-4)] mb-1.5">
        <span>have: </span>
        {gap.have.map((h, i) => (
          <span key={h}>
            <span className="text-[var(--nx-text-3)]">{h}</span>
            {i < gap.have.length - 1 && ", "}
          </span>
        ))}
      </div>
      <div className="text-[10px] text-[var(--nx-text-4)]">
        <span>try: </span>
        {gap.suggestions.slice(0, 4).map((s, i) => (
          <span key={s}>
            <span className="text-[var(--nx-accent)]">{s}</span>
            {i < Math.min(gap.suggestions.length, 4) - 1 && ", "}
          </span>
        ))}
      </div>
    </div>
  );
}
