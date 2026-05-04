import type { AiModels } from "../hooks/useApiExtra";

export const STATUS_LABELS: Record<string, string> = {
  fetching_docs: "fetching docs from context7...",
  generating: "generating description with AI...",
  fetching_quickstart: "pulling quickstart examples...",
  embedding: "generating embeddings...",
  connecting: "finding related concepts...",
};

export function Sec({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="mb-3"><h3 className="text-[11px] text-[var(--nx-text-4)] uppercase tracking-wider mb-1">{title}</h3>{children}</div>;
}

export function timeAgo(d: string): string {
  const m = Math.floor((Date.now() - new Date(d).getTime()) / 60000);
  if (m < 60) return `${m}m ago`;
  return m < 1440 ? `${Math.floor(m / 60)}h ago` : `${Math.floor(m / 1440)}d ago`;
}

export function CmdList({ cmds }: { cmds: string[] }) {
  return <>{cmds.map((cmd, i) => (
    <div key={i} className="relative group mb-1.5">
      <pre className="text-[11px] text-[var(--nx-text-2)] bg-[var(--nx-input)] border border-[var(--nx-border)] px-2.5 py-1.5 rounded font-mono whitespace-pre-wrap break-all leading-relaxed">{cmd}</pre>
      <button onClick={() => navigator.clipboard.writeText(cmd)}
        className="absolute top-1 right-1 px-1.5 py-0.5 text-[10px] text-[var(--nx-text-4)] hover:text-[var(--nx-text)] bg-[var(--nx-hover)] rounded opacity-0 group-hover:opacity-100 transition-opacity">copy</button>
    </div>
  ))}</>;
}

export function ConnectionList({ outgoing, incoming, nameById, onNavigate }: {
  outgoing: any[]; incoming: any[]; nameById: (id: string) => string; onNavigate: (id: string) => void;
}) {
  return (
    <Sec title="connections">
      {outgoing.map((e: any) => (
        <button key={e.id} onClick={() => onNavigate(e.target_id)} className="flex items-center gap-1 w-full text-left text-xs py-0.5 group">
          <span className="text-[var(--nx-text-4)]">&rarr;</span>
          <span className="text-[var(--nx-text-2)] group-hover:text-[var(--nx-text)] flex-1">{nameById(e.target_id)}</span>
          <span className="text-[var(--nx-text-4)] text-[11px]">{e.relationship}</span>
        </button>
      ))}
      {incoming.map((e: any) => (
        <button key={e.id} onClick={() => onNavigate(e.source_id)} className="flex items-center gap-1 w-full text-left text-xs py-0.5 group">
          <span className="text-[var(--nx-text-4)]">&larr;</span>
          <span className="text-[var(--nx-text-2)] group-hover:text-[var(--nx-text)] flex-1">{nameById(e.source_id)}</span>
          <span className="text-[var(--nx-text-4)] text-[11px]">{e.relationship}</span>
        </button>
      ))}
      {outgoing.length === 0 && incoming.length === 0 && <p className="text-[11px] text-[var(--nx-text-4)]">no connections yet</p>}
    </Sec>
  );
}

const _selCls = "w-full px-2 py-1 text-[11px] text-[var(--nx-text-3)] bg-[var(--nx-input)] border border-[var(--nx-border)] rounded outline-none focus:border-[var(--nx-border-strong)] transition-colors";

export function EnrichOptions({ enrichSource, setEnrichSource, enrichProvider, setEnrichProvider, models }: {
  enrichSource: string; setEnrichSource: (v: string) => void;
  enrichProvider: string; setEnrichProvider: (v: string) => void;
  models: AiModels | undefined;
}) {
  return (
    <div className="flex flex-col gap-1.5 p-2 bg-[var(--nx-bg)]/50 border border-[var(--nx-border)] rounded">
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-[var(--nx-text-4)] w-10 shrink-0">source</span>
        <select value={enrichSource} onChange={(e) => setEnrichSource(e.target.value)} className={_selCls}>
          <option value="auto">auto</option><option value="all">all sources</option>
          <option value="context7">context7</option><option value="pypi">pypi</option>
          <option value="npm">npm</option><option value="github">github</option>
          <option value="libraries">libraries.io</option>
        </select>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-[var(--nx-text-4)] w-10 shrink-0">model</span>
        <select value={enrichProvider} onChange={(e) => setEnrichProvider(e.target.value)} className={_selCls}>
          <option value="">auto</option>
          {models?.ollama.models.map(m => <option key={m} value={`ollama|${m}`}>{m}</option>)}
          {models?.cloud.map(c => (
            <option key={c.provider} value={`${c.provider}|${c.model}`}>{c.provider}: {c.model}</option>
          ))}
        </select>
      </div>
    </div>
  );
}
