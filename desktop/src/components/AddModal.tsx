import { useEffect, useRef, useState } from "react";
import { useAddConcept, useConcept } from "../hooks/useApi";

interface Props { onClose: () => void; }

export default function AddModal({ onClose }: Props) {
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [tags, setTags] = useState("");
  const [notes, setNotes] = useState("");
  const [shouldEnrich, setShouldEnrich] = useState(false);
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
      { name: name.trim(), category: category || undefined, tags: tags ? tags.split(",").map((t) => t.trim()) : undefined, notes: notes || undefined, no_enrich: !shouldEnrich },
      { onSuccess: (data) => shouldEnrich ? setEnrichingId(data.id) : onClose() },
    );
  }

  const inputCls = "mt-1 w-full px-3 py-2 bg-[var(--nx-input)] border border-[var(--nx-border)] rounded-lg text-[var(--nx-text)] text-sm outline-none focus:border-[var(--nx-accent)] transition-colors";

  return (
    <div className="fixed inset-0 bg-[var(--nx-overlay)] flex items-center justify-center z-50" onClick={onClose}>
      <form onSubmit={handleSubmit} onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md bg-[var(--nx-surface)] border border-[var(--nx-border-strong)] rounded-xl shadow-2xl p-6">
        <h2 className="text-lg font-semibold text-[var(--nx-text)] mb-4">Add Concept</h2>

        <label className="block mb-3">
          <span className="text-[11px] text-[var(--nx-text-3)] uppercase tracking-wide">Name</span>
          <input ref={inputRef} value={name} onChange={(e) => setName(e.target.value)} className={inputCls} />
        </label>

        <label className="block mb-3">
          <span className="text-[11px] text-[var(--nx-text-3)] uppercase tracking-wide">Category</span>
          <select value={category} onChange={(e) => setCategory(e.target.value)} className={inputCls}>
            <option value="">Auto-detect</option>
            <option value="devtool">Devtool</option>
            <option value="framework">Framework</option>
            <option value="concept">Concept</option>
            <option value="pattern">Pattern</option>
            <option value="language">Language</option>
          </select>
        </label>

        <label className="block mb-3">
          <span className="text-[11px] text-[var(--nx-text-3)] uppercase tracking-wide">Tags (comma-separated)</span>
          <input value={tags} onChange={(e) => setTags(e.target.value)} className={inputCls} />
        </label>

        <label className="block mb-3">
          <span className="text-[11px] text-[var(--nx-text-3)] uppercase tracking-wide">Notes</span>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} className={`${inputCls} resize-none`} />
        </label>

        <label className="flex items-center gap-2 mb-4 text-sm text-[var(--nx-text-2)]">
          <input type="checkbox" checked={shouldEnrich} onChange={(e) => setShouldEnrich(e.target.checked)} className="accent-blue-500" />
          Enrich with AI
        </label>

        {enrichingId ? (
          <div className="flex items-center gap-2 text-sm text-[var(--nx-text-2)]">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
            enriching with AI...
          </div>
        ) : (
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm text-[var(--nx-text-3)] hover:text-[var(--nx-text)] transition-colors">Cancel</button>
            <button type="submit" disabled={!name.trim() || addConcept.isPending}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg disabled:opacity-50 transition-colors">
              {addConcept.isPending ? "Adding..." : "Add"}
            </button>
          </div>
        )}
        {addConcept.isError && <p className="mt-2 text-sm text-red-400">{addConcept.error.message}</p>}
      </form>
    </div>
  );
}
