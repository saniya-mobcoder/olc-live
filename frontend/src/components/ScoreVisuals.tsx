"use client";

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
} from "recharts";
import type { MatchResult } from "@/lib/types";

export function ScoreRadar({ result }: { result: MatchResult }) {
  const factors = result.breakdown?.factors || {};
  const data = Object.entries(factors).map(([key, value]) => ({
    factor: key.replace("_", " "),
    value,
  }));
  if (!data.length) return null;
  return (
    <div className="h-56 w-full">
      <ResponsiveContainer>
        <RadarChart data={data}>
          <PolarGrid stroke="rgba(11,61,46,0.25)" />
          <PolarAngleAxis
            dataKey="factor"
            tick={{ fill: "#10231c", fontSize: 11 }}
          />
          <Radar
            dataKey="value"
            stroke="#0b3d2e"
            fill="#1f6b4f"
            fillOpacity={0.35}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function BreakdownBars({ result }: { result: MatchResult }) {
  const factors = result.breakdown?.factors || {};
  return (
    <div className="space-y-2">
      {Object.entries(factors).map(([key, value]) => (
        <div key={key}>
          <div className="mb-1 flex justify-between text-xs uppercase tracking-wide text-[var(--olc-forest)]/70">
            <span>{key.replace("_", " ")}</span>
            <span>{value.toFixed(1)}</span>
          </div>
          <div className="score-bar">
            <span style={{ width: `${Math.min(100, value)}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}
