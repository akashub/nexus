import { useEffect, useRef, useState } from "react";
import { useConcept, useConceptContext, useConcepts, useEdges, useEnrichConcept, useUpdateConcept } from "../hooks/useApi";
import { slugify } from "../types";
import ConnectModal from "./ConnectModal";
import QuickstartContent from "./QuickstartContent";

const STATUS_LABELS: Record<string, string> = {
  fetching_docs: "fetching docs from context7...",
  generating: "generating description with AI...",
  fetching_quickstart: "pulling quickstart examples...",
  embedding: "generating embeddings...",
  connecting: "finding related concepts...",
};

interface Props { conceptId: string; onClose: () => void; onNavigate: (id: string) => void; }

export default function SidePanel({ conceptId, onClose, onNavigate }: Props) {
  const { data: concept, isLoading, isError } = useConcept(
    conceptId, (q: any) => q.state.data?.enrich_status ? 1000 : false,
  );
  const { data: edges } = useEdges(conceptId);
  const { data: allConcepts } = useConcepts();
  const { data: ctx } = useConceptContext(conceptId);
  const enrich = useEnrichConcept();
  const update = useUpdateConcept();
  const [showConnect, setShowConnect] = useState(false);
  const [noteDraft, setNoteDraft] = useState(concept?.notes ?? "");
  const [enrichSource, setEnrichSource] = useState("auto");
  const initRef = useRef<string | null>(null);

  useEffect(() => {
    if (concept && initRef.current !== conceptId) {
      initRef.current = conceptId;
      setNoteDraft(concept.notes ?? "");
    }
  }, [concept, conceptId]);

  const nameById = (id: string) => {
    const c = allConcepts?.find((c) => c.id === id);
    return c ? slugify(c.name) : id.slice(0, 8);
  };
  const outgoing = edges?.filter((e) => e.source_id === conceptId) || [];
  const incoming = edges?.filter((e) => e.target_id === conceptId) || [];

  return (
    <div className="w-80 shrink-0 border-l border-[var(--nx-border-strong)] bg-[var(--nx-surface)] p-4 overflow-y-auto flex flex-col">
      <div className="flex items-start justify-between mb-2">
        <h2 className="text-base font-medium text-[var(--nx-text)]">
          {concept ? slugify(concept.name) : "loading..."}
        </h2>
        <button onClick={onClose} className="text-[var(--nx-text-4)] hover:text-[var(--nx-text)] text-lg leading-none">&times;</button>
      </div>
      {isLoading && <p className="text-xs text-[var(--nx-text-3)] animate-pulse">loading concept...</p>}
      {isError && <p className="text-xs text-red-400">failed to load concept</p>}
      {concept && (
        <>
          <div className="flex gap-1.5 flex-wrap mb-3">
            {concept.category && (
              <span className="px-2 py-0.5 border border-[var(--nx-border-strong)] rounded text-[11px] text-[var(--nx-text-2)] uppercase tracking-wider">{concept.category}</span>
            )}
            {concept.semantic_group && (
              <span className="px-2 py-0.5 bg-[var(--nx-accent-bg)] border border-[var(--nx-accent)]/20 rounded text-[11px] text-[var(--nx-accent)] tracking-wider">{concept.semantic_group}</span>
            )}
          </div>
          {concept.enrich_status && (
            <div className="flex items-center gap-2 text-xs text-blue-400 mb-3">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
              {STATUS_LABELS[concept.enrich_status] || concept.enrich_status}
            </div>
          )}
          {concept.summary && (
            <p className="text-sm text-[var(--nx-text)] leading-snug mb-3 font-medium">{concept.summary}</p>
          )}
          <Sec title="description">
            {concept.description
              ? <p className="text-xs text-[var(--nx-text-2)] leading-relaxed">{concept.description}</p>
              : <p className="text-xs text-[var(--nx-text-4)]">not enriched yet — click &ldquo;enrich&rdquo; below</p>}
          </Sec>
          {(ctx?.usage_summary || ctx?.usage_context) && (
            <Sec title="usage in project">
              <p className="text-xs text-[var(--nx-text-2)] leading-relaxed">{ctx.usage_summary || ctx.usage_context?.slice(0, 600)}</p>
            </Sec>
          )}
          {ctx?.claude_memories && ctx.claude_memories.length > 0 && (
            <Sec title="from dev sessions">
              {ctx.claude_memories.map((m, i) => (
                <p key={i} className="text-xs text-[var(--nx-text-3)] leading-relaxed mb-1 border-l-2 border-[var(--nx-border)] pl-2">{m.slice(0, 200)}</p>
              ))}
            </Sec>
          )}
          {ctx?.install_commands && ctx.install_commands.length > 0 && (
            <Sec title="install history">
              {ctx.install_commands.map((cmd, i) => (
                <code key={i} className="block text-[11px] text-[var(--nx-text-3)] bg-[var(--nx-input)] px-2 py-1 rounded mb-1 font-mono truncate">{cmd}</code>
              ))}
            </Sec>
          )}
          {concept.setup_commands?.length > 0 && (
            <Sec title="setup">
              {concept.setup_commands.map((cmd, i) => (
                <code key={i} className="block text-[11px] text-[var(--nx-text-3)] bg-[var(--nx-input)] px-2 py-1 rounded mb-1 font-mono truncate">{cmd}</code>
              ))}
            </Sec>
          )}
          <ConnectionList outgoing={outgoing} incoming={incoming} nameById={nameById} onNavigate={onNavigate} />
          <Sec title="notes">
            <textarea value={noteDraft} onChange={(e) => setNoteDraft(e.target.value)}
              onBlur={() => { if (noteDraft !== (concept.notes ?? "")) update.mutate({ id: conceptId, notes: noteDraft || undefined }); }}
              placeholder="add notes..." rows={3}
              className="w-full bg-[var(--nx-input)] border border-[var(--nx-border)] rounded px-2 py-1.5 text-xs text-[var(--nx-text-2)] placeholder:text-[var(--nx-text-4)] leading-relaxed resize-none outline-none focus:border-[var(--nx-border-strong)] transition-colors" />
          </Sec>
          {concept.quickstart && <Sec title="quickstart (context7)"><QuickstartContent text={concept.quickstart} /></Sec>}
          {concept.doc_url && (
            <Sec title="docs">
              <a href={concept.doc_url} target="_blank" rel="noopener noreferrer"
                className="text-xs text-[var(--nx-accent)] hover:underline underline-offset-2 break-all">{concept.doc_url}</a>
            </Sec>
          )}
          <Sec title="source">
            <p className="text-[11px] text-[var(--nx-text-4)]">
              {concept.source === "manual" ? "added manually" : `enriched via ${concept.source}`} · {timeAgo(concept.created_at)}
            </p>
          </Sec>
          <div className="mt-auto pt-3 flex flex-col gap-2">
            <div className="flex gap-2">
              <button onClick={() => setShowConnect(true)}
                className="flex-1 px-3 py-1.5 text-xs text-[var(--nx-text-2)] border border-[var(--nx-border-strong)] rounded hover:bg-[var(--nx-hover)] transition-colors">
                connect &rarr;
              </button>
              <button onClick={() => enrich.mutate({ id: conceptId, mode: enrichSource })} disabled={enrich.isPending || !!concept.enrich_status}
                className="flex-1 px-3 py-1.5 text-xs text-[var(--nx-text-2)] border border-[var(--nx-border-strong)] rounded hover:bg-[var(--nx-hover)] disabled:opacity-50 transition-colors">
                {concept.enrich_status ? "enriching..." : "enrich"}
              </button>
            </div>
            <select value={enrichSource} onChange={(e) => setEnrichSource(e.target.value)}
              className="w-full px-2 py-1 text-[11px] text-[var(--nx-text-3)] bg-[var(--nx-input)] border border-[var(--nx-border)] rounded outline-none">
              <option value="auto">auto (waterfall)</option>
              <option value="all">all sources (merged)</option>
              <option value="context7">context7</option>
              <option value="pypi">pypi</option>
              <option value="npm">npm</option>
              <option value="github">github</option>
              <option value="libraries">libraries.io</option>
            </select>
          </div>
        </>
      )}
      {showConnect && concept && <ConnectModal sourceId={conceptId} sourceName={concept.name} onClose={() => setShowConnect(false)} />}
    </div>
  );
}

function ConnectionList({ outgoing, incoming, nameById, onNavigate }: { outgoing: any[]; incoming: any[]; nameById: (id: string) => string; onNavigate: (id: string) => void }) {
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

function Sec({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="mb-3"><h3 className="text-[11px] text-[var(--nx-text-4)] uppercase tracking-wider mb-1">{title}</h3>{children}</div>;
}

function timeAgo(d: string): string {
  const m = Math.floor((Date.now() - new Date(d).getTime()) / 60000);
  if (m < 60) return `${m}m ago`;
  return m < 1440 ? `${Math.floor(m / 60)}h ago` : `${Math.floor(m / 1440)}d ago`;
}
