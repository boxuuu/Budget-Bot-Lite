# Budget Bot — Project Plan

> Read this file at the start of every session before doing anything else.
> Update it at the end of every session (see the convention at the bottom).

## 1. Project Overview

Budget Bot is a personal finance app built for Jonathan Cummins (Manchester, UK), running entirely
locally on his MacBook Air M3. It parses Chase UK bank statement PDFs into a local SQLite database,
categorises transactions using rule-matching with an Ollama-powered fallback (enriched with live web
search for unfamiliar merchants), and gives a full picture of Jonathan's finances: a spending
dashboard, a net worth tracker with growth projections, live-editable personal and household budgets,
and a natural-language chat assistant — permanently docked in the sidebar — that can answer questions
and make changes on request (always behind an explicit confirm step).

## 2. Tech Stack

- **Frontend:** Streamlit, card-based layout (`st.container(border=True)`), custom theme via
  `.streamlit/config.toml` (brand accent only, preserves the native light/dark/system toggle)
- **Database:** SQLite via SQLAlchemy (one file, `budget_bot.db`, four independent modules each
  defining their own models: `database.py`, `networth.py`, `budget.py`, plus shared analytics)
- **LLM:** Ollama, running two different local models for two different jobs —
  `llama3.2` (3B, fast) for batch merchant categorisation, `qwen2.5:14b` (slower, better reasoning)
  for the chat assistant's tool-calling and advice
- **Web search:** `ddgs` (DuckDuckGo) — gives the categoriser real context about unfamiliar merchants
- **PDF parsing:** PyMuPDF (`fitz`), tuned specifically for Chase UK statement format
- **Charts:** Plotly
- **Language:** Python 3.9

## 3. General Work Plan

The vision: a single local app that replaces (a) manually reading bank statements to categorise
spending, (b) a separate net worth spreadsheet, (c) Jonathan's personal and household budget
spreadsheets, and (d) ad-hoc "what's my spending like" mental math — all backed by real transaction
data, with an AI assistant that can be asked questions or told to make changes in plain English
instead of clicking through forms. Correctness of the underlying numbers (categorisation accuracy,
not double-counting internal transfers, accurate savings/income figures) is treated as more
important than visual polish, though both have had real investment.

## 4. Implementation Stages

| Stage | Status |
|---|---|
| 1. Core Transaction Pipeline | Complete |
| 2. Net Worth Tracking | Complete |
| 3. Budgeting (Personal & Household) | Complete |
| 4. Dashboard & Analytics | Complete |
| 5. AI Chat Assistant | Complete |
| 6. UI/UX Redesign | Complete |
| 7. Data Accuracy Refinements | Complete |
| 8. Budget Targets & Comparisons | Partially started (see below) |

## 5. Detailed Checklist

### Stage 1 — Core Transaction Pipeline
- [x] Chase UK PDF statement parsing (`fitz`/PyMuPDF)
- [x] Transaction storage (SQLite, `Transaction` model)
- [x] Duplicate detection on upload (exact date + description + amount match)
- [x] Merchant categorisation: known-rules dict + Ollama fallback
- [x] Web search (`ddgs`) context fed into the Ollama categorisation fallback
- [x] Manage Categories page: bulk categorise/re-categorise actions, manual correction form
- [x] View Transactions page: month, merchant, and category filters

### Stage 2 — Net Worth Tracking
- [x] `AssetValue` model, append-only historical snapshots
- [x] Worth It app export import
- [x] Net Worth page: asset list + per-asset detail drill-down with full history
- [x] Add/remove/update assets via UI
- [x] Time-range filters (All / 1 Year / YTD / 6 Months / 1 Month)
- [x] Growth-rate calculation + forward projection (blended market + contributions rate)
- [x] Projected trend line drawn on the net worth chart

### Stage 3 — Budgeting
- [x] Personal Budget page: Money In/Money Out editable grids, manually-entered total income
      override (salary sacrifice isn't fully known), computed Money Left Over
- [x] Household Budget page: bills grid (service/provider/renewal date/amount), computed total,
      editable % split between the two people in the household
- [x] `budget.py` module: `PersonalBudgetItem`, `HouseholdBudgetItem`, `BudgetSetting` models

### Stage 4 — Dashboard & Analytics
- [x] KPI row: Net Worth, Total Spent, Monthly Average, Savings Rate
- [x] Category pie chart (top 6 categories + "Other categories", validated colourblind-safe palette)
- [x] Top 10 Merchants table
- [x] Monthly spending trend chart (now "Monthly Spending & Savings Trend", two lines)
- [x] `analytics.py`: shared chronological month-sorting + savings-rate calculation, used by both
      the Dashboard and Chat (previously duplicated, buggy logic — now one source of truth)
- [x] Time-range filters (All / 1 Year / YTD / 6 Months / 1 Month) on the pie chart and trend chart,
      matching the Net Worth page's filter pattern — independent per section, not shared (2026-07-17)

### Stage 5 — AI Chat Assistant
- [x] Ollama tool-calling: `update_networth`, `update_category`, `project_net_worth` (with optional
      asset-subset support), `get_merchant_spending`
- [x] Confirm/Cancel UI before any database write
- [x] Fuzzy-match safety net for garbled enum values the local model returns
- [x] Malformed-response detection + auto-retry (catches wrong-script output and leaked JSON)
- [x] Upgraded chat model to Qwen2.5 14B (from Llama 3.2 3B) for better reasoning quality
- [x] Moved from a standalone page into a persistent sidebar, visible on every page

### Stage 6 — UI/UX Redesign
- [x] Card-based layout (`st.container(border=True)`) applied consistently across all pages
- [x] `.streamlit/config.toml` theming — sets the brand accent only, so the native light/dark/system
      toggle keeps working
- [x] Fixed a pre-existing routing bug (a broken `if`/`elif` chain had left a dead, unreachable
      duplicate Upload Statement page)

### Stage 7 — Data Accuracy Refinements
- [x] Added a "Salary" category, with a rule matching "From B E" transactions
- [x] Netted savings-pot transfers (Fun Money, Round up, Emergency Fund, Wedding, Overflow) so money
      moving back out of a pot reduces the savings figure instead of being invisible
- [x] Fixed negative-currency formatting in chat context (was rendering `£-1,461`, now `-£1,461`)
- [x] Real database re-categorised with the new rules (verified: 6 Salary rows, 0 Uncategorised)
- [x] Committed and pushed (2026-07-16)
- [x] Fixed three categoriser issues found by investigating why "Other" was the #2 spending
      category: the `"aj bell"` rule never matched `"A J Bell Securities"` (spacing), cash
      withdrawals fragmented into one "unique merchant" per branch/location instead of one rule,
      and the web search query reliably surfaced Companies House registration boilerplate instead
      of anything describing what a business actually does. Re-ran categorisation on the real
      database: "Other" dropped from £4,644 to £2,282, no longer the #2 category (2026-07-16)

### Stage 8 — Budget Targets & Comparisons
- [ ] **Budget targets vs actuals on the Dashboard — deferred, revisit when Jonathan wants it.**
      Investigated 2026-07-16: Personal/Household Budget line items are free-text bill names
      ("House", "BJJ / GYM", "Claude", "SIPP", "Mortgage", "Council Tax"...), not the 15 transaction
      categories — there's no clean 1:1 mapping to compare against. Two real options surfaced:
      (a) total-level only (one combined budgeted total vs actual total spend/month, no mapping
      needed), or (b) per-category with a manual category tag added to each budget line item
      (more granular, more upkeep). Jonathan wants to defer this decision rather than pick now —
      **raise it again periodically rather than silently building either option.**
- [x] Month-on-month comparison: Dashboard's trend chart is now two lines, Spending vs
      Savings & Investments (see Session Log 2026-07-16 below) — this was the practical
      "month-on-month" need that came up, may or may not fully close this checklist item depending
      on what else Jonathan has in mind for it.

## 6. Suggested Features (Not Yet Planned)

Ideas raised in conversation, not committed to any stage yet. Resurface these if Jonathan asks
"what's on the plan" or similar — don't build any of them unprompted.

1. ~~**Subscription audit**~~ — **built 2026-07-16**, see "Recurring charges checklist, built" below.
2. **In-month spend pace** — "you've spent £340 of a typical £450 Eating Out month, and it's only the
   12th" — projects the current month's trajectory against historical per-category averages. Lighter
   weight than a formal budget; sidesteps the Stage 8 budget-definition problem entirely.
3. **Savings goal tracking** — per-named-pot progress (Wedding, Emergency Fund, mortgage overpayments
   via Sprive) shown as "£X of £Y saved" against an implicit or explicit target, rather than the
   current lump Savings & Investments figure.
4. **Asset allocation view on Net Worth** — a % breakdown across cash / stocks / crypto / pension
   (AJ Bell pension, ISA, Coinbase, Barclays Shares) — the current total net worth figure hides
   diversification/risk exposure entirely.
5. **Backup/export** — a one-click CSV/DB export. `budget_bot.db` is flagged "do not delete" in
   CLAUDE.md but has no backup story; it's a single local file holding years of net worth history.

### Recurring charges checklist, built (2026-07-16)
Jonathan's real concern turned out to be narrower and more actionable than a full subscription audit:
the Personal Budget page's "Total expenses" is purely manual (a sum of the Money Out grid) with no
connection to real transactions, so it could never reveal spending he'd forgotten to budget for.
Built, rather than the originally-discussed auto-matching approach (matching budget line names like
"BJJ / GYM" to specific merchants like "Empire Grappling" was judged too fragile to trust — see the
parked Stage 8 discussion above for the same concern applied to Household Budget):
- **A real "Actual monthly spend" figure** (`analytics.calculate_avg_monthly_spend`) shown next to
  the manual "Total expenses" on the Personal Budget page, with an inverse-coloured delta — the gap
  is visible as a number with zero matching required.
- **A Recurring Charges card** (`analytics.get_recurring_charges`: merchants paid in ≥2 of the last 3
  months) listing each with Add to budget / Already in budget / Not recurring actions. No
  budget-item-to-merchant auto-matching — Jonathan compares the list against his own Money Out grid
  by eye, same principle as the parked Stage 8 decision.
- **Dismissals expire after 6 months** (`budget.RecurringChargeDismissal`, `DISMISSAL_EXPIRY_DAYS`)
  rather than hiding a merchant forever — explicitly requested by Jonathan, who didn't want to risk
  silently losing track of something he'd waved off once. Dismissed items sit in a collapsed
  "Reviewed" expander (with Un-dismiss) rather than disappearing outright.
- The "Actual monthly spend" figure is never affected by dismissals — it's always the true total,
  dismissing only declutters the checklist.

## 7. Progress

**~95% complete** on the original 8-stage plan. Stage 7 fully done and pushed. Stage 8 has one
concrete win (Dashboard trend chart split into Spending vs Savings lines) and one deliberately
parked decision (budget targets vs actuals — Jonathan is happy with raw data access instead, see
Known Issues). Separately, outside the original 8 stages: the recurring-charges checklist (Suggested
Features above) is built and verified in the real app, not yet pushed.

## 8. Known Issues

- **Chat model reliability**: the local `qwen2.5:14b` model occasionally misfires a tool call on an
  ordinary question (~1 in 5 in testing) or produces malformed output (wrong script, leaked JSON) on
  elliptical follow-ups. Mitigated with a detect-and-retry guard, not eliminated — this is a
  probabilistic limitation of running a 14B model locally, not a bug to "fix" outright.
- **Net worth projections can look extreme**: the growth rate is blended (market performance +
  Jonathan's own contributions, not a pure investment return), so long-horizon projections can produce
  very large, headline-grabbing figures. Caveated in the UI/chat text, but worth remembering when
  reading them. Fixed a real bug in this text 2026-07-16: `chat.py` was labelling the projection as
  "history since {anchor_date}" using the *end* of the history window (today) instead of the actual
  start — made a genuine ~2-year blended rate (Aug 2024 → Jul 2026, £92k → £207k) look like it came
  from almost no data. `networth.project_net_worth()` now also returns `start_date`; the chat message
  correctly reads "history from {start_date} to {anchor_date}".
- **Pension transfer in the net worth history (Mar 2025), confirmed harmless to the total**:
  Jonathan moved ~£12.8k from Workplace Pension (L&G) to Private Pension (AJ Bell, +£14.9k) around
  19–28 Mar 2025 — a one-off, won't recur. Verified 2026-07-16 this does NOT distort the total net
  worth growth rate: the Total series shows a normal change across those dates (£130,839 →
  £133,090, no artifact), and `calculate_growth_rate()` only ever compares the very first and very
  last data points anyway, so a mid-series event structurally can't move it. It DOES distort
  per-asset numbers if either pension is ever projected individually rather than as part of the
  total — currently Workplace Pension shows 89.8%/year and Private Pension 18.6%/year, partly
  reflecting this transfer rather than pure growth. No code change made (would need a way to tag a
  specific value change as "transfer, exclude from growth rate," which doesn't exist) — revisit only
  if per-asset projections become something Jonathan actually uses regularly.
- **PDF parser scope**: tuned specifically for Chase UK statement format — pre-existing, documented
  limitation, not something to fix unless a new statement format needs supporting.
- **Savings & Investments netting scope**: applies to the Savings Rate KPI, Chat's context, and (as of
  2026-07-16) the Dashboard trend chart's "Savings & Investments" line — but deliberately *not* to the
  Dashboard's other general spending views (Total Spent, pie chart, top merchants), which stay
  gross/unmodified by design (netting would break the pie chart, which can't render a negative slice,
  and would misrepresent "Total Spent"). Worth knowing if numbers ever look inconsistent across the
  Dashboard.
- **Savings Rate can be genuinely negative**: currently -£1,561/mo (-41% of salary) because Mar–Jun
  2026 each had net withdrawals from savings pots exceeding contributions. Confirmed with Jonathan
  2026-07-16 that this is correct/expected, not a bug — pots draining is real signal worth seeing, not
  something to hide behind a flat/always-positive percentage.
- **Budget targets vs actuals: parked, not just deferred**: Jonathan decided (2026-07-16) he's happy
  having access to the raw data and making his own calls rather than the app formally comparing
  budget vs actual. Don't build Stage 8's original goal unprompted — only the subscription-audit
  angle (Suggested Features above) is currently active.

## 9. Next Actions

1. Nothing currently blocking. The recurring-charges checklist is built and verified; the chat
   projection date bug is fixed. Resurface the four remaining Suggested Features ideas (§6) if
   Jonathan asks what's on the plan — none are committed to yet.
2. *(Low priority, only if it comes up)* If Jonathan starts using per-pension projections regularly,
   revisit the Mar 2025 pension-transfer distortion noted in Known Issues — would need a way to tag a
   specific asset-value change as "transfer" so it's excluded from that asset's growth rate.

## 10. Session Log

### 2026-07-15 — Core build
Built the app from an initial Chase-PDF-parsing prototype up through a full-featured local finance
app in one long session: web-search-assisted categorisation; chat tool-calling (net worth updates,
category fixes, net worth projections, merchant spend lookups) with a fuzzy-match safety net and a
malformed-response retry guard; upgraded the chat model to Qwen2.5 14B; moved chat into a persistent
sidebar; built the Personal Budget and Household Budget pages end-to-end (ported from Jonathan's own
spreadsheets, formulas verified against the originals); redesigned the Dashboard (KPI row, category
pie chart, top merchants, trend chart); did a full card-based UI redesign across every page with a
custom theme; fixed a pre-existing routing bug found along the way. Set up local git and a private
GitHub remote, committed and pushed everything.

### 2026-07-16 — Data accuracy refinements
Investigated and fixed two real data-accuracy issues: (1) salary transactions ("From B E") had no
proper category and were landing on "Other"/"Shopping" — added a dedicated Salary category and rule;
(2) transfers to/from Jonathan's named savings pots (Fun Money, Round up, Emergency Fund, Wedding,
Overflow) were only counted one-directionally, overstating the true Savings & Investments figure by a
large margin (Fun Money alone had £32k+ flowing back that was invisible to every calculation).
Added a shared netting helper in `analytics.py`, applied it to the Savings Rate calculation and
Chat's context — deliberately *not* to the Dashboard's general spending views, since that would have
broken the pie chart and misrepresented "Total Spent". Verified the real database re-categorised
correctly (6 Salary rows, exact net savings figures matching hand-calculated expectations). Created
this PLAN.md file for cross-session context tracking.

### 2026-07-16 (continued) — Dashboard trend chart split, Stage 8 scoping
Committed and pushed the Stage 7 changes above. Fixed the cosmetic negative-currency formatting on
the Dashboard's Savings Rate tile (moved `format_gbp` out of `chat.py` into `analytics.py` as a
shared helper, now used by both). Looked into Stage 8's "budget targets vs actuals" and found budget
line items (House, BJJ/GYM, SIPP, Mortgage...) don't map cleanly onto the 15 transaction categories —
flagged this to Jonathan, who chose to defer the decision rather than pick a mapping approach now;
documented as an open question to revisit periodically rather than a build task.

Separately, Jonathan noticed the Dashboard's Monthly Spending Trend was showing money moving into
savings pots (SIPP, ISA, Fun Money, etc.) as if it were spending — April looked like £15,866 "spent"
when £8,995 of that was actually a savings transfer. Split the chart into two lines: "Spending"
(gross, excludes Savings & Investments category entirely) and "Savings & Investments" (reuses the
same netted-by-month figures as the Savings Rate KPI, so it can legitimately dip below zero).
Validated the two-line colour pair with the dataviz skill's palette validator (CVD-safe, all checks
pass), then actually launched the app (installed Playwright + Chromium into the venv, since neither
was previously available) and screenshotted the real rendered chart to confirm the fix — April's
green Spending line now peaks around £6,500 instead of £15k, and the blue Savings line visibly dips
negative from March, matching the real net-withdrawal data. Also confirmed with Jonathan that the
Savings Rate KPI's current negative value (-41% of salary) is accurate, not a bug — pots have
genuinely been net-draining since March.

### 2026-07-16 (continued) — Categoriser fixes, Stage 8 parked, feature brainstorm
Jonathan asked why "Other" was his second-largest category — investigated and found it was £4,644
across 93 transactions, some genuinely miscellaneous but several real categoriser misses: the
`"aj bell"` rule silently never matched `"A J Bell Securities"` (spacing), cash withdrawals
fragmented into a separate "unique merchant" per branch/location instead of hitting one rule, and
(the interesting one) a pub called "Overdraught" got miscategorised because the web search query
("{merchant} UK company what type of business") reliably surfaced Companies House registration
boilerplate instead of anything describing what the business does. Fixed all three (new rules +
Companies-House-snippet filtering + reworded queries), verified the fix live against Ollama (flaky
once, then consistently correct), and re-ran categorisation on the real database: "Other" dropped to
£2,282, no longer the #2 category. Committed both this and the earlier trend-chart/formatting work
(2 commits, not yet pushed — Jonathan wants to test in the app first).

Talked through Stage 8 ("budget vs actuals") in more depth: surfaced that Personal Budget items have
no stored time period or history (editing overwrites silently), and — more importantly — that
household bills aren't itemised in Jonathan's transaction data at all, only lump transfers to a
shared "House Account" are visible, so per-bill household comparison isn't achievable with current
data regardless of mapping approach. Jonathan decided to park the original Stage 8 goal entirely
rather than build any version of it — he's happy with raw data access. Brainstormed and recorded five
other feature ideas (Suggested Features, §6) at his request, for future resurfacing rather than
immediate action. Of those, he's actively interested in the subscription audit idea and wants it
expanded into a two-way reconciliation against the Personal Budget "Money Out" list (catch charges
missing from the budget, and budget lines that have lapsed) — recorded in detail under Suggested
Features; not yet designed in full or built.

### 2026-07-16 (continued) — Recurring charges checklist built
Designed and built the recurring-charges feature from the brainstorm above, narrowed down through
conversation to Jonathan's actual concern: "my personal budget doesn't show my full spend." Talked
through the household-bills itemisation gap found earlier as a reason *not* to attempt auto-matching
budget items to specific merchants (same fragility, different page), landing on a simpler design: a
real "Actual monthly spend" figure computed from transactions next to the manual budgeted total
(closes the "how do I even see the gap" problem with zero matching), plus a Recurring Charges
checklist (merchants paid in ≥2 of the last 3 months) that Jonathan reviews and actions himself rather
than the app guessing. Added dismissal ("Already in budget" / "Not recurring") after Jonathan flagged
a real risk: a silent permanent dismiss could bury something and he'd never know to re-check it.
Agreed dismissals expire after 6 months rather than lasting forever, and dismissed items stay visible
in a collapsed "Reviewed" section (with Un-dismiss) rather than disappearing outright — nothing is
ever fully hidden. Built (`analytics.calculate_avg_monthly_spend`, `analytics.get_recurring_charges`,
`budget.RecurringChargeDismissal` + supporting functions, Personal Budget page UI), then verified live
in the browser: added a real recurring merchant to the budget and confirmed the write persisted,
dismissed another and confirmed it moved to Reviewed with today's date, un-dismissed it and confirmed
the dismissal table was empty again. Test data cleaned up afterward so Jonathan's real budget/database
weren't left with test artifacts. Committed (not yet pushed).

### 2026-07-16 (continued) — Net worth projection bug fix, pension transfer investigated
Jonathan questioned a chat projection ("£1,093,218 by 2030" from a stated "growing at 51.5%/year") -
found and fixed a real bug: `chat.py`'s projection message said "history since {anchor_date}" but
`anchor_date` is the *end* of the history window (today), not the start, so it wrongly implied the
51.5%/year rate came from almost no data when the real window is Aug 2024 → Jul 2026 (~2 years, £92k
→ £207k). `networth.project_net_worth()` now returns `start_date` too; message fixed to read "history
from {start_date} to {anchor_date}". The £1,093,218 figure itself was always correct arithmetic - only
the explanation was wrong. Verified the fix by simulating the corrected message text directly (didn't
re-launch the full chat UI for this one, since the fix is a pure string/data-plumbing change already
confirmed correct via `project_net_worth()`'s output).

Separately, Jonathan flagged that Workplace Pension and Private Pension both show a big one-off
dip/spike around Mar 2025 - a real pension transfer between the two, won't recur. Investigated whether
this inflates the total net worth growth rate used in projections: confirmed it does NOT (the Total
series shows a normal, non-distorted change across those dates, and the growth-rate calc only ever
compares the very first and very last data points, nowhere near Mar 2025) - but it DOES distort each
pension's *individual* growth rate if ever projected separately (Workplace Pension 89.8%/year, Private
Pension 18.6%/year, both partly reflecting the transfer rather than pure growth/contributions). No
code change made for this - documented in Known Issues as something to revisit only if per-asset
projections become a regular ask.

Jonathan ended the session here - PLAN.md updated and everything committed locally
(`chat.py`/`networth.py` projection fix), not yet pushed to `origin/main`.

### 2026-07-17 — Dashboard time-range filters
Added time-range filters (All / 1 Year / YTD / 6 Months / 1 Month) to the Dashboard's "Spending by
Category" pie chart and "Monthly Spending & Savings Trend" chart, matching the Net Worth page's
existing filter pattern (button row + session-state selection + "Showing: X" caption) rather than
inventing a new one. Each section got its own independent filter (not one shared control) since
Jonathan asked for filters on "the 2 sections" and viewing the pie chart at a different range than the
trend chart is a reasonable thing to want. Implementation notes: `Transaction.date` is a string
("01 Jan 2026" format) so a parsed `DateParsed` column was added to the Dashboard's working
DataFrame once and reused by both filters; the trend chart's Savings & Investments line now
recomputes `calculate_savings_rate()` on the filtered transaction subset per selection, rather than
reusing the KPI row's always-unfiltered figure. Found and fixed a real cosmetic bug along the way:
"6 Months" word-wrapped mid-word ("6 / Month / s") in the pie chart's half-width card, since the same
5-button row that fits comfortably on the Net Worth page's full-width layout doesn't fit in a
half-width Dashboard card - fixed with shorter button text (All/1yr/YTD/6mo/1mo) while keeping the
full name in the "Showing: ..." caption for readability. Both filters verified live in the browser:
confirmed they operate fully independently (changing one doesn't affect the other), confirmed the
pie chart correctly reflows for a filtered subset, and added an empty-state message for both charts
in case a selected range has no data. Committed, not yet pushed.

---

## Maintenance convention

At the end of every session, update this file: tick off completed checklist items, add any newly
discovered issues to §7, recompute the progress percentage in §6, refresh §8's priority list, and add
a new dated entry to §9. When Jonathan says "continue with PLAN.md" at the start of a session, read
this file in full before taking any other action.
