export default function DataTable({ rows }) {
  if (!rows?.length) return null;
  const cols = Object.keys(rows[0]);
  return (
    <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
      <table className="w-full text-[13px]">
        <thead>
          <tr className="bg-[var(--page)] text-left">
            {cols.map((c) => (
              <th key={c} className="px-3 py-2 font-semibold text-[var(--ink-secondary)] whitespace-nowrap">
                {c.replace(/_/g, " ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-[var(--border)] hover:bg-[var(--page)]/70">
              {cols.map((c) => (
                <td key={c} className="px-3 py-1.5 tabular-nums whitespace-nowrap text-[var(--ink-primary)]">
                  {typeof row[c] === "number" ? row[c].toLocaleString("en-IN") : String(row[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
