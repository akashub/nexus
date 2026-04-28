import { useState } from "react";
import { useAddConcept } from "../hooks/useApi";

interface Props {
  onClose: () => void;
}

export default function AddModal({ onClose }: Props) {
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [tags, setTags] = useState("");
  const [notes, setNotes] = useState("");
  const [enrich, setEnrich] = useState(true);
  const addConcept = useAddConcept();

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
      { onSuccess: onClose },
    );
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md bg-gray-900 border border-gray-700 rounded-lg shadow-2xl p-6"
      >
        <h2 className="text-lg font-semibold text-white mb-4">Add Concept</h2>

        <label className="block mb-3">
          <span className="text-xs text-gray-400 uppercase">Name</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white text-sm outline-none focus:border-blue-500"
            autoFocus
          />
        </label>

        <label className="block mb-3">
          <span className="text-xs text-gray-400 uppercase">Category</span>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="mt-1 w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white text-sm outline-none"
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
          <span className="text-xs text-gray-400 uppercase">Tags (comma-separated)</span>
          <input
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            className="mt-1 w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white text-sm outline-none"
          />
        </label>

        <label className="block mb-3">
          <span className="text-xs text-gray-400 uppercase">Notes</span>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            className="mt-1 w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white text-sm outline-none resize-none"
          />
        </label>

        <label className="flex items-center gap-2 mb-4 text-sm text-gray-300">
          <input
            type="checkbox"
            checked={enrich}
            onChange={(e) => setEnrich(e.target.checked)}
            className="accent-blue-500"
          />
          Enrich with AI
        </label>

        <div className="flex gap-2 justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-400 hover:text-white"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!name.trim() || addConcept.isPending}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded disabled:opacity-50"
          >
            {addConcept.isPending ? "Adding..." : "Add"}
          </button>
        </div>

        {addConcept.isError && (
          <p className="mt-2 text-sm text-red-400">{addConcept.error.message}</p>
        )}
      </form>
    </div>
  );
}
