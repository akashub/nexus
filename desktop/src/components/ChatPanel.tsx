import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { API, useConversations } from "../hooks/useApi";

interface ChatEntry { key: number; question: string; answer: string; streaming?: boolean; }
interface Props { onClose: () => void; }

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
    setQuestion(""); setStreaming(true);
    const k = ++keyRef.current;
    setHistory((h) => [...h, { key: k, question: q, answer: "", streaming: true }]);
    const abort = new AbortController();
    abortRef.current = abort;
    const update = (fn: (e: ChatEntry) => ChatEntry) =>
      setHistory((h) => h.map((e) => (e.key === k ? fn(e) : e)));
    try {
      const res = await fetch(`${API}/ask`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }), signal: abort.signal,
      });
      if (!res.ok || !res.body) throw new Error("Stream failed");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      while (!done) {
        const { value, done: d } = await reader.read();
        done = d;
        if (value) {
          update((e) => ({ ...e, answer: e.answer + decoder.decode(value, { stream: true }) }));
          scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
        }
      }
      const tail = decoder.decode();
      if (tail) update((e) => ({ ...e, answer: e.answer + tail }));
      update((e) => ({ ...e, streaming: false }));
      qc.invalidateQueries({ queryKey: ["conversations"] });
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      update((e) => ({ ...e, answer: e.answer || "Failed to get response.", streaming: false }));
    } finally { setStreaming(false); }
  }

  return (
    <div className="w-96 bg-[var(--nx-surface)] border-l border-[var(--nx-border-strong)] flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--nx-border)]">
        <h2 className="text-sm font-semibold text-[var(--nx-text)]">Ask</h2>
        <button onClick={onClose} className="text-[var(--nx-text-4)] hover:text-[var(--nx-text)] text-xl leading-none">&times;</button>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {history.map((item) => (
          <div key={item.key} className="space-y-1">
            <p className="text-sm text-[var(--nx-accent)] font-medium">{item.question}</p>
            <p className="text-sm text-[var(--nx-text-2)] whitespace-pre-wrap leading-relaxed">
              {item.answer}
              {item.streaming && <span className="inline-block w-1.5 h-3.5 bg-[var(--nx-text-3)] ml-0.5 animate-pulse" />}
            </p>
          </div>
        ))}
        {history.length === 0 && (
          <p className="text-xs text-[var(--nx-text-4)] text-center mt-8">ask a question about your knowledge graph</p>
        )}
      </div>
      <form onSubmit={handleSubmit} className="p-3 border-t border-[var(--nx-border)]">
        <div className="flex gap-2">
          <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask a question..."
            className="flex-1 px-3 py-2 bg-[var(--nx-input)] border border-[var(--nx-border)] rounded-lg text-[var(--nx-text)] text-sm outline-none focus:border-[var(--nx-accent)] placeholder:text-[var(--nx-text-4)]" />
          <button type="submit" disabled={!question.trim() || streaming}
            className="px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg disabled:opacity-50">Ask</button>
        </div>
      </form>
    </div>
  );
}
