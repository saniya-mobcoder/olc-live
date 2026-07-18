"use client";

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
} from "recharts";
import type { MatchResult } from "@/lib/types";
import { ScoreBar } from "@/components/ui";

export function ScoreRadar({ result }: { result: MatchResult }) {
  const factors = result.breakdown?.factors || {};
  const data = Object.entries(factors).map(([key, value]) => ({
    factor: key.replace(/_/g, " "),
    value,
  }));
  if (!data.length) return null;
  return (
    <div className="h-56 w-full">
      <ResponsiveContainer>
        <RadarChart data={data}>
          <PolarGrid stroke="rgba(255,255,255,0.12)" />
          <PolarAngleAxis
            dataKey="factor"
            tick={{ fill: "#8b8fc4", fontSize: 11 }}
          />
          <Radar
            dataKey="value"
            stroke="#22d3ee"
            fill="#8b5cf6"
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
    <div className="space-y-3">
      {Object.entries(factors).map(([key, value]) => (
        <ScoreBar
          key={key}
          label={key.replace(/_/g, " ")}
          score={Number(value)}
        />
      ))}
    </div>
  );
}
