import { useEffect, useRef, useState } from "react";
import { useAddProject } from "../hooks/useApi";

interface Props { onClose: () => void; onCreated?: (id: string) => void; }

export default function AddProjectModal({ onClose, onCreated }: Props) {
  const [name, setName] = useState("");
  const [path, setPath] = useState("");
  const [description, setDescription] = useState("");
  const addProject = useAddProject();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    addProject.mutate(
      { name: name.trim(), path: path.trim() || undefined, description: description.trim() || undefined },
      { onSuccess: (data) => { onCreated?.(data.id); onClose(); } },
    );
  }

  const inputCls = "mt-1 w-full px-3 py-2 bg-[var(--nx-input)] border border-[var(--nx-border)] rounded-lg text-[var(--nx-text)] text-sm outline-none focus:border-[var(--nx-accent)] transition-colors";

  return (
    <div className="fixed inset-0 bg-[var(--nx-overlay)] flex items-center justify-center z-50" onClick={onClose}>
      <form onSubmit={handleSubmit} onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md bg-[var(--nx-surface)] border border-[var(--nx-border-strong)] rounded-xl shadow-2xl p-6">
        <h2 className="text-lg font-semibold text-[var(--nx-text)] mb-4">Add Project</h2>

        <label className="block mb-3">
          <span className="text-[11px] text-[var(--nx-text-3)] uppercase tracking-wide">Name</span>
          <input ref={inputRef} value={name} onChange={(e) => setName(e.target.value)}
            placeholder="my-project" className={inputCls} />
        </label>

        <label className="block mb-3">
          <span className="text-[11px] text-[var(--nx-text-3)] uppercase tracking-wide">Path (optional)</span>
          <input value={path} onChange={(e) => setPath(e.target.value)}
            placeholder="/Users/you/projects/my-project" className={inputCls} />
          <p className="text-[10px] text-[var(--nx-text-4)] mt-1">local folder path — enables scanning</p>
        </label>

        <label className="block mb-4">
          <span className="text-[11px] text-[var(--nx-text-3)] uppercase tracking-wide">Description (optional)</span>
          <input value={description} onChange={(e) => setDescription(e.target.value)}
            placeholder="what this project is about" className={inputCls} />
        </label>

        <div className="flex gap-2 justify-end">
          <button type="button" onClick={onClose}
            className="px-4 py-2 text-sm text-[var(--nx-text-3)] hover:text-[var(--nx-text)] transition-colors">Cancel</button>
          <button type="submit" disabled={!name.trim() || addProject.isPending}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg disabled:opacity-50 transition-colors">
            {addProject.isPending ? "Adding..." : "Add"}
          </button>
        </div>
        {addProject.isError && <p className="mt-2 text-sm text-red-400">{addProject.error.message}</p>}

        <div className="mt-4 pt-3 border-t border-[var(--nx-border)]">
          <p className="text-[10px] text-[var(--nx-text-4)] mb-1.5">or add via CLI:</p>
          <pre className="bg-[var(--nx-input)] border border-[var(--nx-border)] rounded px-2.5 py-1.5 text-[11px] text-[var(--nx-text-2)] font-mono overflow-x-auto">
            nexus project add "my-project" --path /path/to/project</pre>
        </div>
      </form>
    </div>
  );
}
