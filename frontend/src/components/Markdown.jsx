// Small markdown renderer for agent answers: paragraphs, "> " quotes, "- " lists, **bold** and *italic*.
function Inline({ text }) {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*\s][^*]*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) return <b key={i}>{part.slice(2, -2)}</b>;
    if (part.length > 2 && part.startsWith("*") && part.endsWith("*")) return <i key={i}>{part.slice(1, -1)}</i>;
    return <span key={i}>{part}</span>;
  });
}

export default function Markdown({ text }) {
  const blocks = text.split(/\n\s*\n/).map((b) => b.trim()).filter(Boolean);
  return (
    <div className="space-y-2">
      {blocks.map((block, i) => {
        const lines = block.split("\n");
        if (lines.every((l) => l.startsWith(">"))) {
          return (
            <blockquote key={i} className="border-l-2 border-[var(--series-1)]/40 pl-3 text-[var(--ink-secondary)]">
              <Inline text={lines.map((l) => l.replace(/^>\s?/, "")).join(" ")} />
            </blockquote>
          );
        }
        if (lines.every((l) => /^[-*]\s/.test(l))) {
          return (
            <ul key={i} className="list-disc pl-5 space-y-0.5">
              {lines.map((l, j) => <li key={j}><Inline text={l.replace(/^[-*]\s/, "")} /></li>)}
            </ul>
          );
        }
        return <p key={i}><Inline text={lines.join(" ")} /></p>;
      })}
    </div>
  );
}
