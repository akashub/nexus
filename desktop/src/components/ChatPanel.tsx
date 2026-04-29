import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { API, useConversations } from "../hooks/useApi";

interface ChatEntry {
  key: number;
  question: string;
  answer: string;
  streaming?: boolean;
}

interface Props {
  onClose: () => void;
}

export default function ChatPanel({ onClose }: Props) {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<ChatEntry[]>([]);
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const loadedRef = useRef(false);
  const keyRef = useRef(0);
  const qc = useQueryClient();
  const { data: pastConvos } = useConversations();

  useEffect(() => {
    if (pastConvos && !loadedRef.current) {
      loadedRef.current = true;
      const past = [...pastConvos].reverse().map((c) => ({ key: ++keyRef.current, question: c.question, answer: c.answer }));
      setHistory((h) => [...past, ...h]);
    }
  }, [pastConvos]);

  useEffect(() => () => { abortRef.current?.abort(); }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || streaming) return;
    setQuestion("");
    setStreaming(true);
    const k = ++keyRef.current;
    setHistory((h) => [...h, { key: k, question: q, answer: "", streaming: true }]);
    const abort = new AbortController();
    abortRef.current = abort;
    const update = (fn: (e: ChatEntry) => ChatEntry) =>
      setHistory((h) => h.map((e) => (e.key === k ? fn(e) : e)));

    try {
      const res = await fetch(`${API}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
        signal: abort.signal,
      });
      if (!res.ok || !res.body) throw new Error("Stream failed");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      while (!done) {
        const { value, done: d } = await reader.read();
        done = d;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          update((e) => ({ ...e, answer: e.answer + chunk }));
          scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
        }
      }
      update((e) => ({ ...e, streaming: false }));
      qc.invalidateQueries({ queryKey: ["conversations"] });
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      update((e) => ({ ...e, answer: e.answer || "Failed to get response.", streaming: false }));
    } finally {
      setStreaming(false);
    }
  }

  return (
    <div className="w-96 bg-[#111113] border-l border-white/[0.08] flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
        <h2 className="text-sm font-semibold text-gray-200">Ask</h2>
        <button onClick={onClose} className="text-gray-600 hover:text-gray-300 text-xl leading-none">&times;</button>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {history.map((item) => (
          <div key={item.key} className="space-y-1">
            <p className="text-sm text-blue-400/80 font-medium">{item.question}</p>
            <p className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">
              {item.answer}
              {item.streaming && <span className="inline-block w-1.5 h-3.5 bg-gray-400 ml-0.5 animate-pulse" />}
            </p>
          </div>
        ))}
        {history.length === 0 && (
          <p className="text-[11px] text-gray-700 text-center mt-8">ask a question about your knowledge graph</p>
        )}
      </div>

      <form onSubmit={handleSubmit} className="p-3 border-t border-white/[0.06]">
        <div className="flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question..."
            className="flex-1 px-3 py-2 bg-white/[0.04] border border-white/[0.06] rounded-lg text-gray-100 text-sm outline-none focus:border-blue-500/50 placeholder:text-gray-600"
          />
          <button
            type="submit"
            disabled={!question.trim() || streaming}
            className="px-3 py-2 bg-blue-600/80 hover:bg-blue-600 border border-blue-500/30 text-blue-100 text-sm rounded-lg disabled:opacity-50"
          >
            Ask
          </button>
        </div>
      </form>
    </div>
  );
}
