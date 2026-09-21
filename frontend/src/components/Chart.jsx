import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const TOKENS = {
  gridline: "#e1e0d9",
  baseline: "#c3c2b7",
  inkSecondary: "#52514e",
  inkMuted: "#898781",
  series1: "#2a78d6",
  critical: "#d03b3b",
  surface: "#ffffff",
};

const numberFmt = (v) =>
  Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(v % 1000 === 0 ? 0 : 1)}k` : `${v}`;

function CustomTooltip({ active, payload, label, yKey }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-[var(--border)] bg-white px-3 py-2 shadow-lg text-xs">
      <div className="font-semibold text-[var(--ink-primary)] mb-0.5">{label}</div>
      <div className="text-[var(--ink-secondary)] tabular-nums">
        {yKey.replace(/_/g, " ")}: <b>{payload[0].value.toLocaleString("en-IN")}</b>
      </div>
    </div>
  );
}

export function TrendLineChart({ data, xKey, yKey, height = 280 }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={TOKENS.gridline} strokeDasharray="0" />
        <XAxis
          dataKey={xKey}
          tick={{ fill: TOKENS.inkMuted, fontSize: 11 }}
          axisLine={{ stroke: TOKENS.baseline }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: TOKENS.inkMuted, fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={numberFmt}
          width={44}
        />
        <Tooltip content={<CustomTooltip yKey={yKey} />} cursor={{ stroke: TOKENS.baseline, strokeDasharray: "3 3" }} />
        <Line
          type="monotone"
          dataKey={yKey}
          stroke={TOKENS.series1}
          strokeWidth={2}
          dot={{ r: 4, fill: TOKENS.series1, strokeWidth: 1.5, stroke: TOKENS.surface }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function ValueBarChart({ data, xKey, yKey, highlightNegative = false, height = 280 }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={TOKENS.gridline} />
        <XAxis
          dataKey={xKey}
          tick={{ fill: TOKENS.inkMuted, fontSize: 11 }}
          axisLine={{ stroke: TOKENS.baseline }}
          tickLine={false}
          interval={0}
          angle={data.length > 5 ? -20 : 0}
          textAnchor={data.length > 5 ? "end" : "middle"}
          height={data.length > 5 ? 45 : 30}
        />
        <YAxis
          tick={{ fill: TOKENS.inkMuted, fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={numberFmt}
          width={44}
        />
        <Tooltip content={<CustomTooltip yKey={yKey} />} cursor={{ fill: "rgba(11,11,11,0.04)" }} />
        <Bar dataKey={yKey} radius={[4, 4, 4, 4]} maxBarSize={46}>
          {data.map((d, i) => (
            <Cell key={i} fill={highlightNegative && d[yKey] < 0 ? TOKENS.critical : TOKENS.series1} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
