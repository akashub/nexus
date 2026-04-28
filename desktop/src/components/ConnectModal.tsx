import { useState } from "react";
import { useAddEdge, useConcepts } from "../hooks/useApi";

const RELATIONSHIPS = ["related_to", "uses", "depends_on", "similar_to", "part_of"];

interface Props {
  sourceId: string;
  sourceName: string;
  onClose: () => void;
}

export default function ConnectModal({ sourceId, sourceName, onClose }: Props) {
  const [targetId, setTargetId] = useState("");
  const [relationship, setRelationship] = useState("related_to");
  const { data: concepts } = useConcepts();
  const addEdge = useAddEdge();

  const targets = concepts?.filter((c) => c.id !== sourceId) || [];

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!targetId) return;
    addEdge.mutate(
      { source_id: sourceId, target_id: targetId, relationship },
      { onSuccess: onClose },
    );
  }

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50" onClick={onClose}>
      <form
        onSubmit={handleSubmit}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-sm bg-[#0f0f10] border border-white/[0.08] rounded-xl shadow-2xl shadow-black/50 p-5"
      >
        <h2 className="text-sm font-semibold text-gray-100 mb-3">
          Connect from {sourceName.toLowerCase().replace(/\s+/g, "_")}
        </h2>

        <label className="block mb-3">
          <span className="text-[11px] text-gray-500 uppercase tracking-wide">Target</span>
          <select
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            className="mt-1 w-full px-3 py-2 bg-white/[0.04] border border-white/[0.06] rounded-lg text-gray-100 text-sm outline-none"
          >
            <option value="">Select a concept...</option>
            {targets.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>

        <label className="block mb-4">
          <span className="text-[11px] text-gray-500 uppercase tracking-wide">Relationship</span>
          <select
            value={relationship}
            onChange={(e) => setRelationship(e.target.value)}
            className="mt-1 w-full px-3 py-2 bg-white/[0.04] border border-white/[0.06] rounded-lg text-gray-100 text-sm outline-none"
          >
            {RELATIONSHIPS.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </label>

        <div className="flex gap-2 justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-500 hover:text-gray-200 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!targetId || addEdge.isPending}
            className="px-4 py-2 bg-blue-600/80 hover:bg-blue-600 border border-blue-500/30 text-blue-100 text-sm rounded-lg disabled:opacity-50 transition-colors"
          >
            {addEdge.isPending ? "Connecting..." : "Connect"}
          </button>
        </div>

        {addEdge.isError && (
          <p className="mt-2 text-sm text-red-400/80">{addEdge.error.message}</p>
        )}
      </form>
    </div>
  );
}
