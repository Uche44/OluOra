"use client";

interface LineChartProps {
  values: number[];
  height?: number;
  color?: string;
}

/** Dependency-free SVG line chart. The stroke keeps constant width when scaled. */
export function LineChart({ values, height = 160, color = "var(--primary)" }: LineChartProps) {
  const n = values.length;
  const max = Math.max(1, ...values);

  const points = values
    .map((v, i) => {
      const x = n === 1 ? 0 : (i / (n - 1)) * 100;
      const y = 100 - (v / max) * 100;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      className="w-full"
      style={{ height }}
    >
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
