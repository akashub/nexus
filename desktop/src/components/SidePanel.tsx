import { useConcept, useEdges } from "../hooks/useApi";

const CATEGORY_COLORS: Record<string, string> = {
  devtool: "bg-purple-500/20 text-purple-300",
  framework: "bg-blue-500/20 text-blue-300",
  concept: "bg-emerald-500/20 text-emerald-300",
  pattern: "bg-orange-500/20 text-orange-300",
  language: "bg-red-500/20 text-red-300",
};

interface Props {
  conceptId: string;
  onClose: () => void;
  onNavigate: (id: string) => void;
}

export default function SidePanel({ conceptId, onClose, onNavigate }: Props) {
  const { data: concept } = useConcept(conceptId);
  const { data: edges } = useEdges(conceptId);

  if (!concept) return null;

  const catClass = concept.category
    ? CATEGORY_COLORS[concept.category] || "bg-gray-500/20 text-gray-300"
    : null;

  const outgoing = edges?.filter((e) => e.source_id === conceptId) || [];
  const incoming = edges?.filter((e) => e.target_id === conceptId) || [];

  return (
    <div className="w-80 bg-gray-900 border-l border-gray-800 p-4 overflow-y-auto">
      <div className="flex items-start justify-between mb-3">
        <h2 className="text-lg font-semibold text-white">{concept.name}</h2>
        <button onClick={onClose} className="text-gray-500 hover:text-gray-300 text-xl leading-none">
          &times;
        </button>
      </div>

      {catClass && (
        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium mb-3 ${catClass}`}>
          {concept.category}
        </span>
      )}

      {concept.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {concept.tags.map((tag) => (
            <span key={tag} className="px-1.5 py-0.5 bg-gray-800 text-gray-400 rounded text-xs">
              {tag}
            </span>
          ))}
        </div>
      )}

      {concept.description && (
        <div className="mb-4">
          <h3 className="text-xs font-medium text-gray-500 uppercase mb-1">Description</h3>
          <p className="text-sm text-gray-300 leading-relaxed">{concept.description}</p>
        </div>
      )}

      {concept.notes && (
        <div className="mb-4">
          <h3 className="text-xs font-medium text-gray-500 uppercase mb-1">Notes</h3>
          <p className="text-sm text-gray-400">{concept.notes}</p>
        </div>
      )}

      {outgoing.length > 0 && (
        <div className="mb-4">
          <h3 className="text-xs font-medium text-gray-500 uppercase mb-1">
            Outgoing ({outgoing.length})
          </h3>
          {outgoing.map((e) => (
            <button
              key={e.id}
              onClick={() => onNavigate(e.target_id)}
              className="block w-full text-left text-sm text-blue-400 hover:text-blue-300 py-0.5"
            >
              &rarr; {e.relationship} &rarr; {e.target_id.slice(0, 8)}
            </button>
          ))}
        </div>
      )}

      {incoming.length > 0 && (
        <div className="mb-4">
          <h3 className="text-xs font-medium text-gray-500 uppercase mb-1">
            Incoming ({incoming.length})
          </h3>
          {incoming.map((e) => (
            <button
              key={e.id}
              onClick={() => onNavigate(e.source_id)}
              className="block w-full text-left text-sm text-blue-400 hover:text-blue-300 py-0.5"
            >
              &larr; {e.source_id.slice(0, 8)} &rarr; {e.relationship}
            </button>
          ))}
        </div>
      )}

      <div className="text-xs text-gray-600 mt-4">
        Added {new Date(concept.created_at).toLocaleDateString()}
      </div>
    </div>
  );
}
