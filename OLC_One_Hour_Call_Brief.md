# OLC Live — One-Hour Client Call Brief

**Format:** 60-minute call · demo-led · precise talking track with timings.
**Golden rule:** engine correctness is exact and defensible; the product shell is hardening. Never claim "everything is polished."
**One-liner to open and close with:** *"OLC shortlists talent the way a careful producer would — hard gates, a transparent score, an audit trail — and uses AI only to orchestrate and explain. It never invents a score."*

---

## Minute-by-minute agenda

| Time | Segment | Screen |
|---|---|---|
| 0–5 | Positioning & the problem | Overview |
| 5–10 | How it works (architecture in plain words) | Overview / slide |
| 10–22 | Core demo: the flagship match | Matching |
| 22–30 | Search + What-If Lab | Talent / Scenario Lab |
| 30–38 | Co-Pilot with governed AI | Co-Pilot panel |
| 38–46 | Reports, profiling & the paper trail | Reports |
| 46–50 | Decision → Booking → Call sheet | Operations |
| 50–54 | Honest status & rollout plan | slide / talk |
| 54–60 | Q&A + close | — |

---

## 0–5 min · Positioning & problem

Say, verbatim if needed:

- "Casting for live productions is high-stakes and opaque. One missed availability day, one unauthorized work country, one uncertified rigger — and a production loses a week or worse."
- "Generic AI matching tools are black boxes. You can't defend a black box to a performer, a client, or an insurer."
- "OLC inverts that: a **deterministic engine** owns eligibility and scores; **AI only orchestrates and explains**. Every AI sentence is validated against engine facts before it reaches the screen."

Point at the Overview dashboard: open requirements, and the readiness tiles — Healthy / Fillable / At Risk / Blocked — "your whole open book, triaged automatically, each with a recommended sourcing action."

---

## 5–10 min · How it works (plain words, no code)

Three sentences:

1. **Twelve hard gates** decide eligible vs. rejected: role, mandatory skills, day-level availability across the full contract window, audition & showreel thresholds, physical/specialist fit (aerial, aquatic, stunt), passport + visa + work authorization, safety certifications, medical clearance, language, overnight rehearsal, active profile, verified identity & references. Budget is a *commercial signal* unless you switch on strict-budget mode.
2. **A transparent score 0–100** ranks the eligible: Skills 25%, Credits 15%, Availability 15%, Audition 10%, Physical 10%, Mobility 8%, Reliability 7%, Safety 5%, Budget 3%, Language 2%. The full anatomy is visible on every candidate.
3. **Everything is recorded**: every run stores every candidate's result plus an audit trail; every AI explanation is logged with its model, cost, and grounding check.

Stack (only if asked): Next.js studio · FastAPI · PostgreSQL + pgvector · LangGraph agent · Groq free-tier Llama 70B with OpenAI failover · OpenAI embeddings.

---

## 10–22 min · Core demo: the flagship match (the heart of the call)

1. Select **REQ-0001 — Abu Dhabi Night Orchestra** → **Run match**.
   Say: *"35-day window, four mandatory skills, English + Hindi, audition ≥ 81.1 — **4 of 500** clear every gate. That precision is the product."*
2. Walk the four shortlist cards and their badges:
   - **TAL-0378** — over budget +$1,900 · travel ready · safety cleared
   - **TAL-0098** — over budget · needs sponsorship
   - **TAL-0274** — the **only one within budget**
   - **TAL-0111** — over budget · needs sponsorship · no certifications
3. Open Paula (TAL-0378): "Why this person" bullets, risk list (*"over budget is commercial, not a hard gate"*), credit history, **day-level availability strip**, and the score-anatomy chart.
4. **Gate-trust beat:** open the gated-out list, find **TAL-0471** — score ~84, *higher than three shortlisted* — blocked by **1 day of 35** (2026-10-04, an existing external booking). Say: *"Rules keep her out; the strip shows it's one negotiable day. Producers trust gates they can interrogate."*
5. **Secondary-role beat:** switch to **REQ-0025 (Jeddah Arena Vocal Ensemble)** → run → open **TAL-0101 Sandra Aguilar (~97, Excellent)** — primary role Aerial Artist, **matched as Vocalist via secondary role**. Say: *"A primary-role-only search would have missed your best candidate."*

Benefit statements: minutes instead of days; nothing unsafe or unavailable can slip through; every 'no' comes with an exact, evidence-backed reason.

---

## 22–30 min · Search + What-If Lab

**Search (3 min):** Talent tab → type *"aerial performers in Dubai who speak Arabic"*.
Say: *"City, country, and language become **enforced filters** — not ranking suggestions. Semantics only rank inside the filtered pool. And gender, age, ethnicity, religion, and appearance are structurally blocked from ever becoming search criteria."* Click **Score against REQ-0001** on any hit to show instant gate/score evaluation.

**What-If (5 min):** Scenario Lab → toggle visa sponsorship, adjust budget → **Compare scenarios**.
Say: *"Before you concede budget or sponsorship in a negotiation, quantify exactly what it buys: eligible delta, plus the named people you gain or lose. Scenarios never touch the real requirement, and simulation runs are excluded from executive KPIs so numbers can't be gamed."* Optionally click **Suggest scenarios** — AI proposes, the deterministic engine simulates.

---

## 30–38 min · Co-Pilot (governed AI)

With the REQ-0001 run loaded, three prompts only:

1. **"Why was the top pick recommended?"** — point at the tool-trace chips: the agent called the real matcher, then narrated its JSON. Sources listed on the reply.
2. **"What risks should the producer review?"** — grounded on the stored risk factors.
3. **"What changes if visa sponsorship is enabled? Propose only."** → a **Confirm & run** bar appears. Say: *"Mutations require a human confirm. The AI proposes; the engine executes; you approve. The confirm token is single-use and expires in 15 minutes."* Confirm → eligible delta → **View updated match**.

Trust facts to state: every reply is checked by a validator — any number not present in the engine's facts is rejected and replaced with a grounded template; protected-attribute language is blocked; and if a candidate is ineligible, no AI phrasing can imply otherwise. There's also a Help mode answering *only* from product FAQ, which honestly refuses when it doesn't know.

Cost fact: default model is Groq's free-tier Llama 70B with automatic OpenAI failover — the built-in cost dashboard shows AI spend near **$0**.

---

## 38–46 min · Reports, profiling & the paper trail

1. **Reporting Agent** (Reports opens here): ask *"Which roles have the largest talent shortage?"* — answer sentence + table + recommended action + sources. Say: *"Fourteen supported question types; numbers are computed, the AI only phrases them, and anything unsupported gets an honest 'not yet' instead of a guess."*
2. **Executive pack**: pick a period → **Generate pack** → **AI narrative** → download the **PDF** (KPI tables + a score-anatomy chart) or **Excel**. Note: what-if simulations are excluded; proxy metrics are labeled as such in the pack itself.
3. Name the rest of the suite (one breath): fillability per requirement, supply vs demand, availability & capacity, audition performance, reliability, **safety & compliance (9 flag classes per profile — passport expiry, pending medical, missing certs, incident history, unverified identity…)**, budget compatibility, daily digest, weekly bundle, per-requirement casting report, and a **per-talent due-diligence/profiling dossier** (profile, 20-credit history, auditions, reliability, safety flags, and a live match explanation) — API-ready today, screen pending.
4. Audit trail: every run, decision, AI explanation, and booking is an audit event — *"an evidence pack for every shortlist and every rejection."*

---

## 46–50 min · Close the loop: Decision → Booking → Call sheet

1. Mark the top pick **Shortlist** (hire).
2. Operations → Bookings → **Create booking**. Say: *"The booking writes back to her calendar — every contract day marked Booked — so she **cannot** be double-booked on another production; the system returns a conflict with the exact overlapping booking if anyone tries."*
3. Open the **Call sheet PDF** — production, role, dates, rate, and the match snapshot that justified the hire.
4. If pools are thin: show **StageLync** sourcing (sync → discover → import) — *be explicit*: it's a clearly-labeled connector **simulation** today that defines the exact contract for the live integration.

---

## 50–54 min · Honest status & rollout (build trust here)

**Done and defensible:** the matching engine reproduces the reference ground truth exactly; 20/20 contracted features have working paths; full test suite + CI.
**Deliberately deferred (closed demo):** authentication, roles/tenancy, public hosting, live StageLync API, real data — all synthetic, all localhost.
**Production plan (90 days):** ① auth/SSO + RBAC + TLS + hardened hosting → ② real-data migration + notifications → ③ live StageLync + Arabic localization → ④ instrumented pilot on 2–3 real productions with weekly executive packs.

---

## 54–60 min · Q&A rapid answers

| Likely question | Precise answer |
|---|---|
| Can the AI make up a score? | No — a validator rejects any number not in the engine's facts; fallback is a deterministic template. The engine owns all numbers. |
| Can weights/gates be customized? | Fixed today (parity with ground truth); per-client configuration is roadmap. |
| What does the AI cost? | ~$0 — free-tier Groq chat, cents of OpenAI embeddings; a live cost dashboard proves it. |
| What if the AI provider is down? | Automatic failover chain, and every AI surface degrades to a deterministic template — the demo works fully offline. |
| Bias/fair-hiring? | Gender, age, ethnicity, religion, appearance are blocked as filters and in outputs, at the pattern level, everywhere. |
| Is this real data? | Synthetic by design — production-shaped schema, zero PII risk; pilot migrates real data under the security workstream. |
| Where's login? | Deferred by design for the closed demo; first production workstream (SSO, RBAC, tenancy, TLS). |
| Accuracy proof? | Engine reproduces the reference ground-truth labels exactly; an edge-case manifest re-verifies hard scenarios on demand. |
| Scale? | 500-profile pool is instant; known scaling path (prefilters, ANN recall, precompute workers) for 50k+. |
| Timeline? | Engine is ready; production timeline = the security/hosting/integration list above (~90 days to pilot). |

**Close:** *"Precise enough to trust, clear enough to sell. The next step is a scoped pilot on your real briefs — the KPIs to prove ROI are already built into the product."*

---

## Pre-call checklist (do 30 min before)

- Postgres up (`docker compose up -d`), API on 8000 (`/api/health` green), UI on 3000.
- Both API keys set; hit **Explain** and **Co-Pilot** once to warm the free-tier models.
- Verify the three presets: REQ-0001 → 4 shortlisted; TAL-0471 visible in gated-out; REQ-0025 → TAL-0101 "matched as Vocalist".
- Open one shortlist PDF export in advance (backup if live export stalls).
- Rehearse the offline story: if a provider fails mid-call, replies are tagged "template" and the demo continues.
