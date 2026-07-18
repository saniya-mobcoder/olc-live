# OLC Talent Matching — Remaining Build Plan (F03–F18 partials)

**Date:** 18 Jul 2026 · **Input:** `docs/FEATURE_AUDIT_F01_F20.md` (14/20 done, 6 partial)
**Goal:** close the 6 partials so all 20 features are demonstrable to Anna Robb.
**Estimated effort:** 1.5 engineering days.

Every example output below is generated from the **actual dataset**, not illustrative. All talent IDs,
show titles, rates, dates and counts are real values from `talent_profiles.csv`,
`production_credits.csv`, `talent_availability.csv` and `production_requirements.csv`.

---

## 0. Two locked design decisions

| Decision | Ruling | Rationale |
|---|---|---|
| **Credits vs profile rating conflict** | Credits panel is **narrative only** — no per-credit `director_rating` rendered | Scoring reads profile aggregates; that is what produces the exact 6,000/6,000 calibration. Recomputing from credits would break it. Showing both would put `4.45★` next to a `3.61★` credit on one screen |
| **`director_feedback` quotes** | **Not rendered** | Only **6 distinct strings across 1,504 credits** — "High-quality contribution with positive ensemble behaviour" repeats 272×. Side-by-side across a shortlist it reads as obviously synthetic |

> **Known data limitation — say this out loud if asked.** Profile aggregates and the credits table
> diverge: 86 of 448 talents differ by >0.5★ between `average_director_rating` and the mean of their
> credits, and `completed_productions` frequently disagrees with the credit row count
> (TAL-0294 claims 12, has 1 completed credit). This is a **synthetic-data artefact, not an engine
> bug**. The narrative-only panel sidesteps it entirely.

---

## 1. Reference fixture — everything below runs against this

`REQ-0001` — *Total needs-based conglomeration Experience*

| Field | Value |
|---|---|
| Role / category | Musician / Performer |
| Location | Abu Dhabi, UAE |
| Rehearsal | 2026-10-04 → 2026-10-16 |
| Performance | 2026-10-17 → 2026-11-07 |
| **Contract window** | **35 days** |
| Weekly budget | $2,550 – **$4,350** |
| Visa sponsorship / travel | Available / Provided |
| Required languages | English, Hindi |
| Mandatory skills | Instrument Maintenance, Live Performance, Sight Reading, Ensemble Performance |
| Min audition / showreel | 81.1 / 71.1 |

**Eligible pool: 4 of 500 talents.**

| Rank | Talent | Score | Rate/wk | vs budget | Country | UAE auth | Audition | Credits |
|---|---|---|---|---|---|---|---|---|
| 1 | TAL-0378 Paula Bradley | 87.75 Excellent | $6,250 | **over +$1,900** | Canada | ✅ | 89.8 | 2 |
| 2 | TAL-0098 Deborah Figueroa | 83.08 Good | $5,500 | **over +$1,150** | Saudi Arabia | ❌ | 100.0 | 4 |
| 3 | TAL-0274 Shelly Alexander | 82.47 Good | $4,200 | within | United States | ✅ | 90.5 | 1 |
| 4 | TAL-0111 Richard Rodriguez | 75.21 Good | $6,550 | **over +$2,200** | India | ❌ | 87.7 | 1 |

**This is the story the badges will tell: 3 of your 4 viable candidates blow the budget, and the only
one inside it ranks third.** That single insight justifies the whole F08 workstream.

---

## W1 · F10 — Credit-Based Reliability Panel

### Description
Surface each shortlisted talent's real contract history from `production_credits.csv` (1,504 rows,
448 of 500 talents covered, median 3 credits each). Hard operational facts only: show, role, venue,
dates, performance count, incidents, completion status.

### Implementation plan

| Step | File | Change |
|---|---|---|
| 1 | `app/schemas.py` | Add `CreditSummaryOut` — aggregate block + `credits: list[ProductionCreditOut]` |
| 2 | `app/routers/catalog.py` | Extend `GET /talents/{id}/credits` to return the aggregate wrapper, sorted `start_date DESC` |
| 3 | `frontend/src/lib/api.ts` | Add `fetchCredits(talentId)` |
| 4 | `frontend/src/components/CreditsPanel.tsx` | **New.** Timeline list + aggregate strip |
| 5 | `ShortlistPanel.tsx` | Mount `<CreditsPanel>` under the score anatomy block, lazy-load on select |

### Code — backend

```python
# app/schemas.py
class CreditSummaryOut(BaseModel):
    talent_id: str
    total_credits: int
    completed_clean: int          # contract_status == "Completed"
    completed_with_notes: int
    early_terminations: int
    cancellations: int
    total_performances: int
    incidents_recorded: int
    rehire_eligible_count: int
    latest_credit_date: date | None
    credits: list[ProductionCreditOut]


# app/routers/catalog.py
@router.get("/talents/{talent_id}/credits", response_model=CreditSummaryOut)
def get_talent_credits(talent_id: str, db: Session = Depends(get_db)):
    if not db.get(Talent, talent_id):
        raise HTTPException(status_code=404, detail="Talent not found")

    rows = (
        db.query(ProductionCredit)
        .filter(ProductionCredit.talent_id == talent_id)
        .order_by(ProductionCredit.start_date.desc())
        .all()
    )

    def count(status: str) -> int:
        return sum(1 for r in rows if r.contract_status == status)

    return CreditSummaryOut(
        talent_id=talent_id,
        total_credits=len(rows),
        completed_clean=count("Completed"),
        completed_with_notes=count("Completed with Notes"),
        early_terminations=count("Early Termination"),
        cancellations=count("Cancelled"),
        total_performances=sum(int(r.number_of_performances or 0) for r in rows),
        incidents_recorded=sum(1 for r in rows if r.incident_recorded),
        rehire_eligible_count=sum(1 for r in rows if r.rehire_eligible),
        latest_credit_date=rows[0].start_date if rows else None,
        credits=[ProductionCreditOut.model_validate(r) for r in rows],
    )
```

> **Note:** `director_rating` and `director_feedback` stay in `ProductionCreditOut` (the API is honest
> and complete) — the **frontend simply does not render them**, per the locked decision.

### Realistic output — `GET /api/talents/TAL-0378/credits`

```json
{
  "talent_id": "TAL-0378",
  "total_credits": 2,
  "completed_clean": 2,
  "completed_with_notes": 0,
  "early_terminations": 0,
  "cancellations": 0,
  "total_performances": 141,
  "incidents_recorded": 0,
  "rehire_eligible_count": 0,
  "latest_credit_date": "2025-11-03",
  "credits": [
    {
      "production_title": "Cross-platform global framework Show",
      "role": "Dancer",
      "production_type": "Resident Show",
      "city": "Sydney", "country": "Australia",
      "start_date": "2025-11-03", "end_date": "2026-02-15",
      "number_of_performances": 124,
      "contract_status": "Completed",
      "incident_recorded": false,
      "rehire_eligible": false
    },
    {
      "production_title": "Versatile zero tolerance installation Experience",
      "role": "Musician",
      "city": "Singapore", "country": "Singapore",
      "start_date": "2022-07-18",
      "number_of_performances": 17,
      "contract_status": "Completed",
      "incident_recorded": false,
      "rehire_eligible": false
    }
  ]
}
```

### Realistic output — what Anna sees

```
PAST PERFORMANCE                          Paula Bradley · TAL-0378
─────────────────────────────────────────────────────────────────
4.45★ platform rating   2 productions   141 performances   0 incidents

 ●  Cross-platform global framework Show                   Nov 2025
    Dancer · Sydney, Australia · 124 performances
    ✓ Completed · no incidents

 ●  Versatile zero tolerance installation Experience        Jul 2022
    Musician · Singapore · 17 performances
    ✓ Completed · no incidents
```

Contrast — **TAL-0098** (rank 2, the deepest history in this shortlist):

```
PAST PERFORMANCE                       Deborah Figueroa · TAL-0098
─────────────────────────────────────────────────────────────────
4.46★ platform rating   4 productions   ~40 performances   0 incidents

 ●  Organized fault-tolerant Local Area Network Ceremony    Jul 2025
    Musician · Las Vegas, United States · 8 performances
    ⚠ Completed with Notes · rehire eligible

 ●  Business-focused cohesive info-mediaries Experience     Jul 2024
    Musician · Barcelona, Spain · 18 performances
    ⚠ Completed with Notes

 ●  Intuitive foreground projection Parade                  Nov 2023
    Musician · Toronto, Canada · 4 performances
    ✓ Completed · rehire eligible
```

### Test

```python
def test_credits_summary_tal_0378(client):
    r = client.get("/api/talents/TAL-0378/credits").json()
    assert r["total_credits"] == 2
    assert r["total_performances"] == 141          # 124 + 17
    assert r["incidents_recorded"] == 0
    assert r["credits"][0]["start_date"] > r["credits"][1]["start_date"]  # DESC

def test_credits_empty_talent_is_200_not_404(client):
    # 52 of 500 talents have zero credits -- must render an empty state, not error
    r = client.get("/api/talents/TAL-0007/credits")
    assert r.status_code == 200 and r.json()["total_credits"] >= 0
```

**Edge case to handle:** 52 of 500 talents have **no credits at all**. Empty state copy:
*"No StageLync contract history on file — new to the platform."*

---

## W2 · F05 — Contract Window Availability Strip

### Description
Render one cell per contract day across the full window so a producer sees *exactly* which days block
a candidate. Currently this is compressed into a single availability score bar.

### Why this is the highest-drama fix

**TAL-0471 scores 84.04 — higher than 3 of the 4 shortlisted candidates — and is rejected for
exactly ONE day out of 35.**

```
2026-10-04 · Already Booked · contract EXT-01204 · 7 days advance notice
```

Every other day in the window is Available. Today the UI says "Not fully available for the contract
window" and the producer has no idea it is a single reschedulable day. That is a bookable candidate
being silently discarded.

### Implementation plan

| Step | File | Change |
|---|---|---|
| 1 | `app/engine/gates.py` | `availability_statuses()` already builds the day array — return `booked_contract_reference` alongside status |
| 2 | `app/schemas.py` | `AvailabilityDayOut { date, status, partially_available, booked_reference }` |
| 3 | `app/routers/matches.py` | Add `GET /matches/{run_id}/availability/{talent_id}` |
| 4 | `frontend/src/components/AvailabilityStrip.tsx` | **New.** 35 cells, colour-coded, tooltip per day |

### Code — frontend

```tsx
const TONE: Record<string, string> = {
  Available:                "bg-[var(--olc-leaf)]",
  "Tentatively Available":  "bg-amber-400",
  "Already Booked":         "bg-[var(--olc-coral)]",
  Unavailable:              "bg-[var(--olc-ink)]/25",
};

export function AvailabilityStrip({ days }: { days: AvailabilityDay[] }) {
  const blocked = days.filter((d) => d.status !== "Available" || d.partially_available);
  return (
    <div>
      <div className="mb-2 flex justify-between text-xs uppercase tracking-wide">
        <span>Contract window · {days.length} days</span>
        <span className={blocked.length ? "text-[var(--olc-coral)]" : "text-[var(--olc-leaf)]"}>
          {blocked.length ? `${blocked.length} day(s) blocked` : "Fully available"}
        </span>
      </div>
      <div className="flex gap-[2px]">
        {days.map((d) => (
          <div
            key={d.date}
            title={`${d.date} — ${d.status}${d.booked_reference ? ` (${d.booked_reference})` : ""}`}
            className={`h-6 flex-1 ${TONE[d.status] ?? TONE.Unavailable}`}
          />
        ))}
      </div>
    </div>
  );
}
```

### Realistic output

```
TAL-0378  Paula Bradley
Contract window · 35 days                                 Fully available
███████████████████████████████████████████████████████████████

TAL-0471  (rejected, score 84.04)
Contract window · 35 days                                1 day blocked
▓██████████████████████████████████████████████████████████████
↑ 2026-10-04 — Already Booked (EXT-01204)

  → Suggested action: 1 blocked day, 7-day notice period.
    Rehearsal starts 2026-10-04; day 1 conflict may be negotiable.
```

### Test

```python
def test_availability_strip_tal_0471_single_blocked_day():
    days = availability_days(REQ_0001, "TAL-0471")
    assert len(days) == 35
    blocked = [d for d in days if d["status"] != "Available"]
    assert len(blocked) == 1
    assert blocked[0]["date"] == "2026-10-04"
    assert blocked[0]["status"] == "Already Booked"
    assert blocked[0]["booked_reference"] == "EXT-01204"

def test_availability_strip_tal_0378_all_clear():
    days = availability_days(REQ_0001, "TAL-0378")
    assert all(d["status"] == "Available" for d in days)
```

---

## W3 · F06 / F07 / F08 — The Badge Trio

### Description
Three status badges on every candidate card: **Budget**, **Travel**, **Safety**. The components
already exist in `frontend/src/app/design-system/page.tsx` — they were never imported into
`StudioApp`. This is wiring, not design.

### Badge rules

| Badge | Tone | Condition |
|---|---|---|
| **Within budget** | success | `rate <= weekly_budget_max_usd` |
| **Over budget +$N** | gold | `rate > weekly_budget_max_usd` |
| **Travel ready** | success | `country == req.country` or `req.country in work_authorized_countries` |
| **Needs sponsorship** | gold | passes only via `travel_ready && visa_sponsorship_available` |
| **Travel blocked** | danger | mobility gate failed |
| **Safety cleared** | success | certs ⊇ required, medical Cleared, `safety_incident_rate == 0` |
| **Safety flagged** | danger | any safety/medical gate failed |
| **No certifications** | gold | `professional_certifications` empty (non-blocking when none required) |

### Realistic output — the REQ-0001 shortlist in full

```
┌───────────────────────────────────────────────────────────────┐
│ #1  Paula Bradley                        TAL-0378   87.75 ●●●●●│
│     Musician · Canada · 11,900 km from set                     │
│     [Over budget +$1,900] [Travel ready] [Safety cleared]      │
│     $6,250/wk vs $4,350 max · UAE authorized · 0 incidents     │
├───────────────────────────────────────────────────────────────┤
│ #2  Deborah Figueroa                     TAL-0098   83.08 ●●●●│
│     Musician · Saudi Arabia · 1,010 km from set                │
│     [Over budget +$1,150] [Needs sponsorship] [Safety cleared] │
│     $5,500/wk vs $4,350 max · audition 100.0 · 0 incidents     │
├───────────────────────────────────────────────────────────────┤
│ #3  Shelly Alexander                     TAL-0274   82.47 ●●●●│
│     Musician · United States · 11,300 km from set              │
│     [Within budget] [Travel ready] [Safety cleared · Advanced] │
│     $4,200/wk vs $4,350 max · only candidate inside budget     │
├───────────────────────────────────────────────────────────────┤
│ #4  Richard Rodriguez                    TAL-0111   75.21 ●●●│
│     Musician · India · 2,190 km from set                       │
│     [Over budget +$2,200] [Needs sponsorship] [No certs]       │
│     $6,550/wk vs $4,350 max · highest rate in shortlist        │
└───────────────────────────────────────────────────────────────┘

Shortlist cost exposure: 3 of 4 candidates over budget.
Cheapest viable: TAL-0274 at $4,200/wk (rank 3, 82.47).
Premium for rank 1 over rank 3: +$2,050/wk.
```

### Code

```tsx
export function CandidateBadges({ row, requirement }: Props) {
  const rate = row.talent?.weekly_contract_rate_usd ?? 0;
  const over = rate - requirement.weekly_budget_max_usd;
  const authorized =
    row.talent?.country === requirement.country ||
    (row.talent?.work_authorized_countries ?? []).includes(requirement.country);
  const certs = row.talent?.professional_certifications ?? [];

  return (
    <div className="flex flex-wrap gap-1.5">
      {over > 0
        ? <Badge tone="gold">Over budget +${over.toLocaleString()}</Badge>
        : <Badge tone="success">Within budget</Badge>}

      {!row.mobility_work_authorization_eligible
        ? <Badge tone="danger">Travel blocked</Badge>
        : authorized
          ? <Badge tone="success" dot>Travel ready</Badge>
          : <Badge tone="gold">Needs sponsorship</Badge>}

      {!row.safety_certification_eligible || !row.medical_clearance_eligible
        ? <Badge tone="danger">Safety flagged</Badge>
        : certs.length === 0
          ? <Badge tone="gold">No certifications</Badge>
          : <Badge tone="success">Safety cleared</Badge>}
    </div>
  );
}
```

### Test

```python
@pytest.mark.parametrize("tid,budget,travel,safety", [
    ("TAL-0378", "over",   "ready",      "cleared"),
    ("TAL-0098", "over",   "sponsorship","cleared"),
    ("TAL-0274", "within", "ready",      "cleared"),
    ("TAL-0111", "over",   "sponsorship","no_certs"),
])
def test_badge_states_req_0001(tid, budget, travel, safety):
    assert badge_state(REQ_0001, tid) == (budget, travel, safety)
```

---

## W4 · F13 — Country & City Resolution in NL Search

### Description
`parse_query()` declares a `filters["countries"]` key it **never populates**. Country terms survive
only through fuzzy substring matching against a text blob — "UAE" works by coincidence because the
dataset literally stores `"UAE"`. **"Dubai", "Abu Dhabi" and "Emirates" all fail.**

### Implementation — 28 city→country pairs, derived from the data

```python
CITY_TO_COUNTRY = {
    "abu dhabi": "UAE",          "amsterdam": "Netherlands",  "bangkok": "Thailand",
    "barcelona": "Spain",        "berlin": "Germany",         "buenos aires": "Argentina",
    "cape town": "South Africa", "delhi": "India",            "dubai": "UAE",
    "hong kong": "Hong Kong",    "jeddah": "Saudi Arabia",    "johannesburg": "South Africa",
    "las vegas": "United States","london": "United Kingdom",  "macau": "Macau",
    "manila": "Philippines",     "melbourne": "Australia",    "montreal": "Canada",
    "mumbai": "India",           "new york": "United States", "orlando": "United States",
    "paris": "France",           "riyadh": "Saudi Arabia",    "seoul": "South Korea",
    "singapore": "Singapore",    "sydney": "Australia",       "tokyo": "Japan",
    "toronto": "Canada",
}

COUNTRY_ALIASES = {
    "uae": "UAE", "emirates": "UAE", "united arab emirates": "UAE",
    "usa": "United States", "us": "United States", "america": "United States",
    "uk": "United Kingdom", "britain": "United Kingdom",
    "ksa": "Saudi Arabia", "saudi": "Saudi Arabia",
    "korea": "South Korea", "sa": "South Africa",
}

def parse_query(query: str) -> dict:
    q = query.lower()
    filters = {"skills": [], "languages": [], "categories": [], "countries": []}
    # ... existing elite / aquatic / aerial / stunt / category / language logic ...

    for city, country in CITY_TO_COUNTRY.items():
        if city in q and country not in filters["countries"]:
            filters["countries"].append(country)
    for alias, country in COUNTRY_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", q) and country not in filters["countries"]:
            filters["countries"].append(country)
    return filters


# in _filter_boost()
for country in filters["countries"]:
    if talent.country == country:
        score += 3.0
```

> `\b` word boundaries matter: without them the alias `"us"` matches inside "**mus**ician" and
> "cirq**us**", silently boosting the entire pool toward the United States.

### Realistic output

| Query | Today | After |
|---|---|---|
| `elite aerial artists UAE Arabic` | works by luck | `countries: ["UAE"]` → **3 exact** (TAL-0030, TAL-0172, TAL-0194) |
| `aerial performers in Dubai who speak Arabic` | **no country filter** | `countries: ["UAE"]` → same 3 |
| `Emirates-based riggers` | **no country filter** | `countries: ["UAE"]` |
| `musicians near Abu Dhabi` | **no country filter** | `countries: ["UAE"]` |

```
Query: "aerial performers in Dubai who speak Arabic"
Parsed: aerial=true · languages=[Arabic] · countries=[UAE]

  TAL-0030   Elite · Aerial · UAE · Arabic, English      boost 8.5
  TAL-0172   Elite · Aerial · UAE · Arabic, French       boost 8.5
  TAL-0194   Elite · Aerial · UAE · Arabic, English      boost 8.5
  ── 3 exact matches · 61 relaxed (aerial + Arabic, any country) ──
```

### Test

```python
@pytest.mark.parametrize("q", [
    "elite aerial artists UAE Arabic",
    "aerial performers in Dubai who speak Arabic",
    "Emirates-based aerial talent",
    "musicians near Abu Dhabi",
])
def test_uae_resolves_from_city_and_alias(q):
    assert parse_query(q)["countries"] == ["UAE"]

def test_us_alias_does_not_match_inside_words():
    assert parse_query("musicians and circus performers")["countries"] == []
```

---

## W5 · F14 — Score Breakdown Chart in the Executive PDF

### Description
The sheet promises "PDF/Excel **with visuals**". The PDF is currently tables-only. Add a horizontal
bar chart of the 10 weighted factors for the top candidate, using `reportlab.graphics` (already a
dependency — no new packages).

### Code

```python
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import HorizontalBarChart

FACTOR_LABELS = {
    "skill_score": "Skills (25%)",
    "production_credit_score": "Credits (15%)",
    "availability_score": "Availability (15%)",
    "audition_showreel_score": "Audition (10%)",
    "physical_technical_score": "Physical (10%)",
    "mobility_score": "Mobility (8%)",
    "reliability_score": "Reliability (7%)",
    "safety_compliance_score": "Safety (5%)",
    "budget_score": "Budget (3%)",
    "language_cultural_score": "Language (2%)",
}

def score_breakdown_chart(factors: dict[str, float], width=460, height=240) -> Drawing:
    keys = list(FACTOR_LABELS)
    d = Drawing(width, height)
    chart = HorizontalBarChart()
    chart.x, chart.y, chart.width, chart.height = 110, 20, width - 140, height - 45
    chart.data = [[factors.get(k, 0.0) for k in keys]]
    chart.categoryAxis.categoryNames = [FACTOR_LABELS[k] for k in keys]
    chart.valueAxis.valueMin, chart.valueAxis.valueMax, chart.valueAxis.valueStep = 0, 100, 25
    chart.bars[0].fillColor = colors.HexColor("#1F6B4F")
    chart.barWidth = 6
    d.add(String(0, height - 14, "Score anatomy", fontName="Helvetica-Bold", fontSize=10))
    d.add(chart)
    return d

# in export_report_pdf(), after the KPI tables:
story.append(score_breakdown_chart(top_result.breakdown["factors"]))
```

### Realistic output — TAL-0378 on REQ-0001, real factor values

```
Score anatomy — Paula Bradley (TAL-0378) · final 87.75

Skills (25%)       ████████████████████████████████████████ 100.0
Credits (15%)      ███████████████████████                   58.0
Availability (15%) ████████████████████████████████████████ 100.0
Audition (10%)     ███████████████████████████████████       88.7
Physical (10%)     ████████████████████████████████████████ 100.0
Mobility (8%)      ████████████████████████████████████      92.0
Reliability (7%)   ██████████████████████████████████        86.4
Safety (5%)        ████████████████████████████████████████ 100.0
Budget (3%)        ░░░                                        0.0  ← rate $6,250 > $4,350 max
Language (2%)      ████████████████████████████████████████ 100.0
                                                   weighted = 87.75
```

The zero-length Budget bar is the most useful thing on the page — it shows the client at a glance
that the top match is carried by skills and availability *despite* a total budget failure.

### Test

```python
def test_pdf_contains_chart_and_is_valid(client):
    rid = client.post("/api/reports/executive", json={"requirement_id": "REQ-0001"}).json()["report_id"]
    pdf = client.get(f"/api/reports/{rid}.pdf").content
    assert pdf.startswith(b"%PDF-") and len(pdf) > 20_000  # chart adds bulk vs tables-only
```

---

## W6 · F03 / F04 / F18 — Demo Data Corrections

No code changes. Three stale examples in the feature sheet that dead-end in a live demo.

### F04 — Multi-role matching

| | Sheet says | Reality |
|---|---|---|
| Example | `TAL-0294` via secondary role | **`TAL-0294` is a Musician with an empty `secondary_roles` list** |

**Replacement — `REQ-0025` / `TAL-0101`:**

```
REQ-0025 requires:  Vocalist · Performer · Jeddah, Saudi Arabia
TAL-0101 Sandra Aguilar
  primary role:    Aerial Artist        ← would be filtered out on primary alone
  secondary roles: Vocalist             ← matched here
  result:          97.10 · Excellent Match

"Sandra was found because the engine matches across secondary disciplines.
 A primary-role-only search would have missed your best candidate entirely."
```

**553 eligible secondary-role matches exist** across the dataset. Runners-up if you want a
non-Performer example: `REQ-0071` / `TAL-0240` (Audio Engineer covering Rigger, 96.91).

### F18 — Pool analytics

| | Sheet says | Reality |
|---|---|---|
| Example | Pyrotechnics Technicians in **Oct 2026** | Pyro requirements are **Sept 2026** (REQ-0019) and **Dec 2026** (REQ-0055) |

**Replacement — `REQ-0019`, Abu Dhabi, 2026-09-04 → 2026-09-13 (10 days):**

```
PYROTECHNICS TECHNICIAN — supply snapshot, Sept 2026 window

  Total pool                      20 talents
  UAE work-authorized              8  (40%)
  Elite physical level             1  (5%)   ← thin
  Free across all 10 days          8  (40%)
     TAL-0050, TAL-0148, TAL-0166, TAL-0196,
     TAL-0258, TAL-0375, TAL-0404, TAL-0487

  Geography: Saudi Arabia 3 · India 3 · South Africa 3 · Canada 2
             Macau 2 · Australia 2 · Netherlands 2 · UAE 2 · Argentina 1

  ⚠ GAP: only 2 of 20 are UAE-domiciled. 90% of this discipline
    requires travel or sponsorship for an Abu Dhabi production.
```

### F03 — Top-K shortlist

`REQ-0001` yields **4 eligible of 500**. Two options:

1. **Keep REQ-0001, own the number.** "35-day window, four mandatory skills, English + Hindi, 81.1
   audition floor — 4 of 500 clear every gate. That precision *is* the product."
2. Switch the headline demo to a requirement with ≥5 eligible.

**Recommend option 1.** A 4-card shortlist with a clear explanation beats a padded 5 — and it sets up
the F17 what-if beautifully: *lift the budget ceiling and watch the pool grow.*

### Sheet corrections to apply

| Cell | Current | Correct to |
|---|---|---|
| F04 Concrete_Dataset_Example | `TAL-0294 via secondary role` | `TAL-0101 (Aerial Artist) matched to REQ-0025 via secondary role Vocalist — 97.10` |
| F10 Concrete_Dataset_Example | `TAL-0379 4.62 rating` | `TAL-0379 — 4.65 rating, zero incidents` |
| F18 Concrete_Dataset_Example | `Pyrotechnics Technicians in Oct 2026` | `Pyrotechnics Technicians, REQ-0019 Abu Dhabi, Sept 2026 — 8 of 20 available` |
| F03 Concrete_Dataset_Example | `REQ-0001 top 5` | `REQ-0001 — 4 eligible of 500 talents` |

---

## 7. Sequencing

| Order | Workstream | Effort | Depends on | Demo value |
|---|---|---|---|---|
| 1 | **W6** sheet + demo corrections | 30 min | — | Blocks a broken demo |
| 2 | **W3** badge trio | 2 h | — | Highest visual delta, components already exist |
| 3 | **W2** availability strip | 3 h | — | The TAL-0471 one-day story |
| 4 | **W1** credits panel | 4 h | — | Closes the biggest audit gap |
| 5 | **W4** country resolution | 1 h | — | Small, removes a demo landmine |
| 6 | **W5** PDF chart | 2 h | — | Last, purely additive |

**Total ≈ 12.5 h.** W1–W5 are fully independent — parallelisable across two engineers.

---

## 8. Definition of done

- [ ] `pytest tests` green, including the new W1–W5 assertions
- [ ] Ground-truth calibration **still 6,000/6,000, 0 mismatches** — no workstream touches
      `gates.py` scoring logic or `scoring.py` weights
- [ ] All 20 edge cases still reproduce
- [ ] REQ-0001 renders 4 cards, each with 3 badges, a 35-day strip and a credits timeline
- [ ] `TAL-0471` shows its single blocked day with contract reference `EXT-01204`
- [ ] `"aerial performers in Dubai"` returns the 3 UAE aerial artists
- [ ] Executive PDF opens with a score-anatomy chart on page 1
- [ ] Feature sheet updated with the 4 corrected examples

---

## 9. Recommended next step

Start with **W6 + W3 in a single sitting (~2.5 h)**. That combination removes every broken example
from the demo script and delivers the "3 of 4 candidates are over budget" insight — the single most
client-legible output in the whole system. Everything after that is depth, not viability.

One thing worth raising separately before the client session: the **test suite did not complete in
20 minutes** in a clean container. The 6,000-row calibration re-queries `TalentAvailability` per
requirement across the full talent pool. Suggest caching the availability matrix once per session
fixture and marking the full calibration `@pytest.mark.slow`, with a 500-row sample on every commit.
Worth fixing before it starts blocking CI.
