"use client";

import { useState } from "react";
import {
  AppHeader,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardFooter,
  Chip,
  Divider,
  Eyebrow,
  Field,
  Footer,
  Input,
  Label,
  ScoreBar,
  ScoreRing,
  SectionHeader,
  Select,
  Stat,
  StatusBadge,
  Tabs,
  TableWrap,
  THead,
  TH,
  TR,
  TD,
  Textarea,
} from "@/components/ui";

const STAGE = [
  ["magenta", "#ff2e93"],
  ["violet", "#8b5cf6"],
  ["cyan", "#22d3ee"],
  ["amber", "#ffb020"],
  ["coral", "#ff6a3d"],
  ["lime", "#34e0a1"],
];
const STATUS = [
  ["success", "#2de0a6", "Eligible / Excellent"],
  ["info", "#38bdf8", "Good match"],
  ["warning", "#ffbe3d", "Risk / Over-budget"],
  ["danger", "#ff4d6d", "Not eligible"],
];

function Swatch({ hex, name, note }: { hex: string; name: string; note?: string }) {
  return (
    <div>
      <div className="h-16 rounded-xl border border-line shadow-card" style={{ background: hex, boxShadow: `0 8px 30px -8px ${hex}66` }} />
      <div className="mt-2 text-xs font-semibold text-ink">{name}</div>
      <div className="text-[11px] text-ink-muted">{hex}{note ? ` · ${note}` : ""}</div>
    </div>
  );
}

export default function DesignSystemPage() {
  const [tab, setTab] = useState("match");
  const demoTabs = [
    { id: "match", label: "Match" },
    { id: "search", label: "Search" },
    { id: "pool", label: "Pool" },
    { id: "reports", label: "Reports" },
    { id: "copilot", label: "Copilot" },
  ];

  return (
    <div className="min-h-screen">
      <AppHeader
        nav={<Tabs items={demoTabs} value={tab} onChange={setTab} />}
        actions={
          <>
            <Button variant="ghost" size="sm">Docs</Button>
            <Button variant="primary" size="sm">New match</Button>
          </>
        }
      />

      <main className="mx-auto max-w-6xl px-6 py-16 space-y-20">
        {/* Hero */}
        <section className="text-center animate-rise">
          <div className="inline-flex items-center gap-2 rounded-full glass px-4 py-1.5 text-xs font-semibold text-ink-soft">
            <span className="h-1.5 w-1.5 rounded-full bg-lime animate-pulse-soft" />
            Our Legacy Creations · Design System
          </div>
          <h1 className="mx-auto mt-6 max-w-3xl text-6xl font-black leading-[1.02]">
            Cast the <span className="text-gradient">impossible.</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-ink-soft">
            Spotlight is the AI talent-intelligence copilot for live spectacle — an explainable
            matching engine wrapped in a vibrant, stage-lit interface built for OLC producers.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Button size="lg">Run a match</Button>
            <Button size="lg" variant="gold">Discover talent</Button>
            <Button size="lg" variant="outline">View credits</Button>
          </div>
        </section>

        {/* Color */}
        <section className="animate-rise">
          <SectionHeader eyebrow="Foundation" title="Color" subtitle="Vibrant stage-light accents over a midnight base. Status colors stay distinct from the brand gradient." />
          <div className="space-y-8">
            <div>
              <div className="mb-3 text-sm font-semibold text-ink">Stage lights</div>
              <div className="grid grid-cols-3 gap-5 sm:grid-cols-6">
                {STAGE.map(([n, h]) => <Swatch key={n} name={n} hex={h} />)}
              </div>
            </div>
            <div>
              <div className="mb-3 text-sm font-semibold text-ink">Signature gradient</div>
              <div className="h-20 rounded-2xl bg-spotlight shadow-glow-violet flex items-center justify-center font-display text-xl font-bold text-white">
                magenta → violet → cyan
              </div>
            </div>
            <div>
              <div className="mb-3 text-sm font-semibold text-ink">Status</div>
              <div className="grid grid-cols-2 gap-5 sm:grid-cols-4">
                {STATUS.map(([n, h, note]) => <Swatch key={n} name={n} hex={h} note={note} />)}
              </div>
            </div>
          </div>
        </section>

        {/* Typography */}
        <section className="animate-rise">
          <SectionHeader eyebrow="Foundation" title="Typography" subtitle="Fraunces (display, serif) paired with Source Sans 3 for UI." />
          <Card>
            <CardBody className="pt-6 space-y-3">
              <h1 className="text-5xl font-black text-gradient inline-block">Display — Fraunces</h1>
              <h2 className="text-3xl">Heading H2 — Fraunces</h2>
              <h3 className="text-xl">Heading H3 — Fraunces</h3>
              <p className="text-base text-ink-soft max-w-2xl">
                Body — Source Sans 3. Legible on midnight for shortlists, audit trails and
                explanations. The quick brown fox jumps over the lazy dog.
              </p>
              <p className="text-sm text-ink-muted">Muted caption / metadata text.</p>
              <Eyebrow>Eyebrow label · cyan uppercase</Eyebrow>
            </CardBody>
          </Card>
        </section>

        {/* Buttons */}
        <section className="animate-rise">
          <SectionHeader eyebrow="Component" title="Buttons" />
          <Card>
            <CardBody className="pt-6">
              <div className="flex flex-wrap items-center gap-3">
                <Button>Primary</Button>
                <Button variant="gold">Gold</Button>
                <Button variant="outline">Outline</Button>
                <Button variant="subtle">Subtle</Button>
                <Button variant="ghost">Ghost</Button>
                <Button variant="danger">Danger</Button>
                <Button disabled>Disabled</Button>
              </div>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <Button size="sm">Small</Button>
                <Button size="md">Medium</Button>
                <Button size="lg">Large</Button>
              </div>
            </CardBody>
          </Card>
        </section>

        {/* Badges */}
        <section className="animate-rise">
          <SectionHeader eyebrow="Component" title="Status badges" />
          <Card>
            <CardBody className="pt-6">
              <div className="flex flex-wrap gap-2.5">
                <StatusBadge label="Excellent Match" />
                <StatusBadge label="Good Match" />
                <StatusBadge label="Partial Match" />
                <StatusBadge label="Weak Match" />
                <StatusBadge label="Not Eligible" />
                <Badge tone="navy" dot>Featured</Badge>
                <Badge tone="gold">Over budget</Badge>
                <Badge tone="success">Travel ready</Badge>
              </div>
            </CardBody>
          </Card>
        </section>

        {/* KPI row */}
        <section className="animate-rise">
          <SectionHeader eyebrow="Pattern" title="KPI cards" subtitle="For Pool analytics, Reports and dashboard headers." />
          <div className="grid grid-cols-2 gap-5 lg:grid-cols-4">
            <Stat label="Eligible talent" value="128" delta={{ value: "12%", positive: true }} hint="vs last run" />
            <Stat label="Avg match score" value="82.4" delta={{ value: "3.1", positive: true }} />
            <Stat label="Gate-fail rate" value="34%" delta={{ value: "5%", positive: false }} hint="availability" />
            <Stat label="Open requirements" value="17" hint="6 markets" />
          </div>
        </section>

        {/* Score visuals */}
        <section className="animate-rise">
          <SectionHeader eyebrow="Component" title="Score visuals" />
          <Card>
            <CardBody className="pt-8">
              <div className="flex flex-wrap items-center justify-between gap-10">
                <div className="flex items-center gap-5">
                  <ScoreRing score={87.8} />
                  <ScoreRing score={72} />
                  <ScoreRing score={58} />
                  <ScoreRing score={41} />
                </div>
                <div className="w-full max-w-md space-y-3">
                  <ScoreBar score={92} label="Skill match" />
                  <ScoreBar score={74} label="Availability" />
                  <ScoreBar score={55} label="Budget fit" />
                  <ScoreBar score={38} label="Mobility" />
                </div>
              </div>
            </CardBody>
          </Card>
        </section>

        {/* Candidate cards */}
        <section className="animate-rise">
          <SectionHeader eyebrow="Pattern" title="Candidate cards" subtitle="How a shortlist entry looks in Spotlight." />
          <div className="grid gap-5 md:grid-cols-2">
            <Card accent interactive>
              <CardHeader
                eyebrow="Rank 01 · TAL-0378"
                title="Aerial Artist — Elite"
                subtitle="Dubai, UAE · 9.8 yrs · Arabic, English"
                action={<ScoreRing score={87.8} size={62} stroke={6} />}
              />
              <CardBody>
                <div className="flex flex-wrap gap-2 mb-4">
                  <StatusBadge label="Excellent Match" />
                  <Badge tone="success" dot>Travel ready</Badge>
                  <Badge tone="navy">4.62★ director</Badge>
                </div>
                <div className="space-y-2.5">
                  <ScoreBar score={92} label="Skill match" />
                  <ScoreBar score={100} label="Availability" />
                </div>
                <div className="mt-4 flex flex-wrap gap-1.5">
                  <Chip>Aerial Silks</Chip>
                  <Chip>Trampoline</Chip>
                  <Chip>Live Performance</Chip>
                </div>
              </CardBody>
              <CardFooter className="flex justify-between items-center">
                <span className="text-xs text-ink-muted">Within budget · $6,800/wk</span>
                <Button size="sm">View profile</Button>
              </CardFooter>
            </Card>

            <Card interactive>
              <CardHeader
                eyebrow="TAL-0471"
                title="Diver — Athletic"
                subtitle="Abu Dhabi, UAE · not eligible"
                action={<ScoreRing score={0} size={62} stroke={6} showLabel={false} />}
              />
              <CardBody>
                <div className="flex flex-wrap gap-2 mb-4">
                  <StatusBadge label="Not Eligible" />
                  <Badge tone="danger">Availability gate</Badge>
                </div>
                <p className="text-sm text-ink-soft">
                  Unavailable on key rehearsal dates (2026-10-04 → 2026-10-09). All other gates
                  pass — becomes eligible if the rehearsal window shifts by 5 days.
                </p>
              </CardBody>
              <CardFooter>
                <span className="text-xs text-ink-muted">Deterministic gate · logged to audit trail</span>
              </CardFooter>
            </Card>
          </div>
        </section>

        {/* Table */}
        <section className="animate-rise">
          <SectionHeader eyebrow="Pattern" title="Data table" subtitle="Shortlist / audit / credits listing." />
          <TableWrap>
            <THead>
              <TH>Rank</TH>
              <TH>Talent</TH>
              <TH>Role</TH>
              <TH>Score</TH>
              <TH>Status</TH>
              <TH>Rate</TH>
            </THead>
            <tbody>
              {[
                ["01", "TAL-0378", "Aerial Artist", 87.8, "Excellent Match", "$6,800"],
                ["02", "TAL-0294", "Acrobat", 79.2, "Good Match", "$5,400"],
                ["03", "TAL-0512", "Dancer", 63.5, "Partial Match", "$4,100"],
                ["—", "TAL-0471", "Diver", 0, "Not Eligible", "$7,200"],
              ].map((r) => (
                <TR key={r[1] as string}>
                  <TD className="font-semibold text-ink">{r[0]}</TD>
                  <TD className="font-medium text-ink">{r[1]}</TD>
                  <TD>{r[2]}</TD>
                  <TD>{r[3] ? (r[3] as number).toFixed(1) : "—"}</TD>
                  <TD><StatusBadge label={r[4] as string} /></TD>
                  <TD>{r[5]}</TD>
                </TR>
              ))}
            </tbody>
          </TableWrap>
        </section>

        {/* Forms */}
        <section className="animate-rise">
          <SectionHeader eyebrow="Component" title="Form controls" />
          <Card>
            <CardBody className="pt-6">
              <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                <Field label="Requirement" hint="Pick an open production">
                  <Select defaultValue="REQ-0001">
                    <option>REQ-0001 — Burj Khalifa NYE</option>
                    <option>REQ-0002 — Boulevard Parade</option>
                  </Select>
                </Field>
                <Field label="Search talent">
                  <Input placeholder="elite aerial UAE Arabic" />
                </Field>
                <Field label="Min score">
                  <Input type="number" defaultValue={70} />
                </Field>
                <div className="sm:col-span-2 lg:col-span-3">
                  <Label>Casting brief</Label>
                  <Textarea placeholder="Paste a casting brief to ingest…" />
                </div>
              </div>
            </CardBody>
          </Card>
        </section>

        {/* Tabs */}
        <section className="animate-rise">
          <SectionHeader eyebrow="Component" title="Tab navigation" />
          <Card>
            <CardBody className="pt-6">
              <Tabs items={demoTabs} value={tab} onChange={setTab} />
              <p className="mt-4 text-sm text-ink-muted">Active tab: <span className="font-semibold text-ink">{tab}</span></p>
            </CardBody>
          </Card>
        </section>

        <Divider />
        <p className="text-center text-sm text-ink-muted">
          Approve this direction and I&apos;ll roll Spotlight across every screen — Match, Search,
          Pool, Reports, StageLync, What-If, Copilot, Edge Cases and Audit.
        </p>
      </main>

      <Footer />
    </div>
  );
}
