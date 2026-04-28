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

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    setSelectedIdx(0);
  }, [results]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") {
      onClose();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIdx((i) => Math.min(i + 1, (results?.length || 1) - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && results && results[selectedIdx]) {
      onSelect(results[selectedIdx].id);
      onClose();
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-start justify-center pt-24 z-50">
      <div className="w-full max-w-lg bg-[#0a0a0b]/95 backdrop-blur-xl border border-white/[0.08] rounded-xl shadow-2xl shadow-black/50 overflow-hidden">
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Search concepts..."
          className="w-full px-4 py-3 bg-transparent text-gray-100 text-lg outline-none border-b border-white/[0.06] placeholder:text-gray-600"
        />
        {results && results.length > 0 && (
          <ul className="max-h-64 overflow-y-auto">
            {results.map((c, i) => (
              <li key={c.id}>
                <button
                  onClick={() => {
                    onSelect(c.id);
                    onClose();
                  }}
                  className={`w-full text-left px-4 py-2.5 flex items-center gap-2 transition-colors ${
                    i === selectedIdx ? "bg-white/[0.06]" : "hover:bg-white/[0.04]"
                  }`}
                >
                  <span className="text-gray-200 text-sm">{c.name}</span>
                  {c.category && (
                    <span className="text-[11px] text-gray-600">{c.category}</span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
        {query && results && results.length === 0 && (
          <p className="px-4 py-3 text-sm text-gray-600">No results</p>
        )}
      </div>
    </div>
  );
}
