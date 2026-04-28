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
    <div className="w-96 bg-gray-900 border-l border-gray-800 flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <h2 className="text-sm font-semibold text-white">Ask</h2>
        <button onClick={onClose} className="text-gray-500 hover:text-gray-300 text-xl leading-none">
          &times;
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {history.map((item, i) => (
          <div key={i}>
            <p className="text-sm text-blue-400 mb-1">{item.question}</p>
            <p className="text-sm text-gray-300 whitespace-pre-wrap">{item.answer}</p>
          </div>
        ))}
        {ask.isPending && <p className="text-sm text-gray-500">Thinking...</p>}
        {ask.isError && <p className="text-sm text-red-400">{ask.error.message}</p>}
      </div>

      <form onSubmit={handleSubmit} className="p-3 border-t border-gray-800">
        <div className="flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question..."
            className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white text-sm outline-none focus:border-blue-500"
          />
          <button
            type="submit"
            disabled={!question.trim() || ask.isPending}
            className="px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded disabled:opacity-50"
          >
            Ask
          </button>
        </div>
      </form>
    </div>
  );
}
