import { useCallback, useEffect, useState } from "react";
import AddModal from "./components/AddModal";
import ChatPanel from "./components/ChatPanel";
import GraphView from "./components/GraphView";
import Logo from "./components/Logo";
import SearchBar from "./components/SearchBar";
import SidePanel from "./components/SidePanel";
import { useGraph, useStats } from "./hooks/useApi";
import { useBackend } from "./hooks/useBackend";

const CATEGORIES = [
  { key: "devtool", color: "#a78bfa", label: "Devtool" },
  { key: "framework", color: "#60a5fa", label: "Framework" },
  { key: "concept", color: "#34d399", label: "Concept" },
  { key: "pattern", color: "#fb923c", label: "Pattern" },
  { key: "language", color: "#f87171", label: "Language" },
];

export default function App() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showSearch, setShowSearch] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const backendStatus = useBackend();
  const { data: graph } = useGraph();
  const { data: stats } = useStats();

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.metaKey && e.key === "k") {
        e.preventDefault();
        setShowSearch(true);
      } else if (e.metaKey && e.key === "n") {
        e.preventDefault();
        setShowAdd(true);
      } else if (e.key === "Escape") {
        setShowSearch(false);
        setShowAdd(false);
      }
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  const handleSelectNode = useCallback((id: string | null) => {
    setSelectedId(id);
  }, []);

  return (
    <div className="flex h-screen bg-[#0a0a0b] text-gray-100">
      <div className="flex-1 flex flex-col">
        <header className="flex items-center justify-between px-4 py-2 border-b border-white/[0.06] bg-[#0a0a0b]/90 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <Logo size={22} />
            <h1 className="text-sm font-semibold tracking-wider text-gray-200">NEXUS</h1>
            {stats && (
              <span className="text-[11px] text-gray-600">
                {stats.concept_count} concepts &middot; {stats.edge_count} edges
              </span>
            )}
          </div>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setShowSearch(true)}
              className="px-2.5 py-1 text-[11px] text-gray-500 bg-white/[0.04] border border-white/[0.06] rounded-md hover:bg-white/[0.08] hover:text-gray-300 transition-colors"
            >
              Search
              <kbd className="ml-1.5 text-gray-700">&#8984;K</kbd>
            </button>
            <button
              onClick={() => setShowAdd(true)}
              className="px-2.5 py-1 text-[11px] text-blue-200 bg-blue-600/80 border border-blue-500/30 rounded-md hover:bg-blue-600 transition-colors"
            >
              Add
              <kbd className="ml-1.5 text-blue-400/60">&#8984;N</kbd>
            </button>
            <button
              onClick={() => setShowChat((v) => !v)}
              className={`px-2.5 py-1 text-[11px] rounded-md border transition-colors ${
                showChat
                  ? "text-gray-200 bg-white/[0.08] border-white/[0.1]"
                  : "text-gray-500 bg-white/[0.04] border-white/[0.06] hover:bg-white/[0.08] hover:text-gray-300"
              }`}
            >
              Chat
            </button>
          </div>
        </header>

        <main className="flex-1 relative">
          {backendStatus === "connecting" ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <Logo size={48} />
                <p className="text-gray-500 text-sm mt-4">Connecting to backend...</p>
                <p className="text-gray-700 text-xs mt-1">
                  Run <code className="text-gray-600 bg-white/[0.04] px-1.5 py-0.5 rounded">nexus serve</code> if not started
                </p>
              </div>
            </div>
          ) : (
            <GraphView data={graph} onSelectNode={handleSelectNode} selectedId={selectedId} />
          )}

          {stats && stats.concept_count > 0 && (
            <div className="absolute bottom-4 left-4 flex items-center gap-3 px-3 py-1.5 bg-[#0a0a0b]/80 backdrop-blur-md border border-white/[0.06] rounded-lg">
              {CATEGORIES.map((cat) => (
                <div key={cat.key} className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: cat.color }} />
                  <span className="text-[10px] text-gray-600">{cat.label}</span>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>

      {selectedId && (
        <SidePanel
          conceptId={selectedId}
          onClose={() => setSelectedId(null)}
          onNavigate={setSelectedId}
        />
      )}

      {showChat && <ChatPanel onClose={() => setShowChat(false)} />}
      {showSearch && (
        <SearchBar onSelect={setSelectedId} onClose={() => setShowSearch(false)} />
      )}
      {showAdd && <AddModal onClose={() => setShowAdd(false)} />}
    </div>
  );
}
