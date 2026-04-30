import { useState } from "react";
import { useAddEdge, useConcepts } from "../hooks/useApi";
import { slugify } from "../types";

const RELATIONSHIPS = ["related_to", "uses", "depends_on", "similar_to", "part_of"];

interface Props { sourceId: string; sourceName: string; onClose: () => void; }

export default function ConnectModal({ sourceId, sourceName, onClose }: Props) {
  const [targetId, setTargetId] = useState("");
  const [relationship, setRelationship] = useState("related_to");
  const { data: concepts } = useConcepts();
  const addEdge = useAddEdge();
  const targets = concepts?.filter((c) => c.id !== sourceId) || [];

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!targetId) return;
    addEdge.mutate({ source_id: sourceId, target_id: targetId, relationship }, { onSuccess: onClose });
  }

  const inputCls = "mt-1 w-full px-3 py-2 bg-[var(--nx-input)] border border-[var(--nx-border)] rounded-lg text-[var(--nx-text)] text-sm outline-none";

  return (
    <div className="fixed inset-0 bg-[var(--nx-overlay)] flex items-center justify-center z-50" onClick={onClose}>
      <form onSubmit={handleSubmit} onClick={(e) => e.stopPropagation()}
        className="w-full max-w-sm bg-[var(--nx-surface)] border border-[var(--nx-border-strong)] rounded-xl shadow-2xl p-5">
        <h2 className="text-sm font-semibold text-[var(--nx-text)] mb-3">Connect from {slugify(sourceName)}</h2>

        <label className="block mb-3">
          <span className="text-[11px] text-[var(--nx-text-3)] uppercase tracking-wide">Target</span>
          <select value={targetId} onChange={(e) => setTargetId(e.target.value)} className={inputCls}>
            <option value="">Select a concept...</option>
            {targets.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </label>

        <label className="block mb-4">
          <span className="text-[11px] text-[var(--nx-text-3)] uppercase tracking-wide">Relationship</span>
          <select value={relationship} onChange={(e) => setRelationship(e.target.value)} className={inputCls}>
            {RELATIONSHIPS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>

        <div className="flex gap-2 justify-end">
          <button type="button" onClick={onClose}
            className="px-4 py-2 text-sm text-[var(--nx-text-3)] hover:text-[var(--nx-text)] transition-colors">Cancel</button>
          <button type="submit" disabled={!targetId || addEdge.isPending}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg disabled:opacity-50 transition-colors">
            {addEdge.isPending ? "Connecting..." : "Connect"}
          </button>
        </div>
        {addEdge.isError && <p className="mt-2 text-sm text-red-400">{addEdge.error.message}</p>}
      </form>
    </div>
  );
}
