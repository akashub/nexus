import { useState } from "react";
import { useSaveAiConfig, useAiConfig } from "../hooks/useApiExtra";

const PROVIDERS: Record<string, { label: string; fields: string[] }> = {
  anthropic: { label: "Anthropic", fields: ["api_key", "model"] },
  openai: { label: "OpenAI", fields: ["api_key", "model"] },
  gemini: { label: "Gemini", fields: ["api_key", "model", "project", "location"] },
};

const DEFAULTS: Record<string, Record<string, string>> = {
  anthropic: { model: "claude-sonnet-4-6" },
  openai: { model: "gpt-4o-mini" },
  gemini: { model: "gemini-2.5-flash", location: "us-central1" },
};

const LABELS: Record<string, string> = {
  api_key: "API Key", model: "Model", project: "GCP Project (Vertex)", location: "Location",
};

interface Props { provider: string; onClose: () => void; onSaved: () => void; }

export default function AiConfigModal({ provider, onClose, onSaved }: Props) {
  const spec = PROVIDERS[provider];
  const { data: existing } = useAiConfig();
  const save = useSaveAiConfig();
  const defaults = DEFAULTS[provider] || {};
  const current = existing?.[provider] || {};

  const [values, setValues] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const f of spec.fields) {
      const val = current[f] || "";
      init[f] = f === "api_key" && val.includes("...") ? "" : val;
    }
    return init;
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    save.mutate({ provider, settings: values }, { onSuccess: onSaved });
  }

  const set = (k: string, v: string) => setValues((p) => ({ ...p, [k]: v }));
  const inputCls = "mt-1 w-full px-3 py-2 bg-[var(--nx-input)] border border-[var(--nx-border)] rounded-lg text-[var(--nx-text)] text-sm outline-none focus:border-[var(--nx-border-strong)] transition-colors";

  return (
    <div className="fixed inset-0 bg-[var(--nx-overlay)] flex items-center justify-center z-50" onClick={onClose}>
      <form onSubmit={handleSubmit} onClick={(e) => e.stopPropagation()}
        className="w-full max-w-sm bg-[var(--nx-surface)] border border-[var(--nx-border-strong)] rounded-xl shadow-2xl p-5">
        <h2 className="text-sm font-semibold text-[var(--nx-text)] mb-1">Configure {spec.label}</h2>
        <p className="text-[11px] text-[var(--nx-text-4)] mb-4">Credentials are stored locally at ~/.nexus/ai_config.json</p>

        {spec.fields.map((field) => (
          <label key={field} className="block mb-3">
            <span className="text-[11px] text-[var(--nx-text-3)] uppercase tracking-wide">{LABELS[field] || field}</span>
            <input type={field === "api_key" ? "password" : "text"}
              value={values[field] || ""} onChange={(e) => set(field, e.target.value)}
              placeholder={defaults[field] || ""} className={inputCls} />
          </label>
        ))}

        {provider === "gemini" && (
          <p className="text-[10px] text-[var(--nx-text-4)] mb-3">Use API key for standard access, or GCP Project for Vertex AI.</p>
        )}

        <div className="flex gap-2 justify-end">
          <button type="button" onClick={onClose}
            className="px-4 py-2 text-sm text-[var(--nx-text-3)] hover:text-[var(--nx-text)] transition-colors">Cancel</button>
          <button type="submit" disabled={!values.api_key && !values.project}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg disabled:opacity-50 transition-colors">
            {save.isPending ? "Saving..." : "Save"}
          </button>
        </div>
        {save.isError && <p className="mt-2 text-sm text-red-400">{save.error.message}</p>}
      </form>
    </div>
  );
}
