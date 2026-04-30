import { useEffect, useState } from "react";
import AddModal from "./components/AddModal";
import ChatPanel from "./components/ChatPanel";
import GlobalGraphView from "./components/GlobalGraphView";
import GraphView, { CATEGORY_COLORS } from "./components/GraphView";
import LeftSidebar from "./components/LeftSidebar";
import Logo from "./components/Logo";
import SearchBar from "./components/SearchBar";
import SidePanel from "./components/SidePanel";
import { useGlobalGraph, useGraph, useOllamaStatus, useStats } from "./hooks/useApi";
import { useBackend } from "./hooks/useBackend";
import type { Project } from "./types";

export default function App() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showSearch, setShowSearch] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const backendStatus = useBackend();
  const { data: graph } = useGraph(activeProject?.id);
  const { data: globalGraph } = useGlobalGraph();
  const { data: stats } = useStats();
  const { data: aiStatus } = useOllamaStatus();

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.metaKey && e.key === "k") { e.preventDefault(); setShowSearch(true); }
      else if (e.metaKey && e.key === "n") { e.preventDefault(); setShowAdd(true); }
      else if (e.metaKey && e.key === "/") { e.preventDefault(); setShowChat((v) => !v); }
      else if (e.key === "Escape") { setShowSearch(false); setShowAdd(false); }
    }
    const onAdd = () => setShowAdd(true);
    const onChat = () => setShowChat((v) => !v);
    const onEdit = (e: Event) => setSelectedId((e as CustomEvent).detail);
    window.addEventListener("keydown", handleKey);
    window.addEventListener("nexus:add", onAdd);
    window.addEventListener("nexus:chat", onChat);
    window.addEventListener("nexus:edit", onEdit);
    return () => {
      window.removeEventListener("keydown", handleKey);
      window.removeEventListener("nexus:add", onAdd);
      window.removeEventListener("nexus:chat", onChat);
      window.removeEventListener("nexus:edit", onEdit);
    };
  }, []);

  if (backendStatus === "connecting") {
    return (
      <div className="flex items-center justify-center h-screen bg-[#0a0a0b] text-gray-100">
        <div className="text-center">
          <Logo size={48} />
          <p className="text-gray-500 text-sm mt-4">connecting to backend...</p>
          <p className="text-gray-700 text-xs mt-1">
            run <code className="text-gray-500 bg-white/[0.04] px-1.5 py-0.5 rounded">nexus serve</code> if not started
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-[#0a0a0b] text-gray-100">
      <header className="flex items-center justify-between px-4 h-10 border-b border-white/[0.06] shrink-0">
        <div className="flex items-center gap-2">
          <Logo size={18} />
          <button onClick={() => { setActiveProject(null); setSelectedId(null); }} className="text-xs tracking-[0.2em] text-gray-400 uppercase hover:text-gray-200 transition-colors">
            nexus
          </button>
          {activeProject && (
            <>
              <span className="text-xs text-gray-700">/</span>
              <span className="text-xs text-gray-300">{activeProject.name}</span>
            </>
          )}
        </div>
        <div className="flex items-center gap-3 text-[11px] text-gray-600">
          <div className="flex items-center gap-1.5">
            <div className={`w-1.5 h-1.5 rounded-full ${aiStatus?.available ? "bg-emerald-500" : "bg-gray-600"}`} />
            <span>ollama</span>
          </div>
          {stats && <span>{stats.concept_count} nodes &middot; {stats.edge_count} edges</span>}
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {activeProject && (
          <LeftSidebar
            onSelectNode={setSelectedId}
            selectedId={selectedId}
            categoryFilter={categoryFilter}
            onCategoryFilter={setCategoryFilter}
          />
        )}

        <div className="flex-1 min-w-0 flex flex-col">
          <div className="flex items-center gap-2 px-3 py-1.5 border-b border-white/[0.06] shrink-0">
            <input
              readOnly
              onClick={() => setShowSearch(true)}
              placeholder="search..."
              className="w-36 px-2 py-1 text-[11px] text-gray-600 bg-white/[0.03] border border-white/[0.06] rounded cursor-pointer hover:bg-white/[0.06] transition-colors"
            />
            <span className="text-[10px] text-gray-700 ml-0.5">⌘K</span>
            <Shortcut label="add" keys="⌘N" onClick={() => setShowAdd(true)} />
            <Shortcut label="ask" keys="⌘/" onClick={() => setShowChat((v) => !v)} />
            <div className="flex-1" />
            {activeProject && <Shortcut label="fit" onClick={() => window.dispatchEvent(new CustomEvent("nexus:fit"))} />}
          </div>

          <main className="flex-1 relative">
            {activeProject ? (
              <GraphView data={graph} onSelectNode={setSelectedId} selectedId={selectedId} categoryFilter={categoryFilter} />
            ) : (
              <GlobalGraphView data={globalGraph} onSelectProject={(id) => {
                const proj = globalGraph?.nodes.find((n) => n.id === id);
                if (proj) setActiveProject(proj);
              }} />
            )}
          </main>

          {activeProject && (
            <div className="flex items-center px-3 py-1 border-t border-white/[0.06] shrink-0 text-[10px] text-gray-700">
              <div className="flex-1" />
              <div className="flex items-center gap-3">
                {Object.entries(CATEGORY_COLORS).map(([cat, color]) => (
                  <div key={cat} className="flex items-center gap-1">
                    <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
                    <span>{cat}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {selectedId && activeProject && (
          <SidePanel conceptId={selectedId} onClose={() => setSelectedId(null)} onNavigate={setSelectedId} />
        )}
        {showChat && !selectedId && <ChatPanel onClose={() => setShowChat(false)} />}
      </div>

      {showSearch && <SearchBar onSelect={setSelectedId} onClose={() => setShowSearch(false)} />}
      {showAdd && <AddModal onClose={() => setShowAdd(false)} />}
    </div>
  );
}

function Shortcut({ label, keys, onClick }: { label: string; keys?: string; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      className="px-2 py-0.5 text-[10px] text-gray-600 border border-white/[0.08] rounded hover:bg-white/[0.06] hover:text-gray-400 transition-colors"
    >
      {keys && <span className="mr-1 text-gray-700">{keys}</span>}
      {label}
    </button>
  );
}
