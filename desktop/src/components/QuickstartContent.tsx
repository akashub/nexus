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
    <div className="border border-white/[0.06] rounded-lg p-2.5">
      {data.title && <h4 className="text-[11px] text-gray-300 font-medium mb-1">{data.title}</h4>}
      {data.text && <p className="text-[10px] text-gray-500 mb-2 leading-relaxed">{data.text}</p>}
      {data.codeBlocks.map((block, i) => (
        <div key={i} className="relative group mb-1.5 last:mb-0">
          <pre className="bg-white/[0.03] border border-white/[0.06] rounded px-2.5 py-2 text-[10px] text-gray-400 leading-relaxed overflow-x-auto whitespace-pre-wrap font-mono">
            {block.code}</pre>
          <button onClick={() => navigator.clipboard.writeText(block.code)}
            className="absolute top-1 right-1 px-1.5 py-0.5 text-[9px] text-gray-600 hover:text-gray-300 bg-white/[0.06] rounded opacity-0 group-hover:opacity-100 transition-opacity">
            copy</button>
        </div>
      ))}
      {data.source && (
        <a href={data.source} target="_blank" rel="noopener noreferrer"
          className="block text-[9px] text-gray-700 hover:text-gray-500 mt-1.5 truncate">{data.source}</a>
      )}
    </div>
  );
}

export default function QuickstartContent({ text }: { text: string }) {
  const sections = text.split(/\n-{3,}\n/).map(parseSection).filter(s => s.title || s.codeBlocks.length);
  return (
    <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
      {sections.map((s, i) => <Section key={i} data={s} />)}
    </div>
  );
}
