import { useEffect, useRef, useState } from "react";
import { useConcept, useConcepts, useEdges, useEnrichConcept, useUpdateConcept } from "../hooks/useApi";
import { useAiModels, useConceptContext } from "../hooks/useApiExtra";
import { slugify } from "../types";
import ConnectModal from "./ConnectModal";
import QuickstartContent from "./QuickstartContent";
import { CmdList, ConnectionList, EnrichOptions, Sec, STATUS_LABELS, timeAgo } from "./SidePanelParts";

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
  const [enrichProvider, setEnrichProvider] = useState("");
  const { data: models } = useAiModels();
  const [aiProvider, aiModel] = enrichProvider ? enrichProvider.split("|") : [];
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
            <Sec title="install history"><CmdList cmds={ctx.install_commands} /></Sec>
          )}
          {concept.setup_commands?.length > 0 && (
            <Sec title="setup"><CmdList cmds={concept.setup_commands} /></Sec>
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
          <div className="mt-auto pt-3 flex flex-col gap-1.5">
            <div className="flex gap-2">
              <button onClick={() => setShowConnect(true)}
                className="flex-1 px-3 py-1.5 text-xs text-[var(--nx-text-2)] border border-[var(--nx-border-strong)] rounded hover:bg-[var(--nx-hover)] transition-colors">
                connect &rarr;
              </button>
              <button disabled={enrich.isPending || !!concept.enrich_status}
                onClick={() => enrich.mutate({
                  id: conceptId, mode: enrichSource, provider: aiProvider, model: aiModel,
                })}
                className="flex-1 px-3 py-1.5 text-xs text-[var(--nx-text-2)] border border-[var(--nx-border-strong)] rounded hover:bg-[var(--nx-hover)] disabled:opacity-50 transition-colors">
                {concept.enrich_status ? "enriching..." : "enrich"}
              </button>
            </div>
            <EnrichOptions enrichSource={enrichSource} setEnrichSource={setEnrichSource}
              enrichProvider={enrichProvider} setEnrichProvider={setEnrichProvider} models={models} />
          </div>
        </>
      )}
      {showConnect && concept && <ConnectModal sourceId={conceptId} sourceName={concept.name} onClose={() => setShowConnect(false)} />}
    </div>
  );
}

