import { useEffect, useRef, useState } from "react";
import { useConcept, useConcepts, useEdges, useEnrichConcept, useUpdateConcept } from "../hooks/useApi";
import { slugify } from "../types";
import ConnectModal from "./ConnectModal";

interface Props {
  conceptId: string;
  onClose: () => void;
  onNavigate: (id: string) => void;
}

export default function SidePanel({ conceptId, onClose, onNavigate }: Props) {
  const { data: concept, isLoading, isError } = useConcept(conceptId);
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

          {concept.description ? (
            <PanelSection title="description">
              <p className="text-[11px] text-gray-400 leading-relaxed">{concept.description}</p>
            </PanelSection>
          ) : (
            <PanelSection title="description">
              <p className="text-[11px] text-gray-600 mb-2">no description yet</p>
              <button
                onClick={() => enrich.mutate(conceptId)}
                disabled={enrich.isPending}
                className="px-2.5 py-1 text-[10px] text-blue-400 border border-blue-500/20 rounded hover:bg-blue-500/10 disabled:opacity-50 transition-colors"
              >
                {enrich.isPending ? "enriching..." : "enrich with AI"}
              </button>
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
              {" · "}
              {getTimeAgo(concept.created_at)}
            </p>
          </PanelSection>

          <div className="mt-auto pt-3 flex gap-2">
            <button
              onClick={() => setShowConnect(true)}
              className="flex-1 px-3 py-1.5 text-[11px] text-gray-400 border border-white/[0.1] rounded hover:bg-white/[0.04] transition-colors"
            >
              connect &rarr;
            </button>
            <button
              onClick={() => enrich.mutate(conceptId)}
              disabled={enrich.isPending}
              className="flex-1 px-3 py-1.5 text-[11px] text-gray-400 border border-white/[0.1] rounded hover:bg-white/[0.04] disabled:opacity-50 transition-colors"
            >
              {enrich.isPending ? "enriching..." : "research"}
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

function getTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}
