import { useCallback, useEffect, useState } from "react";
import { API } from "../hooks/useApi";

interface Props { projectId: string; projectName: string; onClose: () => void; }
interface ListItem { id: string; name: string; category: string | null; }

type Tab = "complete" | "context";

export default function ReplicateModal({ projectId, projectName, onClose }: Props) {
  const [tab, setTab] = useState<Tab>("complete");
  const [items, setItems] = useState<ListItem[]>([]);
  const [excluded, setExcluded] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState("");
  const [script, setScript] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const fetchList = useCallback(async (context?: string) => {
    setLoading(true);
    setScript("");
    try {
      const params = new URLSearchParams({ mode: "list" });
      if (context) params.set("context", context);
      const res = await fetch(`${API}/projects/${projectId}/replicate?${params}`);
      if (!res.ok) throw new Error("fetch failed");
      const data: ListItem[] = await res.json();
      setItems(data);
      setExcluded(new Set());
    } catch { setItems([]); }
    setLoading(false);
  }, [projectId]);

  const generate = async () => {
    setLoading(true);
    try {
      const body: Record<string, unknown> = { mode: tab };
      if (tab === "context" && query) body.context = query;
      if (excluded.size > 0) body.exclude_ids = [...excluded];
      const res = await fetch(`${API}/projects/${projectId}/replicate`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("generate failed");
      const data = await res.json();
      setScript(typeof data === "string" ? data : data.script ?? JSON.stringify(data, null, 2));
    } catch { setScript("# error generating script"); }
    setLoading(false);
  };

  const toggleExclude = (id: string) => {
    setExcluded((prev) => { const s = new Set(prev); if (s.has(id)) s.delete(id); else s.add(id); return s; });
  };

  const copyScript = () => {
    navigator.clipboard.writeText(script);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const switchTab = (t: Tab) => {
    setTab(t);
    setItems([]);
    setScript("");
    setExcluded(new Set());
    if (t === "complete") fetchList();
  };

  useEffect(() => { fetchList(); }, [fetchList]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="w-[520px] max-h-[80vh] bg-[var(--nx-surface)] border border-[var(--nx-border-strong)] rounded-lg flex flex-col overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--nx-border)]">
          <h2 className="text-sm font-medium text-[var(--nx-text)]">replicate: {projectName}</h2>
          <button onClick={onClose} className="text-[var(--nx-text-4)] hover:text-[var(--nx-text)] text-lg leading-none">&times;</button>
        </div>

        <div className="flex border-b border-[var(--nx-border)]">
          {(["complete", "context"] as Tab[]).map((t) => (
            <button key={t} onClick={() => switchTab(t)}
              className={`flex-1 px-3 py-2 text-xs transition-colors ${tab === t ? "text-[var(--nx-text)] border-b-2 border-[var(--nx-accent)]" : "text-[var(--nx-text-4)] hover:text-[var(--nx-text-3)]"}`}>
              {t}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {tab === "context" && (
            <div className="flex gap-2 mb-3">
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="describe what you need..."
                className="flex-1 px-2 py-1.5 text-xs text-[var(--nx-text-2)] bg-[var(--nx-input)] border border-[var(--nx-border)] rounded outline-none focus:border-[var(--nx-border-strong)]"
                onKeyDown={(e) => { if (e.key === "Enter" && query) fetchList(query); }} />
              <button onClick={() => query && fetchList(query)} disabled={!query || loading}
                className="px-3 py-1.5 text-xs text-[var(--nx-text-2)] border border-[var(--nx-border-strong)] rounded hover:bg-[var(--nx-hover)] disabled:opacity-50 transition-colors">
                search
              </button>
            </div>
          )}

          {loading && <p className="text-xs text-[var(--nx-text-3)] animate-pulse">loading...</p>}

          {items.length > 0 && (
            <div className="flex flex-col gap-0.5 mb-3">
              {items.map((item) => (
                <label key={item.id} className="flex items-center gap-2 px-2 py-1 rounded hover:bg-[var(--nx-hover)] cursor-pointer">
                  <input type="checkbox" checked={!excluded.has(item.id)} onChange={() => toggleExclude(item.id)}
                    className="accent-[var(--nx-accent)]" />
                  <span className="text-xs text-[var(--nx-text-2)] flex-1">{item.name}</span>
                  {item.category && <span className="text-[11px] text-[var(--nx-text-4)]">{item.category}</span>}
                </label>
              ))}
            </div>
          )}

          {script && (
            <div className="relative">
              <button onClick={copyScript}
                className="absolute top-2 right-2 px-2 py-0.5 text-[10px] text-[var(--nx-text-4)] border border-[var(--nx-border)] rounded hover:bg-[var(--nx-hover)] transition-colors">
                {copied ? "copied" : "copy"}
              </button>
              <pre className="text-xs text-[var(--nx-text-2)] bg-[var(--nx-input)] border border-[var(--nx-border)] rounded p-3 overflow-x-auto whitespace-pre-wrap">{script}</pre>
            </div>
          )}
        </div>

        <div className="px-4 py-3 border-t border-[var(--nx-border)]">
          <button onClick={generate} disabled={loading || items.length === 0}
            className="w-full px-3 py-1.5 text-xs text-[var(--nx-text-2)] border border-[var(--nx-border-strong)] rounded hover:bg-[var(--nx-hover)] disabled:opacity-50 transition-colors">
            {loading ? "generating..." : "generate script"}
          </button>
        </div>
      </div>
    </div>
  );
}
