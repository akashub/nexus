import { openUrl } from "@tauri-apps/plugin-opener";

interface SectionData {
  title: string;
  source: string;
  text: string;
  codeBlocks: { lang: string; code: string }[];
}

function parseSection(raw: string): SectionData {
  const s: SectionData = { title: "", source: "", text: "", codeBlocks: [] };
  let inCode = false, lang = "", codeLines: string[] = [];
  const textLines: string[] = [];

  for (const line of raw.split("\n")) {
    if (line.startsWith("```") && !inCode) {
      inCode = true; lang = line.slice(3).trim(); codeLines = [];
    } else if (line.startsWith("```") && inCode) {
      inCode = false;
      if (codeLines.length) s.codeBlocks.push({ lang, code: codeLines.join("\n") });
    } else if (inCode) {
      codeLines.push(line);
    } else if (line.startsWith("### ")) {
      s.title = line.slice(4).trim();
    } else if (line.startsWith("Source:")) {
      s.source = line.slice(7).trim();
    } else if (line.trim()) {
      textLines.push(line.trim());
    }
  }
  s.text = textLines.join(" ");
  return s;
}

function Section({ data }: { data: SectionData }) {
  return (
    <div className="border border-[var(--nx-border)] rounded-lg p-2.5">
      {data.title && <h4 className="text-xs text-[var(--nx-text)] font-medium mb-1">{data.title}</h4>}
      {data.text && <p className="text-[11px] text-[var(--nx-text-3)] mb-2 leading-relaxed">{data.text}</p>}
      {data.codeBlocks.map((block, i) => (
        <div key={i} className="relative group mb-1.5 last:mb-0">
          <pre className="bg-[var(--nx-input)] border border-[var(--nx-border)] rounded px-2.5 py-2 text-[11px] text-[var(--nx-text-2)] leading-relaxed overflow-x-auto whitespace-pre-wrap font-mono">
            {block.code}</pre>
          <button onClick={() => navigator.clipboard.writeText(block.code)}
            className="absolute top-1 right-1 px-1.5 py-0.5 text-[10px] text-[var(--nx-text-4)] hover:text-[var(--nx-text)] bg-[var(--nx-hover)] rounded opacity-0 group-hover:opacity-100 transition-opacity">
            copy</button>
        </div>
      ))}
      {data.source && (
        <button onClick={() => openUrl(data.source)}
          className="block text-[10px] text-[var(--nx-text-4)] hover:text-[var(--nx-text-3)] mt-1.5 truncate text-left cursor-pointer">{data.source}</button>
      )}
    </div>
  );
}

export default function QuickstartContent({ text }: { text: string }) {
  const sections = text.split(/\n-{3,}\n/).map(parseSection).filter(s => s.title || s.text || s.codeBlocks.length);
  if (!sections.length) {
    return (
      <pre className="bg-[var(--nx-input)] border border-[var(--nx-border)] rounded px-2.5 py-2 text-[11px] text-[var(--nx-text-2)] leading-relaxed overflow-x-auto whitespace-pre-wrap font-mono">
        {text}</pre>
    );
  }
  return (
    <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
      {sections.map((s, i) => <Section key={i} data={s} />)}
    </div>
  );
}
