import { useEffect, useRef, useState } from "react";
import { useAddConcept, useConcept } from "../hooks/useApi";

interface Props {
  onClose: () => void;
}

export default function AddModal({ onClose }: Props) {
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [tags, setTags] = useState("");
  const [notes, setNotes] = useState("");
  const [enrich, setEnrich] = useState(false);
  const [enrichingId, setEnrichingId] = useState<string | null>(null);
  const addConcept = useAddConcept();
  const { data: enrichingConcept } = useConcept(enrichingId ?? "", enrichingId ? 2000 : undefined);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  useEffect(() => {
    if (!enrichingId) return;
    if (enrichingConcept?.description) { onClose(); return; }
    const t = setTimeout(onClose, 30000);
    return () => clearTimeout(t);
  }, [enrichingId, enrichingConcept, onClose]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    addConcept.mutate(
      {
        name: name.trim(),
        category: category || undefined,
        tags: tags ? tags.split(",").map((t) => t.trim()) : undefined,
        notes: notes || undefined,
        no_enrich: !enrich,
      },
      { onSuccess: (data) => enrich ? setEnrichingId(data.id) : onClose() },
    );
  }

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50" onClick={onClose}>
      <form
        onSubmit={handleSubmit}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md bg-[#0f0f10] border border-white/[0.08] rounded-xl shadow-2xl shadow-black/50 p-6"
      >
        <h2 className="text-lg font-semibold text-gray-100 mb-4">Add Concept</h2>

        <label className="block mb-3">
          <span className="text-[11px] text-gray-500 uppercase tracking-wide">Name</span>
          <input
            ref={inputRef}
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full px-3 py-2 bg-white/[0.04] border border-white/[0.06] rounded-lg text-gray-100 text-sm outline-none focus:border-blue-500/50 transition-colors"
          />
        </label>

        <label className="block mb-3">
          <span className="text-[11px] text-gray-500 uppercase tracking-wide">Category</span>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="mt-1 w-full px-3 py-2 bg-white/[0.04] border border-white/[0.06] rounded-lg text-gray-100 text-sm outline-none"
          >
            <option value="">Auto-detect</option>
            <option value="devtool">Devtool</option>
            <option value="framework">Framework</option>
            <option value="concept">Concept</option>
            <option value="pattern">Pattern</option>
            <option value="language">Language</option>
          </select>
        </label>

        <label className="block mb-3">
          <span className="text-[11px] text-gray-500 uppercase tracking-wide">Tags (comma-separated)</span>
          <input
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            className="mt-1 w-full px-3 py-2 bg-white/[0.04] border border-white/[0.06] rounded-lg text-gray-100 text-sm outline-none"
          />
        </label>

        <label className="block mb-3">
          <span className="text-[11px] text-gray-500 uppercase tracking-wide">Notes</span>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            className="mt-1 w-full px-3 py-2 bg-white/[0.04] border border-white/[0.06] rounded-lg text-gray-100 text-sm outline-none resize-none"
          />
        </label>

        <label className="flex items-center gap-2 mb-4 text-sm text-gray-400">
          <input
            type="checkbox"
            checked={enrich}
            onChange={(e) => setEnrich(e.target.checked)}
            className="accent-blue-500"
          />
          Enrich with AI
        </label>

        {enrichingId ? (
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
            enriching with AI...
          </div>
        ) : (
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm text-gray-500 hover:text-gray-200 transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={!name.trim() || addConcept.isPending}
              className="px-4 py-2 bg-blue-600/80 hover:bg-blue-600 border border-blue-500/30 text-blue-100 text-sm rounded-lg disabled:opacity-50 transition-colors">
              {addConcept.isPending ? "Adding..." : "Add"}
            </button>
          </div>
        )}
        {addConcept.isError && (
          <p className="mt-2 text-sm text-red-400/80">{addConcept.error.message}</p>
        )}
      </form>
    </div>
  );
}
