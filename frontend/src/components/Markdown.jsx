// Tiny **bold** renderer — the agent's answers only ever use bold markers.
export default function Markdown({ text }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((part, i) =>
        part.startsWith("**") && part.endsWith("**") ? (
          <b key={i}>{part.slice(2, -2)}</b>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}
