"use client";

interface BarChartProps {
  data: { label: string; value: number }[];
  height?: number;
  color?: string;
}

/** Dependency-free bar chart. Bars scale to the max value in the series. */
export function BarChart({ data, height = 160, color = "var(--primary)" }: BarChartProps) {
  const max = Math.max(1, ...data.map((d) => d.value));

  return (
    <div className="flex items-end gap-[2px] w-full" style={{ height }}>
      {data.map((d, i) => (
        <div
          key={i}
          className="flex-1 h-full flex flex-col justify-end group relative"
          title={`${d.label}: ${d.value}`}
        >
          <div
            className="w-full rounded-t-sm transition-all group-hover:opacity-80"
            style={{
              height: `${(d.value / max) * 100}%`,
              minHeight: d.value > 0 ? 2 : 0,
              backgroundColor: color,
            }}
          />
        </div>
      ))}
    </div>
  );
}
