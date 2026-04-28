import { useCallback, useEffect, useState } from "react";
import AddModal from "./components/AddModal";
import ChatPanel from "./components/ChatPanel";
import GraphView from "./components/GraphView";
import SearchBar from "./components/SearchBar";
import SidePanel from "./components/SidePanel";
import { useGraph, useStats } from "./hooks/useApi";
import { useBackend } from "./hooks/useBackend";

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
    <div className="flex h-screen bg-gray-950 text-gray-100">
      <div className="flex-1 flex flex-col">
        <header className="flex items-center justify-between px-4 py-2 border-b border-gray-800 bg-gray-900/80">
          <div className="flex items-center gap-3">
            <h1 className="text-sm font-bold tracking-wide">NEXUS</h1>
            {stats && (
              <span className="text-xs text-gray-500">
                {stats.concept_count} concepts &middot; {stats.edge_count} edges
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowSearch(true)}
              className="px-3 py-1 text-xs text-gray-400 bg-gray-800 border border-gray-700 rounded hover:bg-gray-700"
            >
              Search
              <kbd className="ml-2 text-gray-600">&#8984;K</kbd>
            </button>
            <button
              onClick={() => setShowAdd(true)}
              className="px-3 py-1 text-xs text-white bg-blue-600 rounded hover:bg-blue-500"
            >
              Add
              <kbd className="ml-2 text-blue-300">&#8984;N</kbd>
            </button>
            <button
              onClick={() => setShowChat((v) => !v)}
              className={`px-3 py-1 text-xs rounded border ${
                showChat
                  ? "text-white bg-gray-700 border-gray-600"
                  : "text-gray-400 bg-gray-800 border-gray-700 hover:bg-gray-700"
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
                <p className="text-gray-400 text-sm">Connecting to backend...</p>
                <p className="text-gray-600 text-xs mt-1">
                  Run <code className="text-gray-500">nexus serve</code> if not started
                </p>
              </div>
            </div>
          ) : (
            <GraphView data={graph} onSelectNode={handleSelectNode} />
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
