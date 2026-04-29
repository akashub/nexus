import { useEffect, useRef, useState } from "react";
import { useConcept, useConcepts, useEdges, useEnrichConcept, useUpdateConcept } from "../hooks/useApi";
import { slugify } from "../types";
import ConnectModal from "./ConnectModal";

const STATUS_LABELS: Record<string, string> = {
  fetching_docs: "fetching docs from context7...",
  generating: "generating description with AI...",
  fetching_quickstart: "pulling quickstart examples...",
  embedding: "generating embeddings...",
  connecting: "finding related concepts...",
};

interface Props {
  conceptId: string;
  onClose: () => void;
  onNavigate: (id: string) => void;
}

export default function SidePanel({ conceptId, onClose, onNavigate }: Props) {
  const { data: concept, isLoading, isError } = useConcept(
    conceptId, (q: any) => q.state.data?.enrich_status ? 1000 : false,
  );
  const { data: edges } = useEdges(conceptId);
  const { data: allConcepts } = useConcepts();
  const enrich = useEnrichConcept();
  const update = useUpdateConcept();
  const [showConnect, setShowConnect] = useState(false);
  const [noteDraft, setNoteDraft] = useState(concept?.notes ?? "");
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
    <div className="w-80 shrink-0 border-l border-white/[0.08] bg-[#111113] p-4 overflow-y-auto flex flex-col">
      <div className="flex items-start justify-between mb-2">
        <h2 className="text-base font-medium text-gray-100">
          {concept ? slugify(concept.name) : "loading..."}
        </h2>
        <button onClick={onClose} className="text-gray-600 hover:text-gray-300 text-lg leading-none">&times;</button>
      </div>

      {isLoading && <p className="text-[11px] text-gray-600 animate-pulse">loading concept...</p>}
      {isError && <p className="text-[11px] text-red-400/80">failed to load concept</p>}

      {concept && (
        <>
          {concept.category && (
            <span className="inline-block self-start px-2 py-0.5 border border-white/[0.1] rounded text-[10px] text-gray-400 uppercase tracking-wider mb-3">
              {concept.category}
            </span>
          )}

          {concept.enrich_status && (
            <div className="flex items-center gap-2 text-[11px] text-blue-400/80 mb-3">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
              {STATUS_LABELS[concept.enrich_status] || concept.enrich_status}
            </div>
          )}

          <PanelSection title="description">
            {concept.description
              ? <p className="text-[11px] text-gray-400 leading-relaxed">{concept.description}</p>
              : <p className="text-[11px] text-gray-600">no description yet</p>}
          </PanelSection>

          {concept.quickstart && (
            <PanelSection title="quickstart"><QuickstartContent text={concept.quickstart} /></PanelSection>
          )}

          {concept.doc_url && (
            <PanelSection title="docs">
              <a href={concept.doc_url} target="_blank" rel="noopener noreferrer"
                className="text-[11px] text-blue-400/80 hover:text-blue-300 underline underline-offset-2 break-all">
                {concept.doc_url}
              </a>
            </PanelSection>
          )}

          {concept.tags.length > 0 && (
            <PanelSection title="tags">
              <div className="flex flex-wrap gap-1">
                {concept.tags.map((tag) => (
                  <span key={tag} className="px-1.5 py-0.5 border border-white/[0.08] text-gray-500 rounded text-[10px]">
                    {tag}
                  </span>
                ))}
              </div>
            </PanelSection>
          )}

          <PanelSection title="connections">
            {outgoing.map((e) => (
              <button key={e.id} onClick={() => onNavigate(e.target_id)}
                className="flex items-center gap-1 w-full text-left text-[11px] py-0.5 group">
                <span className="text-gray-600">&rarr;</span>
                <span className="text-gray-400 group-hover:text-gray-200 flex-1">{nameById(e.target_id)}</span>
                <span className="text-gray-700 text-[10px]">{e.relationship}</span>
              </button>
            ))}
            {incoming.map((e) => (
              <button key={e.id} onClick={() => onNavigate(e.source_id)}
                className="flex items-center gap-1 w-full text-left text-[11px] py-0.5 group">
                <span className="text-gray-600">&larr;</span>
                <span className="text-gray-400 group-hover:text-gray-200 flex-1">{nameById(e.source_id)}</span>
                <span className="text-gray-700 text-[10px]">{e.relationship}</span>
              </button>
            ))}
            {outgoing.length === 0 && incoming.length === 0 && (
              <p className="text-[10px] text-gray-700">no connections yet</p>
            )}
          </PanelSection>

          <PanelSection title="notes">
            <textarea
              value={noteDraft}
              onChange={(e) => setNoteDraft(e.target.value)}
              onBlur={() => {
                if (noteDraft !== (concept.notes ?? ""))
                  update.mutate({ id: conceptId, notes: noteDraft || undefined });
              }}
              placeholder="add notes..."
              rows={3}
              className="w-full bg-white/[0.03] border border-white/[0.06] rounded px-2 py-1.5 text-[11px] text-gray-400 placeholder:text-gray-700 leading-relaxed resize-none outline-none focus:border-white/[0.12] transition-colors"
            />
          </PanelSection>

          <PanelSection title="source">
            <p className="text-[10px] text-gray-700">
              {concept.source === "manual" ? "added manually" : `enriched via ${concept.source}`}
              {" · "}{getTimeAgo(concept.created_at)}
            </p>
          </PanelSection>

          <div className="mt-auto pt-3 flex gap-2">
            <button onClick={() => setShowConnect(true)}
              className="flex-1 px-3 py-1.5 text-[11px] text-gray-400 border border-white/[0.1] rounded hover:bg-white/[0.04] transition-colors">
              connect &rarr;
            </button>
            <button onClick={() => enrich.mutate(conceptId)} disabled={enrich.isPending || !!concept.enrich_status}
              className="flex-1 px-3 py-1.5 text-[11px] text-gray-400 border border-white/[0.1] rounded hover:bg-white/[0.04] disabled:opacity-50 transition-colors">
              {concept.enrich_status ? "enriching..." : "enrich"}
            </button>
          </div>
        </>
      )}

      {showConnect && concept && (
        <ConnectModal sourceId={conceptId} sourceName={concept.name} onClose={() => setShowConnect(false)} />
      )}
    </div>
  );
}

function PanelSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-3">
      <h3 className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">{title}</h3>
      {children}
    </div>
  );
}

function QuickstartContent({ text }: { text: string }) {
  return (
    <div className="space-y-2 max-h-64 overflow-y-auto">{text.split(/(```[\s\S]*?```)/g).filter(Boolean).map((part, i) => {
      const m = part.match(/^```\w*\n?([\s\S]*?)```$/);
      if (m) return (
        <div key={i} className="relative group">
          <pre className="w-full bg-white/[0.03] border border-white/[0.06] rounded px-3 py-2 text-[10px] text-gray-400 leading-relaxed overflow-x-auto whitespace-pre-wrap font-mono">{m[1].trim()}</pre>
          <button onClick={() => navigator.clipboard.writeText(m[1].trim())}
            className="absolute top-1 right-1 px-1.5 py-0.5 text-[9px] text-gray-600 hover:text-gray-300 bg-white/[0.06] rounded opacity-0 group-hover:opacity-100 transition-opacity">copy</button>
        </div>
      );
      return part.trim() ? <p key={i} className="text-[11px] text-gray-400 leading-relaxed">{part.trim()}</p> : null;
    })}</div>
  );
}

function getTimeAgo(d: string): string {
  const m = Math.floor((Date.now() - new Date(d).getTime()) / 60000);
  if (m < 60) return `${m}m ago`;
  return m < 1440 ? `${Math.floor(m / 60)}h ago` : `${Math.floor(m / 1440)}d ago`;
}
