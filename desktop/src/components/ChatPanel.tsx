import { useState } from "react";
import { useAsk } from "../hooks/useApi";
import type { AskResponse } from "../types";

interface Props {
  onClose: () => void;
}

export default function ChatPanel({ onClose }: Props) {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<AskResponse[]>([]);
  const ask = useAsk();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || ask.isPending) return;
    ask.mutate(question.trim(), {
      onSuccess: (res) => {
        setHistory((h) => [...h, res]);
        setQuestion("");
      },
    });
  }

  return (
    <div className="w-96 bg-[#0a0a0b]/95 backdrop-blur-xl border-l border-white/[0.06] flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
        <h2 className="text-sm font-semibold text-gray-200">Ask</h2>
        <button onClick={onClose} className="text-gray-600 hover:text-gray-300 text-xl leading-none transition-colors">
          &times;
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {history.map((item, i) => (
          <div key={i} className="space-y-1">
            <p className="text-sm text-blue-400/80 font-medium">{item.question}</p>
            <p className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">{item.answer}</p>
          </div>
        ))}
        {ask.isPending && <p className="text-sm text-gray-600 animate-pulse">Thinking...</p>}
        {ask.isError && <p className="text-sm text-red-400/80">{ask.error.message}</p>}
      </div>

      <form onSubmit={handleSubmit} className="p-3 border-t border-white/[0.06]">
        <div className="flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question..."
            className="flex-1 px-3 py-2 bg-white/[0.04] border border-white/[0.06] rounded-lg text-gray-100 text-sm outline-none focus:border-blue-500/50 placeholder:text-gray-600 transition-colors"
          />
          <button
            type="submit"
            disabled={!question.trim() || ask.isPending}
            className="px-3 py-2 bg-blue-600/80 hover:bg-blue-600 border border-blue-500/30 text-blue-100 text-sm rounded-lg disabled:opacity-50 transition-colors"
          >
            Ask
          </button>
        </div>
      </form>
    </div>
  );
}
