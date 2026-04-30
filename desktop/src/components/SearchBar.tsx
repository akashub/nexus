import { useEffect, useRef, useState } from "react";
import { useSearch } from "../hooks/useApi";

interface Props {
  onSelect: (id: string) => void;
  onClose: () => void;
}

export default function SearchBar({ onSelect, onClose }: Props) {
  const [query, setQuery] = useState("");
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const { data: results } = useSearch(query);

  useEffect(() => { inputRef.current?.focus(); }, []);
  useEffect(() => { setSelectedIdx(0); }, [results]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") { onClose(); }
    else if (e.key === "ArrowDown") { e.preventDefault(); setSelectedIdx((i) => Math.min(i + 1, (results?.length || 1) - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setSelectedIdx((i) => Math.max(i - 1, 0)); }
    else if (e.key === "Enter" && results && results[selectedIdx]) { onSelect(results[selectedIdx].id); onClose(); }
  }

  return (
    <div className="fixed inset-0 bg-[var(--nx-overlay)] flex items-start justify-center pt-24 z-50" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="w-full max-w-lg bg-[var(--nx-surface)] border border-[var(--nx-border-strong)] rounded-xl shadow-2xl overflow-hidden">
        <input ref={inputRef} value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={handleKeyDown}
          placeholder="Search concepts..."
          className="w-full px-4 py-3 bg-transparent text-[var(--nx-text)] text-lg outline-none border-b border-[var(--nx-border)] placeholder:text-[var(--nx-text-4)]" />
        {results && results.length > 0 && (
          <ul className="max-h-64 overflow-y-auto">
            {results.map((c, i) => (
              <li key={c.id}>
                <button onClick={() => { onSelect(c.id); onClose(); }}
                  className={`w-full text-left px-4 py-2.5 flex items-center gap-2 transition-colors ${
                    i === selectedIdx ? "bg-[var(--nx-hover)]" : "hover:bg-[var(--nx-hover)]"
                  }`}>
                  <span className="text-[var(--nx-text)] text-sm">{c.name}</span>
                  {c.category && <span className="text-xs text-[var(--nx-text-3)]">{c.category}</span>}
                </button>
              </li>
            ))}
          </ul>
        )}
        {query && results && results.length === 0 && (
          <p className="px-4 py-3 text-sm text-[var(--nx-text-3)]">No results</p>
        )}
      </div>
    </div>
  );
}
