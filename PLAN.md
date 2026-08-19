# Budget Bot — Project Plan

> Read this file at the start of every session before doing anything else.
> Update it at the end of every session (see the convention at the bottom).

## 1. Project Overview

Budget Bot is a personal finance app built for Jonathan Cummins (Manchester, UK), running entirely
locally on his MacBook Air M3. It parses bank statement CSV exports into a local SQLite database,
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
- [x] Chase UK statement parsing — CSV export, via the profile-driven `csv_import.py` engine
      (replaced the original PyMuPDF/`fitz` PDF parser 2026-08-12)
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
- [x] Per-asset Growth % column on the main Assets list, just right of Value — colour-coded
      (green/red), recalculated for whichever time filter is currently selected on the page,
      matching the "Current Total Assets" delta above it (2026-07-17)
- [x] Growth-rate calculation + forward projection (blended market + contributions rate)
- [x] Projected trend line drawn on the net worth chart

### Stage 3 — Budgeting
- [x] Personal Budget page: Money In/Money Out editable grids, manually-entered total income
      override (salary sacrifice isn't fully known), computed Money Left Over — renamed "Overview"
      and moved to the top of the page, above Money In (2026-07-20)
- [x] Household Budget page: bills grid (service/provider/renewal date/amount), computed total,
      editable % split between the two people in the household
- [x] `budget.py` module: `PersonalBudgetItem`, `HouseholdBudgetItem`, `BudgetSetting` models
- [x] Household Budget: Actual-spend gap + Recurring Charges checklist, mirroring Personal Budget's
      (2026-07-17), sourced from a new, completely separate `HouseholdTransaction` table
      (`household_transactions.py`) for the joint Santander account — structurally isolated from
      Jonathan's personal Chase data, never touched by the Dashboard/Personal Budget/Chat
- [x] Santander statement support: originally a dedicated `parse_santander_transactions` PDF parser
      (2026-07-20, since replaced 2026-08-12 by the `SANTANDER` profile in `csv_import.py`'s shared
      CSV engine). Upload Statement page has two side-by-side boxes, Personal (Chase) and Household
      (Santander)

### Stage 4 — Dashboard & Analytics
- [x] KPI row: Net Worth, Total Spent, Monthly Average, Savings Rate
- [x] Category pie chart (top 6 categories + "Other categories", validated colourblind-safe palette)
- [x] Top 10 Merchants table — split into "Top 10 Spend" and "Top 10 Save" (2026-07-20), since a
      merchant showing a big savings-pot transfer alongside real purchases like Tesco/Amazon read as
      confusing; shares one time filter (All/1yr/YTD/6mo/1mo), independent of the pie chart's
- [x] Monthly spending trend chart (now "Monthly Spending & Savings Trend", two lines)
- [x] `analytics.py`: shared chronological month-sorting + savings-rate calculation, used by both
      the Dashboard and Chat (previously duplicated, buggy logic — now one source of truth)
- [x] Time-range filters (All / 1 Year / YTD / 6 Months / 1 Month) on the pie chart and trend chart,
      matching the Net Worth page's filter pattern — independent per section, not shared (2026-07-17)
- [x] Savings Rate KPI now shows the percentage as the headline figure (was the £ amount), with the
      £/mo as a secondary delta — plus a help tooltip explaining the calculation (2026-07-17)
- [x] Fun Money excluded entirely from the Savings & Investments figure (both contributions and
      withdrawals) everywhere it's calculated — Dashboard KPI, Dashboard trend chart, and Chat —
      since it behaves as a discretionary spending buffer, not genuine savings (2026-07-17)

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
3. ~~**Savings goal tracking**~~ — **built 2026-08-12**, see the Goals page (`goals.py`) in the Session
   Log — savings target + discretionary spend ceiling, with streaks, superseding this original idea.
4. **Asset allocation view on Net Worth** — a % breakdown across cash / stocks / crypto / pension
   (AJ Bell pension, ISA, Coinbase, Barclays Shares) — the current total net worth figure hides
   diversification/risk exposure entirely.
5. **Backup/export** — a one-click CSV/DB export. `budget_bot.db` is flagged "do not delete" in
   CLAUDE.md but has no backup story; it's a single local file holding years of net worth history.
6. ~~**Share Budget Bot with friends (Mac + Windows)**~~ — **built 2026-08-17**, as a genuine fork
   rather than in-app optional AI toggles (GitHub can't fork a private personal repo, so this repo's
   `main` gained a local `lite` branch pushed to a separate public repo, `boxuuu/Budget-Bot-Lite`).
   Persisted `CategoryRule` table and bank-agnostic CSV import (both originally scoped here) are done
   and shared by both repos. See the 2026-08-17 Session Log entries for the full breakdown - the one
   piece of the original scope NOT done is a per-user Settings UI for `SAVINGS_POT_NAMES`; only the
   `EXCLUDED_FROM_SAVINGS`/"Fun Money" half became user-configurable (`SavingsBufferMerchant`).

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
Known Issues). Outside the original 8 stages: the recurring-charges checklist (Suggested Features
above) is built for both Personal and Household Budget, and the app now supports two separate bank
accounts (Chase personal, Santander household) with fully isolated data. As of 2026-08-17, Budget
Bot Lite (public fork for friends, no AI) also exists and is past its first real testing pass — see
Session Log for the full build-and-fix history. As of 2026-08-19, `lite` also has a README, and
categories are user-editable (add/remove) on both branches instead of a hardcoded list.

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
- ~~**Two PDF parsers now, not one**~~ — **superseded 2026-08-12**: both accounts now use CSV
  exports via `csv_import.py`'s single profile-driven `parse_bank_csv()` engine instead of two
  bank-specific PDF parsers. A new bank is a new `BankCsvProfile`, not new parsing code — see
  `csv_import.py` and the Session Log entry below.
- ~~**No manual category-correction UI for household transactions yet**~~ — **superseded
  2026-08-17**: Manage Categories now has Personal/Household tabs, both with the same bulk actions
  and directly-editable merchant table (see Session Log). Household transactions can be corrected
  the same way Chase ones always could.
- **Savings & Investments netting scope**: applies to the Savings Rate KPI, Chat's context, and the
  Dashboard trend chart's "Savings & Investments" line — but deliberately *not* to the Dashboard's
  other general spending views (Total Spent, pie chart, top merchants), which stay gross/unmodified
  by design (netting would break the pie chart, which can't render a negative slice, and would
  misrepresent "Total Spent"). Worth knowing if numbers ever look inconsistent across the Dashboard.
- **Fun Money excluded from Savings & Investments entirely (2026-07-17), superseding the netting
  design from 2026-07-16**: Jonathan was unhappy the Savings Rate KPI showed a discouraging negative
  figure (-46%) despite feeling he saves well. Investigation found the netting design from the day
  before was too broad — Fun Money's month-to-month churn (£3.9k-£11.8k moving both in and out most
  months, presumably a spending buffer) was swamping genuinely strong, consistently positive saving
  into Emergency Fund/Wedding/SIPP/ISA/Round up (£2.6k-£8.7k/month). Excluded Fun Money entirely
  (`EXCLUDED_FROM_SAVINGS` in `analytics.py`) rather than just adjusting its netting direction — the
  average Savings Rate went from -46% to a genuine +38%. The other 4 named pots (Round up, Emergency
  Fund, Wedding, Overflow) are still netted as before; only Fun Money's treatment changed.
- **Budget targets vs actuals: parked, not just deferred**: Jonathan decided (2026-07-16) he's happy
  having access to the raw data and making his own calls rather than the app formally comparing
  budget vs actual. Don't build Stage 8's original goal unprompted — only the subscription-audit
  angle (Suggested Features above) is currently active.
- **Budget Bot Lite exists as a second repo, tracked from this same working directory**: a public
  fork for friends, `boxuuu/Budget-Bot-Lite`, built 2026-08-17 (see Session Log). This local
  `~/budget-bot` checkout carries both branches — `main` (this private repo, pushes to `origin`) and
  `lite` (pushes to a separate `lite` remote). A non-AI fix belongs on `main` first, then
  `git merge main` into `lite`; AI-specific or lite-only wording changes go on `lite` only. A
  standing `~/budget-bot-lite` clone exists purely for manual browser testing (`git pull` to refresh
  it) — it is not itself a git remote and has no bearing on either branch's history.
- **Lite's savings-pot netting is still hardcoded to Jonathan's own pot names, unlike the buffer
  exclusion**: `analytics.SAVINGS_POT_NAMES` (Round up/Emergency Fund/Wedding/Overflow) and the
  salary detection (`"From B E"` in `calculate_savings_rate`) were left untouched 2026-08-17 while
  `EXCLUDED_FROM_SAVINGS`/"Fun Money" became the configurable `SavingsBufferMerchant` mechanism —
  for a friend on lite whose bank doesn't share those exact strings, the Savings Rate KPI just shows
  N/A and pot-withdrawal netting silently never fires. Not broken, just inert. Worth making
  configurable the same way if it comes up as a recurring annoyance for an actual friend.
- **28 of Jonathan's real transactions are still tagged "Coffee & Beans"**, a category removed from
  `DEFAULT_CATEGORIES` 2026-08-19 (see Session Log). Left deliberately untouched rather than
  bulk-migrated — they still display/filter fine everywhere (categories are read from the data, not
  the list), they just can't be re-selected as "Coffee & Beans" going forward. Clicking
  "Re-categorise everything" on the Personal tab would flip them to Eating Out & Takeaway naturally
  (their `KNOWN_RULES` entries now point there) — offered to Jonathan, his call whether/when to do it.

## 9. Next Actions

1. Nothing currently blocking on `main`. Keep testing Budget Bot Lite as real friend usage surfaces
   issues (same pattern as 2026-08-17's fresh-install/real-data testing pass) — most likely next
   findings are more first-run rough edges, same category as what got fixed this session.
2. *(Only if it comes up for an actual friend)* Make `SAVINGS_POT_NAMES`/salary detection
   user-configurable on lite, same approach as the `SavingsBufferMerchant` toggle — see Known Issues.
3. *(Low priority, only if it comes up)* If Jonathan starts using per-pension projections regularly,
   revisit the Mar 2025 pension-transfer distortion noted in Known Issues — would need a way to tag a
   specific asset-value change as "transfer" so it's excluded from that asset's growth rate.
4. *(Jonathan's call)* Decide whether to bulk-migrate the 28 real "Coffee & Beans" transactions to
   Eating Out & Takeaway now, or leave them as legacy leftovers — see Known Issues.

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

### 2026-07-17 (continued) — Net Worth growth column, Savings Rate/Fun Money fix
Added a Growth % column to the Net Worth page's main Assets list, just right of Value, colour-coded
green/red and recalculated for whichever time-range filter is currently selected on the page (reuses
the same first/last-value-in-window logic as the "Current Total Assets" delta above it, applied
per-asset). Verified live: confirmed the header label and every row's percentage update correctly
when switching filters (e.g. Coinbase read -20.5% on "All" and -17.3% on "6 Months").

Separately, Jonathan pushed back on the Dashboard Savings Rate KPI: it showed a discouraging negative
figure despite him feeling he saves well, and he wanted it shown as a percentage with a better
explanation. Broke down the underlying transactions by month and found the 2026-07-16 netting design
was too broad: Fun Money's month-to-month churn (£3.9k-£11.8k moving both in and out most months) was
swamping genuinely strong, consistently positive saving into Emergency Fund/Wedding/SIPP/ISA/Round up
(£2.6k-£8.7k/month, positive every month). Confirmed with Jonathan that Fun Money behaves as a
discretionary spending buffer, not real savings, and got explicit sign-off to exclude it entirely
(both directions - a contribution isn't durable saving if it's earmarked to be spent) rather than
just adjusting how it nets. Implemented via a new `EXCLUDED_FROM_SAVINGS` list in `analytics.py`
(separate from `SAVINGS_POT_NAMES`, which still nets the other 4 pots as before); flipped the
Dashboard KPI to show the percentage as the headline with the £/mo as a secondary delta, added a help
tooltip explaining the calculation, and updated stale "Fun Money is a savings pot" wording in the
trend chart caption and Chat's system prompt so nothing contradicts the new definition. Verified live
in the browser (tile now reads +38%, £1,426/mo, green) and via a hover screenshot of the new help
tooltip. Committed as two separate commits (Net Worth growth column; Savings Rate/Fun Money fix) via
a manual `git add -p` split of `app.py`, kept logically separate despite landing in the same session.
Not yet pushed.

### 2026-07-20 — Household Budget gets its own account: Santander support
Jonathan wanted the expanded subscription-audit/recurring-charges pattern (built for Personal Budget
on 2026-07-16) added to Household Budget too — but the household spending lives on a separate
Santander account, and he was explicit it must never mix with his personal Chase data. Presented two
architectures (shared table with an account tag, vs a fully separate table) and he picked the
separate-table approach for a structural isolation guarantee rather than relying on remembering a
filter everywhere. Built `household_transactions.py`: a new `HouseholdTransaction` table plus its own
`HouseholdRecurringChargeDismissal` table (kept separate from `budget.RecurringChargeDismissal` too,
so a Personal dismissal can't suppress a Household one or vice versa). `categoriser.categorise_all`/
`recategorise_all` and `analytics.calculate_avg_monthly_spend`/`get_recurring_charges` all turned out
to already be generic (duck-typed on shared attribute names), so no changes needed there. Added the
same Actual-spend-gap + Recurring-Charges-checklist UI to the Household Budget page. Verified
end-to-end with synthetic data (add/dismiss/undismiss all worked) and confirmed zero leakage into the
personal `Transaction` table, then cleaned the synthetic data up.

First real upload failed ("No transactions found") - Jonathan shared his actual (real) Santander
statement to debug against. Investigation found Santander's layout is structurally different from
Chase's in three ways: transaction dates have no year at all (e.g. "23rd Jun", year only appears once
in a "Your transactions X to Y" header), amounts have no £ or minus sign, and whether a transaction
is money in or out isn't in the text at all - it has to be inferred by comparing each row's running
balance to the previous one. Built a dedicated `parse_santander_transactions` parser rather than
patching the Chase one (the formats are too different to share cleanly) and verified it against
Jonathan's real statement: all 21 transactions parsed correctly, uploaded via the real app UI, and
saved. While reviewing the categorisation results, found 4 real rule gaps that map directly to
existing Household Bills items (Octopus energy, Nationwide mortgage, Manchester council tax, JD
Plumbing) and added them to `categoriser.py`, then re-ran categorisation on the real household data.
Reconfirmed isolation held with this real data too (zero Santander descriptions found in the personal
table).

Jonathan then asked to reorganise the upload UI: move the Santander upload out of the Household
Budget page and onto the existing Upload Statement page, as a second box alongside the Chase one.
Restructured Upload Statement into two side-by-side cards ("Personal (Chase)" / "Household
(Santander)"); Household Budget keeps just the categorise button plus the Actual-spend/Recurring-
Charges analysis. Verified the moved upload still works (still finds 21 transactions from the new
location) and that duplicate detection correctly prevents re-saving. Also updated `claude.md`
(previously only updated as part of session end, not mid-session) since it had gone stale in several
places this session touched directly - new `household_transactions.py` module entry, updated Pages
section, added the two new dismissal-table model docs, fixed a stale "Fun Money is a savings pot"
mention, and replaced the hardcoded "935 transactions" snapshot with a pointer to PLAN.md (a specific
count would just go stale again). Note: while testing, discovered Jonathan had independently uploaded
several more real Santander statements himself in parallel (household transaction count reached 109,
spanning Dec 2025-Jul 2026) - confirms the feature works for him beyond just my test upload.

### 2026-07-20 (continued) — Dashboard/Personal Budget UI tweaks
Two quick UI requests. Split the Dashboard's "Top 10 Merchants" table into "Top 10 Spend" and
"Top 10 Save" (same Savings & Investments category split already used by the trend chart), sharing
one time-range filter independent of the pie chart's own filter — previously savings-pot transfers
like "To Emergency Fund" crowded the same top-10 list as real merchants like Tesco. Verified both
tables and the shared filter work correctly and independently from the pie chart's filter.

Moved Personal Budget's "Money Left Over" card to the top of the page (above Money In) and renamed
it "Overview" - required hoisting the `total_income = get_personal_total_income()` fetch above all
the cards (previously fetched inside the Money In/Income card, which the summary card depended on
being rendered first) rather than just moving the card and leaving a dangling reference. Verified
live: all four figures (Total expenses, Income minus expenses, Money per week, Actual monthly spend)
render correctly at the top, and the income input card below still works normally.

### 2026-07-24 — Statements Uploaded checklist on Upload Statement page
Jonathan wanted a way to see at a glance which months' statements he'd already uploaded, starting
from Jan 2026, worried that a missed month might silently fall off the list. Recommended and agreed
the range should run from Jan 2026 to the current month, recomputed live (not a fixed end date) -
this satisfies "never disappears" for free, since the start never moves and the end only ever grows
forward, so a missing month stays visible (unticked) indefinitely until actually uploaded.

Added `analytics.get_upload_checklist(existing_months, start_month)`, returning
`[(month_label, uploaded_bool), ...]` for Jan 2026 through today's month; added
`household_transactions.get_household_months()` (mirroring `database.get_months()`, which already
existed). Added a new "Statements Uploaded" section to the Upload Statement page, below the two
upload cards, mirroring their Personal/Household two-column split - each side is its own card listing
one row per month with a disabled `st.checkbox` (native tick, no emoji, per CLAUDE.md) ticked if any
transaction exists for that month. Verified live in the browser against real data: Personal (Chase)
correctly shows Jul 2026 unticked (no July Chase statement uploaded yet) while Jun and earlier are
ticked; Household (Santander) shows all months through July ticked, matching the real upload history
noted in the 2026-07-20 session log. No console errors.

### 2026-07-31 — Split Net Worth's actual and projected lines into separate charts
Jonathan disliked that the Net Worth page's "Total Assets Over Time" chart overlaid the 5-year
projected line on the same axes as actual history - the projection is always anchored on full,
unfiltered history and runs 5 years forward regardless of the time-range filter selected on the
actual line, so a narrow view (e.g. "1 Month") still shared an axis with a projection that could
reach into the hundreds of thousands, squashing the real, meaningful movement flat. Presented three
options (separate charts, a show/hide toggle, or a locked y-axis range on one shared chart); Jonathan
picked separate charts. Split "Total Assets Over Time" (now actual-only, respects the time filter,
autoscales properly - verified live that "1 Month" now shows a readable £207,000-£208,000 range
instead of a flat line) from a new "Net Worth Projection" card below it, which always shows full
history + the dashed projected line together on its own dedicated axis, independent of the page's
time filter (as the projection always was). Verified both live in the browser: the main chart at
"All" shows the full £100k-£207k climb in detail, the projection card shows actual + a ~50%/yr dashed
line out to 2031, and the "1 Month" filter now genuinely zooms in rather than being dwarfed by the
projection. No console errors.

### 2026-08-01 — Visual polish pass: typography, icons, card/button/nav refinement
Jonathan said the app looked "a bit dull" and asked what could be done, given it's plain Streamlit
with no design system beyond the existing card layout and brand accent color. Presented five levers
(CSS refinement, richer config.toml theming, icons, native nav restructuring, chart-template polish)
with tradeoffs; agreed to start with CSS + icons since both are zero-new-dependency and don't touch
the light/dark/system toggle CLAUDE.md protects, leaving the bigger nav restructuring for later if
wanted. Extended the single existing `st.markdown(<style>)` block in `app.py` (previously just the
card padding/shadow rule) with: a system-font stack (`-apple-system`/`Segoe UI`/etc - crisper, no
network fetch, unlike a Google Fonts import which would break offline use), heavier/tighter heading
weight, larger card border-radius, and a rounded-corners-plus-hover-lift rule for every button
app-wide. Also restyled the sidebar page picker (a plain `st.radio` under the hood) to read as a real
nav list - a highlighted pill for the active page and a hover tint on the rest, using `:has(input:
checked)` (safe in current browsers) rather than fragile emotion-hashed class names, which Streamlit
regenerates per version/build and can't be relied on directly.

Added Material Symbols icons (Streamlit's built-in `:material/name:` shorthand, no new dependency)
throughout: one per sidebar nav item via `format_func` on the `st.radio` (kept the underlying `page`
value a plain string, e.g. "Dashboard", so none of the many `elif page == "...":` routing checks
needed touching), one per page's `st.header`, and one on the top-level `st.title`. Found along the
way that `icon=` is not a valid kwarg on `st.title`/`st.header` in the installed Streamlit version
(1.50) despite that being a common assumption - the shorthand has to be embedded directly in the
body string instead (e.g. `st.header(":material/space_dashboard: Dashboard")`); fixed after hitting
a live `TypeError` and confirming the correct pattern via `inspect.signature`.

Verified live in the browser (screenshots, light mode + Playwright's dark `color_scheme` emulation,
`console --errors` checked on both): sidebar nav shows icons and a green highlight pill on the active
page, page headers show matching icons, cards have visibly softer rounded corners, and Personal
Budget's "Save Money In" button (checked as a representative example) picks up the new rounded/hover
style. Not yet committed - Jonathan asked to see it working before deciding whether to keep it.

### 2026-08-01 (continued) — Forest green palette, replacing the grey sidebar
Jonathan liked the polish pass but called out the leftover Streamlit-default grey (mainly the light
grey sidebar panel) as still looking dull, and asked for a darker forest green worked in - but was
explicit it shouldn't clash with the bright teal-green (`primaryColor` `#1D9E75`) already used
everywhere for data (chart lines, positive KPI deltas, category pie slices). Resolved this by treating
forest green as a separate *chrome* color, reserved for structure/navigation, and leaving every
existing data use of the bright teal untouched - the two greens now read as distinct rather than
competing for the same meaning.

Added a `:root` palette (`--forest-deep` #14251c, `--forest-mid` #2d6a4f, `--forest-soft` #e7efe9) to
the CSS block and: recoloured the sidebar background to `--forest-deep` (replacing Streamlit's default
light grey panel) with `[data-testid="stSidebar"] * { color: var(--forest-soft) !important; }` for
contrast: switched the nav's active-page pill (added earlier this session) from a teal tint to a solid
`--forest-mid` fill; gave cards a subtle forest-tinted border (previously shadow-only); and retinted
the button hover shadow from plain black/grey to a soft forest green. The sidebar is deliberately a
fixed dark green regardless of the light/dark/system toggle - same pattern as a permanent dark nav
rail in VS Code/Slack/Notion - since config.toml has never set background colors (only `primaryColor`)
so the toggle was only ever governing the main content area anyway; nothing about the toggle itself
changed.

Verified live via Playwright screenshots (full sidebar crop + two content pages, light mode and dark
`color_scheme` emulation, `console --errors` on all): sidebar text, icons, radio circles, chat input,
and the collapse-arrow icon are all legible against the dark green background; the active-page pill
is visibly a different, darker shade from the bright teal used in the Dashboard's pie chart and KPI
deltas right next to it. Not yet committed - same as the CSS/icon pass above, held for Jonathan's
review first.

### 2026-08-01 (continued) — Lighter forest shade + tinted main background
Two follow-up tweaks after seeing the forest palette live: Jonathan wanted a slightly lighter green
(the first pass's `--forest-deep` #14251c read almost black), and asked for the main page's stark
white background to be replaced with something that ties into the dark green rather than sitting
against it as plain white. Lightened `--forest-deep` to #1b3a2b and `--forest-mid` (the active nav
pill) to #3a7a5a - both still clearly distinct from the bright teal `primaryColor` used for data.
Added `--forest-page-bg` (#f2f7f4, a faint sage tint) applied to `.stApp` in light mode only (same
`@media (prefers-color-scheme: light)` pattern already used elsewhere, so dark mode - not "stark" in
the same way - is untouched). Also caught and fixed a visual seam this introduced: Streamlit's own
top toolbar strip (`[data-testid="stHeader"]`, the bar holding the Deploy/menu controls) has its own
separate white background and stayed stark white against the newly tinted body below it - tinted it
to match `--forest-page-bg` too. Cards keep their existing white-ish fill, so they still visibly pop
above the new tinted page background rather than blending into it. Verified live via screenshots
(Dashboard + Personal Budget, no console errors) - sidebar, header strip, and page background now
read as one cohesive palette. Not yet committed.

### 2026-08-01 (continued) — Per-asset breakdown toggle on Total Assets Over Time
Jonathan asked how hard it'd be to add a line per asset to "Total Assets Over Time." Flagged the
real tradeoff up front: assets span very different scales (pensions in the hundreds of thousands vs a
much smaller Emergency Fund), so all lines sharing one linear axis risks squashing the small ones -
the same problem just fixed for the actual/projected split earlier this session. Presented three
options (separate chart, same chart, same chart behind a toggle); Jonathan picked toggle - keep the
clean Total-only view by default, opt into the breakdown.

Refactored `networth.py`: pulled the pivot logic already inside `get_total_net_worth_series` (one
column per asset, forward-filled daily, before summing to Total) out into a shared `_daily_asset_pivot`
helper, and added `get_per_asset_series()` which returns that same pivot *without* summing it - one
column per asset. `get_total_net_worth_series` now calls the shared helper too, so both functions stay
in sync with zero duplicated pivot logic. Added a "Show per-asset breakdown" checkbox to the Net Worth
page (off by default) - when checked, one line per asset is added to the existing chart via
`go.Scatter` traces, respecting the same time-range filter and cutoff as the Total line, colored with
the same validated 8-slot categorical palette already used by the Dashboard's category pie chart
(colors assigned alphabetically by asset name, not by current value, so a given asset keeps its color
across every time filter - per the dataviz skill's "color follows the entity, not its rank" rule).
More than 8 assets would fold the smallest into a muted-gray "Other" line rather than generating a 9th
hue, though this hasn't been exercised yet (6 assets currently tracked). Loaded the dataviz skill
before implementing to reuse its validated palette rather than picking colors ad hoc.

Verified live in the browser: toggle off looks identical to before (Total line only, no legend, no
console errors); toggle on shows all 6 assets + Total with a horizontal legend, confirms the expected
scale tradeoff in practice (Private Pension and Total are clearly readable; Emergency Fund/Barclays
Shares/Coinbase/ISA/Workplace Pension compress into a thin band near £0 since they're much smaller) -
acceptable since it's opt-in and doesn't affect the default view. Not yet committed.

### 2026-08-12 — Goals page: savings/spend targets with streaks
Jonathan wanted to gamify saving more/spending less. A plain "did you save more than last month"
streak wouldn't work well since his spending is already fairly regular month to month, so we landed
on an explicit goals/targets design instead, with two open questions he asked for options on: how to
stop himself loosening a target he's about to miss, and how targets get set. Resolved: (1) a new goal
always takes effect from next month, never the one in progress, AND changing a goal immediately
zeroes its streak (even for a same-month future change) - a real cost to moving the goalposts, not
just a delay; (2) targets pre-fill with a suggested figure from the last 3 complete months' real
average, editable before saving; (3) scoped to two goal types only for v1 - an overall savings target
and an overall spend ceiling, deliberately not per-category, echoing the granularity/upkeep tradeoff
already parked once on Stage 8.

Built a new `goals.py` module, `Goal` model: append-only like `AssetValue` (editing never overwrites
the current row, just inserts a new one with a future `effective_month`), so past months keep being
judged by whatever target actually governed them at the time - history never changes retroactively.
`calculate_streak()` walks backward from the most recent complete month counting consecutive hits,
stopping at the first miss OR the first month that predates the CURRENT (most recently set) goal row -
that second condition is what makes an edit "reset" the streak, since a fresh edit's effective_month
is always next month, so zero complete months fall under it yet. Verified this logic directly
(bypassing the UI) with synthetic goal rows before trusting it: 3 consecutive hits ending on the most
recent month streaks correctly; a miss in the most recent month (even after prior hits) correctly
zeroes the streak, matching real "current streak" semantics (a break today zeroes it, regardless of a
past run); editing a goal correctly zeroes it even when a later month would otherwise have hit the new
target. All synthetic rows cleaned up afterward.

Added `analytics.get_monthly_spend()` (extracted from the existing `calculate_avg_monthly_spend`,
which now calls it) since the Goals page needed a per-month breakdown, not just one overall average,
for both the spend streak and the suggested-target calculation. Built the Goals page (new sidebar nav
entry, `flag` icon) with a Savings Goal and Spend Ceiling card - each showing the current target and
whether it's active yet or starts next month, the streak (`local_fire_department` icon), this month's
progress so far (informational only, doesn't count toward the streak until the month is complete), a
"Set a new target" expander with the suggested default, and a History expander. Added a compact
"Goals" tile to the Dashboard under the Spending by Category pie chart, in the space Jonathan pointed
out was free next to the taller Top Merchants card - shows both streaks at a glance, or a prompt to
visit the Goals page if neither is set yet.

Scoped to personal transactions only (`load_all_transactions`), matching every other savings-rate/
spend feature in the app (Household stays fully separate, per CLAUDE.md, and wasn't asked for here).

Hit and fixed one real bug during live testing: `st.number_input`'s pre-filled `value` used
`max(0.0, round(suggested))`, but `round()` on a float returns an int, and `max()` returning that int
tripped Streamlit's `StreamlitMixedNumericTypesError` (value/min_value/step must share a type) -
wrapped in `float()`. Verified the full flow live in the browser: suggested default populated
correctly, saved a real test goal (target correctly showed "Starts Sep 2026", streak stayed 0, History
table recorded it), confirmed the Dashboard tile picked it up, then deleted the test goal directly so
Jonathan's real database was left exactly as it was before (no goals set). Not yet committed.

### 2026-08-12 (continued) — Spend Ceiling scoped to discretionary spending only
Jonathan noticed the Spend Ceiling was using the same gross-spend definition as the Dashboard's "Total
Spent" (everything except Savings & Investments) - meaning Rent & Housing, Bills & Utilities, etc. all
counted toward it, which isn't spending he actually has month-to-month control over. Asked for the
goal specifically to reflect discretionary spending instead. Presented three exclusion-set options;
Jonathan picked excluding Rent & Housing, Bills & Utilities, Insurance & Finance, and Phone & Internet.

Added `goals.NON_DISCRETIONARY_CATEGORIES` and `goals.get_discretionary_monthly_spend()` - same gross-
outflow-excluding-Savings&Investments definition as `analytics.get_monthly_spend`, plus the four
excluded categories. Deliberately kept as a Goals-only helper rather than changing the shared
`analytics.get_monthly_spend`/`calculate_avg_monthly_spend`, which the Dashboard's KPI and trend chart
still use unmodified by design (same reasoning as the existing Savings & Investments netting scope
note in Known Issues - a goal-specific definition shouldn't leak into general spending views). Swapped
both of the Spend Ceiling's call sites (the Goals page and the Dashboard tile) to the new function;
relabelled the card "Discretionary Spend Ceiling" with a caption listing the excluded categories, and
the input/success-message copy to match.

While verifying this live, found the database already had a real Savings Goal (£835) and Spend Ceiling
(£250) saved, both effective Sep 2026 - initially concerning, since I'd verified the goals table was
empty at the end of the previous session. Asked Jonathan directly rather than assuming and deleting:
confirmed he'd set both himself while exploring the page (explains his Rent & Housing question - he
was looking at the real feature with real numbers). Left both untouched - the discretionary-spend
change applies automatically going forward without needing to touch the stored target values
themselves. Verified live: Goals page shows the new "Discretionary Spend Ceiling" title and exclusion
caption correctly against his real £250 target; Dashboard tile shows both streaks at 0 months (neither
goal's effective month has arrived yet). Not yet committed.

### 2026-08-12 (continued) — Fixed Dashboard "Monthly Average" KPI (all-time total ÷ hardcoded 6)
Jonathan flagged the Dashboard's Monthly Average KPI as impossible - it read £12,991.18. Root cause:
despite being labelled "Total Spent (6 months)", `spending['Amount'].sum()` was never actually filtered
to any date range - it summed EVERY transaction ever uploaded (12 months of real data, £77,947.08
total), and "Monthly Average" then divided that all-time total by a hardcoded `6` regardless of how
much data actually existed. Confirmed the exact arithmetic matched the bug (£77,947.08 / 6 =
£12,991.18) before fixing.

Fixed by actually filtering to the trailing 6 months (`DateParsed >= now - 182 days`, the same cutoff
already used by the page's own "6 Months" time-filter buttons) for both KPIs, and dividing by the
REAL number of distinct months present in that window rather than a fixed 6 - so the figure stays
correct even with less than 6 months of data, rather than swapping one hardcoded-divisor bug for
another. Verified live: Total Spent (6 months) now reads £51,595.64 (genuinely Feb-Jul 2026) and
Monthly Average reads £8,599.27 - both independently cross-checked against a direct pandas calculation
before trusting the UI number. Not yet committed.

### 2026-08-12 (continued) — Monthly Average KPI scoped to discretionary spend too
Even after the hardcoded-divisor fix above, Jonathan flagged the corrected £8,599.27 Monthly Average
as still implausibly high and asked what was actually driving it - suspecting inter-account transfers
and recent house-move costs. Broke down the real trailing-6-month data to check: confirmed both
guesses. Savings & Investments transfers (Emergency Fund, Fun Money, Wedding, AJ Bell contributions)
alone were £24,662.30 of the £51,595.64 total (48%) - money moving to his own pots, not spending - and
Rent & Housing included a real one-off £954 "Stockport Removals & Storage LTD" charge from the house
move alongside recurring ~£1,000-1,150/month "HOUSE ACC" transfers. This wasn't the hardcoded-6 bug -
it's the Dashboard's existing, deliberate "Total Spent stays gross/unmodified" design (Known Issues) -
but Jonathan agreed the Monthly Average KPI specifically would be more useful scoped to discretionary
spend, same definition as the Goals page's Spend Ceiling.

Changed Monthly Average to exclude Savings & Investments plus `goals.NON_DISCRETIONARY_CATEGORIES`
(Rent & Housing, Bills & Utilities, Insurance & Finance, Phone & Internet) - reused the same constant
rather than duplicating the list, so the two features can't drift apart. "Total Spent (6 months)"
deliberately left as-is (gross) - Jonathan was only asked about, and only agreed to, changing Monthly
Average; Total Spent stays the "complete picture" figure per the existing design principle. Added a
help tooltip on the KPI explaining what's excluded, since the number no longer means "everything you
spent." Verified live: Monthly Average now reads £2,469.88 (cross-checked against a direct pandas
calculation first) - a much more plausible discretionary figure than either the buggy £12,991.18 or
the corrected-but-still-gross £8,599.27. Not yet committed.

### 2026-08-12 (continued) — Replaced PDF statement upload with CSV (Chase + Santander)
Jonathan asked how hard it would be to eventually share Budget Bot with friends. Assessed this
separately (recorded above in §6 as a Suggested Feature) - not committed to, but the assessment
flagged bank-specific PDF parsing as the single biggest limiter on how many friends could actually
use the app. Discussing that, Jonathan realized both his own banks offer CSV exports and asked to
switch now, partly for robustness (the Santander PDF parser needed real debugging effort to get
working originally - no year on dates, amounts inferred from balance movement) and partly as a
concrete first step toward "less personal, more portable." He specifically asked for the CSV import
to be designed with other banks in mind, not two more one-off hardcoded parsers.

Got real sample exports for both banks and analyzed the actual formats before writing anything:
Chase (comma-delimited, a title row then a header, non-zero-padded dates like "1 August 2026",
already-signed comma-formatted amounts) and Santander's "midata" export (semicolon-delimited, header
is row 1, `DD/MM/YYYY` dates, a combined signed `Debit/Credit` column styled `-£142.03`, a
non-transaction footer row). Santander's CSV export can't be scoped to one statement period like
Chase's - it's always ~12 months, which the existing exact-match duplicate detection already handles
correctly on every re-upload (confirmed the overhead is not a real performance concern at this app's
scale before proceeding).

Built `csv_import.py`: a `BankCsvProfile` dataclass (delimiter, column names, date format, and either
a single signed amount column or separate debit/credit columns) plus one shared `parse_bank_csv()`
engine that finds the header row by locating the profile's date-column label (robust to Chase's extra
title row vs. Santander's none), and treats any row whose date field fails to parse as non-transaction
noise to skip (this is what discards Santander's footer row, with no bank-specific footer logic
needed). `CHASE` and `SANTANDER` are the two profiles defined so far - adding a friend's bank later is
a new profile, not a new parser. Deliberately did not build a self-service column-mapping UI for
non-technical friends to define their own profile - real feature, worth doing once an actual friend
on an actual unsupported bank shows up, not speculatively now.

Removed the now-dead PDF parsing code: `parse_transactions`, `parse_santander_transactions`, and
their helpers (`is_date`, `is_amount`, `is_balance`, `is_santander_date`, `is_plain_number`), the
`fitz` import, and (after confirming via repo-wide grep it was unused anywhere else) `PyMuPDF` from
`requirements.txt`. Updated both Upload Statement uploaders to accept CSV instead of PDF. Updated
`CLAUDE.md` (Tech stack, Project structure, Pages, Database models, Known Issues) - also caught and
fixed two pieces of unrelated staleness found along the way: the Goals page/`goals.py` and Goal model
were entirely missing from `CLAUDE.md` despite being built earlier this same session, and Suggested
Feature idea #3 ("Savings goal tracking") was still listed as open despite being superseded by Goals.

Verified thoroughly before considering this done: `parse_bank_csv` tested directly against both real
sample files first (correct row counts - 156 Chase, 190 Santander - correct date/amount conversion,
confirmed Santander's footer row excluded) before wiring into the UI at all. Live in the browser:
uploaded both real files through the actual Upload Statement page, confirmed "Found N transactions"
for both. For Chase (real, wanted data - his actual 14 Jul-13 Aug 2026 statement) went further and
actually clicked Save: "Saved 69 new transactions. Skipped 87 duplicates" (the 87 correctly caught
against transactions already in the database from prior PDF uploads - strong evidence the CSV parser
produces output byte-compatible with what the old PDF parser used to produce), then re-uploaded the
identical file and confirmed "Saved 0. Skipped 156" (full dedup). For Santander, the sample provided
was privacy-redacted (merchant descriptions replaced with asterisks) - deliberately did NOT click Save
in the live app, since that would have written meaningless placeholder text into Jonathan's real
household ledger. Instead verified the identical save/dedup logic against an isolated in-memory SQLite
database (same `HouseholdTransaction` model, never touching `budget_bot.db`): 190 saved on first pass,
0 saved/190 skipped on re-upload. Confirmed afterward that the real household transaction count was
unchanged (109, matching the last known count) and zero redacted rows leaked in. Spot-checked the
newly-saved real Chase rows for clean parsing (no stray quotes/whitespace/HTML-entity artifacts) -
correctly landed as "Uncategorised" pending the normal categorisation step, unrelated to this change.

### 2026-08-12 (continued) — Dropped "(Chase)"/"(Santander)" from the Upload Statement labels
Small follow-up in the same spirit as the CSV work above: Jonathan asked to remove the "(Chase)" and
"(Santander)" parentheticals from the Upload Statement page's two card subheaders and the matching
"Statements Uploaded" checklist labels - now plain "Personal" and "Household" - and flagged that,
going forward, the app should keep being developed with a user-agnostic mindset rather than assuming
Jonathan's own specific banks everywhere. Left the file-uploader hint text ("Upload your Chase
transactions CSV export") and warning messages as-is, since those are still functionally accurate -
Chase and Santander are the only two `BankCsvProfile`s that actually exist yet (see `csv_import.py`
and the Session Log entry above) - only the two card *titles* were asked to be genericized. Verified
live: both cards and both checklist columns now read "Personal"/"Household" with no console errors.

**Noted for future sessions**: Jonathan wants a consistently user-agnostic bias in ongoing work on
this app now, not just isolated to the CSV-import piece - e.g. prefer generic labels/wording over
Jonathan- or bank-specific ones where it costs nothing to do so, even on features not directly related
to the friends-sharing effort. Doesn't mean stripping personal specifics that are still load-bearing
(the `CHASE`/`SANTANDER` profiles, `chat.py`'s Jonathan-specific system prompt, `analytics.py`'s
named savings pots, etc. all still need Jonathan's real setup to function correctly today) - see the
"Share Budget Bot with friends" assessment (§6) for the fuller list of what that would actually take.

### 2026-08-17 — Budget Bot Lite: forked and stripped of AI
Jonathan asked how to actually create a downloadable version for friends, having previously only
assessed it (2026-08-12, §6). GitHub won't let a personal private repo be forked at all, so instead
of a real fork this repo's `main` gained a local `lite` branch, pushed to a new separate public repo,
`boxuuu/Budget-Bot-Lite`. This local `~/budget-bot` checkout now carries both branches side by side:
`main` pushes to the existing private `origin` remote as always, `lite` pushes to a new `lite`
remote. The working convention established and used all session: a fix that isn't AI-specific goes
on `main` first, then `git merge main` into `lite` to carry it across; AI-removal or lite-only wording
changes go directly on `lite`.

Stripped from `lite`: the Chat sidebar and `chat.py` entirely (unlike categorisation, it has no
non-AI fallback - it just doesn't exist here); the Ollama/web-search fallback tier in
`categoriser.py` (`categorise_all` is now rules-only - anything no rule matches stays `Uncategorised`
for a manual fix instead of an AI guess); `ollama`/`ddgs`/`primp` from `requirements.txt`;
personal-only `KNOWN_RULES` entries (a salary reference string, a specific plumber/council, an
account nickname - generic UK-wide brand rules were kept); `PLAN.md` entirely (this file - a personal
session log with no value to a friend); and `CLAUDE.md`'s remaining personal specifics (name,
location, hardware, real asset list), while keeping the file itself since it's genuinely useful for
anyone using an AI coding assistant on their own fork later.

New on **both** branches: a `CategoryRule` table (`categoriser.py`) that persists automatically
whenever a category is corrected, so a fix survives future statement uploads and full
re-categorisations instead of resetting every time - checked before `KNOWN_RULES` and (on `main`)
before Ollama, so a human correction always wins. This was the persisted-rules piece originally
scoped in the 2026-08-12 friends-sharing assessment (§6).

Verified via a fresh clone + fresh venv + `pip install` (simulating exactly what a friend's first
run looks like) and Streamlit's `AppTest` framework scripting through every page - `main` and `lite`
both boot clean with no import errors.

### 2026-08-17 (continued) — First real testing pass surfaces a string of first-run bugs
Testing `lite` end-to-end (not just "does it boot") surfaced several bugs that only show up on a
genuinely fresh install or with real bank data - none were caused by the AI removal itself, but
Jonathan's own long-running `main` instance never has zero data or a Windows-1252-encoded export, so
none had been hit before. Fixed on **both** branches (all found via `AppTest` scripting through
real/copied data, not just visual inspection):
- Manage Categories crashed outright on a completely empty database - `pd.DataFrame([]).sort_values`
  has no columns to sort on.
- Net Worth's manual "Add or Remove an Asset" tile already existed in the code but only rendered once
  at least one asset existed - a brand new user had no way in except a Worth It import, which almost
  nobody else will have.
- `start.sh` was hardcoded to `cd ~/budget-bot` regardless of where it was actually run from - running
  it from `~/budget-bot-lite` silently launched the *private* app instead (hit this personally: ran
  it from the lite clone, got confused why "lite" showed the Chat sidebar - it was actually launching
  `main`). Fixed with `cd "$(dirname "$0")"`.
- CSV upload crashed with `UnicodeDecodeError` on a real Santander export - Windows-1252 encodes £ as
  a single byte (0xA3) that isn't valid UTF-8 alone. Added `csv_import.decode_csv_bytes()` (tries
  utf-8-sig, then cp1252, then latin-1 as a guaranteed-to-succeed last resort).
- Santander redacts many transaction descriptions down to mostly asterisks, but still exposes a
  `Type` column (DD/Card Payment/Cash Back/etc.) separately - captured it (`BankCsvProfile` gained an
  optional `type_column`, `HouseholdTransaction` a `transaction_type` field with a PRAGMA-based
  migration for the already-existing table) and added a `Cash Back -> Other` rule (same reasoning as
  the existing `cash withdrawal -> Other` rule: unknowable regardless of merchant text). Also
  surfaced Type as a display column on View Transactions' Household tab for manual-correction context
  on everything Type alone can't resolve.
- Household transactions had **no** manual category-correction path at all - only a bulk "Categorise
  uncategorised" button, no browse/correct page like Chase always had. This is the exact gap flagged
  in Known Issues on 2026-07-20 and finally fixed here - see the next entry for where it ended up.

### 2026-08-17 (continued) — Manage Categories consolidated across both accounts, made bulk-editable
Went through a few iterations same session, each prompted by a follow-up ask:
1. Added a household category-management block directly to Household Budget (bulk button + merchant
   table + one-at-a-time correction form, mirroring Personal's old Manage Categories layout).
2. Moved it instead: Manage Categories now has Personal/Household tabs (same pattern as the new View
   Transactions tabs, added earlier the same session), each built from one shared
   `render_manage_categories()` function. Household Budget went back to just bills/split/actual-
   spend/recurring-charges, matching Personal Budget's scope - all categorisation lives in one place.
   Household picked up parity it never had (a "Re-categorise everything" button) as a side effect of
   sharing the function.
3. Both Recurring Charges filters and Manage Categories' own filter used a static category list that
   never included "Uncategorised" as an option - switched all three to derive their options from
   what's actually present in the data (same approach View Transactions' filter already used
   correctly), so "Uncategorised" (or anything else real) shows up whenever it's actually there.
4. Final iteration: replaced the separate "select merchant / select category / click Update" form
   with a directly-editable Category column on the merchant table itself (`st.data_editor` +
   `SelectboxColumn`, Merchant locked) and one "Save changes" button that diffs the edited table
   against the original and applies every changed row at once - several corrections in one save
   instead of one at a time.

All of the above shipped on both `main` and `lite`. Testing note: Streamlit's `AppTest` framework
(used throughout this session to script through pages/widgets without a browser) does not support
`data_editor` interactions at all - it's missing from its widget API entirely. Verified step 4's
actual logic a different way instead: replicated the exact diff/update code standalone against
copied real data (never the live database), confirming pandas index alignment correctly isolates
only the edited row even after filtering, and that the save path (DB update + `CategoryRule`
persistence) works end to end. Full 8-page `AppTest` sweep still covers everything else on the page.

### 2026-08-17 (continued) — Lite-only: first-run experience and a data-driven savings-buffer toggle
Two gaps specific to a brand new `lite` user, raised by Jonathan after testing uploads himself:
- The Dashboard's Savings Rate KPI tooltip and trend chart caption both named Jonathan's specific
  pots (Emergency Fund, Wedding, SIPP, ISA, Round up, Fun Money) - accurate on `main` (that's genuinely
  what `analytics.SAVINGS_POT_NAMES` matches there) but misleading on `lite`, where a friend's pots
  won't share those names. Reworded both generically on `lite` only; `main`'s wording is intentionally
  untouched since it still describes `main`'s real hardcoded behaviour accurately.
- A new user had no nudge to clear the `Uncategorised` backlog after uploading - Manage Categories
  exists but nothing points there. Upload Statement now auto-runs `categorise_all` right after a save,
  then shows a "Still need a category" card per account: the top 10 uncategorised merchants by £
  impact, each with an inline category picker saving via the same `save_user_rule()` Manage
  Categories uses. Always shown when there's a backlog (not just right after upload), so it also
  nudges on return visits.
- Jonathan proposed also asking a new user about their bank's specific "pots" during onboarding, then
  self-identified the problem: pots are a Monzo/Starling-specific concept, not something to assume
  every bank has. Went with a data-driven alternative instead of an upfront question: a new
  `SavingsBufferMerchant` table (`analytics.py`) plus a "Manage spending-buffer merchants" expander
  under the Dashboard's trend chart, listing whatever's actually categorised Savings & Investments in
  the real data and letting the user tag any of them as a spending buffer - the configurable
  equivalent of the hardcoded "Fun Money" exclusion, but never assuming pots exist at all.
  Deliberately left `SAVINGS_POT_NAMES` (the withdrawal-netting half) and the `"From B E"` salary
  detection untouched - still hardcoded to Jonathan's specifics, silently inert for anyone else. Not
  fixed here; tracked in Known Issues (§8) and Next Actions (§9) as a real follow-up if it matters to
  an actual friend.

### 2026-08-19 — README for lite, friendlier Recurring Charges copy, user-editable categories
Three separate small-to-medium asks in one session, all shipped to both `main` and `lite` (or
`lite`-only where noted). First, added `README.md` to `lite` (setup/run instructions) - the public
repo had no onboarding doc beyond source files, so a friend cloning it had no path from "cloned" to
"running" without asking Jonathan directly. `lite`-only, since `main` has no equivalent audience.

Second, rewrote both Recurring Charges cards' copy (Personal and Household Budget) - shorter,
friendlier tone, and the Household card's caption/help text no longer names "Santander" directly
(inaccurate for a friend on a different bank). `lite`-only for the same reason as the README.

Third, the larger piece: categories were a hardcoded Python list, so adding or removing one meant
editing code. Investigated where `CATEGORIES` was actually used before touching anything - found the
rest of the app already reads categories dynamically from the data itself (View Transactions, Manage
Categories, and Recurring Charges filters), so the static list only actually constrained two
dropdowns (the Manage Categories bulk-edit table and, on `lite`, the Upload Statement page's
uncategorised-merchant nudge). Moved the list into a new `Category` table (`categoriser.py`,
`name`/`sort_order`) seeded from `DEFAULT_CATEGORIES` on first use, with `get_categories`/
`add_category`/`remove_category` and a new "Manage category list" expander on the Manage Categories
page (shared once across the Personal/Household tabs, not duplicated, since the list is global).
Verified add/remove/duplicate-name/protected-removal logic against a scratch copy of the real
database before touching anything live.

Jonathan asked specifically that "Savings & Investments" can't be removed - traced it to four exact-
string matches (`analytics.calculate_savings_rate`/`get_monthly_spend`, `goals.get_discretionary_
monthly_spend`, the Dashboard's trend-chart/top-merchants splits) that would silently misreport
rather than crash if the category disappeared. Added `PROTECTED_CATEGORIES` in `categoriser.py`
(currently just this one) and blocked its removal in the UI and in `remove_category()` itself, not
just at the button level. Left the four `goals.NON_DISCRETIONARY_CATEGORIES` (Rent & Housing, Bills &
Utilities, Insurance & Finance, Phone & Internet) deletable but undocumented as protected - removing
one only stops future transactions being excluded from the Spend Ceiling, a narrower and more
self-correcting consequence than losing Savings & Investments entirely.

Also reviewed the default category list per Jonathan's flag that "Coffee & Beans" was too specific -
confirmed it in the code: its only three `KNOWN_RULES` entries (oddy knocky, kickback, coffeehit) are
hyper-local Manchester coffee shops, not generic merchants, which shouldn't have been in `lite`'s
"kept deliberately generic" rules list in the first place. Folded it into Eating Out & Takeaway in
`DEFAULT_CATEGORIES` and remapped those three rules; Jonathan's real database has 28 transactions
still tagged "Coffee & Beans" from before this change, left untouched rather than bulk-migrated (see
Known Issues) - they display/filter fine as-is, and a "Re-categorise everything" click would migrate
them naturally via the updated rules whenever Jonathan wants.

Built on `main` first (touching `categoriser.py`, `chat.py`'s three `CATEGORIES` usages, and
`app.py`), then merged into `lite` per the usual convention. The merge needed manual conflict
resolution in `categoriser.py`: kept the new `Category`/`get_categories`/`add_category`/
`remove_category` code (applies identically on both branches) but dropped `main`-only pieces that
don't belong on `lite` (the `import ollama`, `get_merchant_context`/`search_merchant_web`/
`categorise_with_ollama` functions, and `main`'s Ollama-referencing comment above `KNOWN_RULES`,
restoring `lite`'s own "no AI fallback in this build" comment instead). `PLAN.md` and `chat.py`
stayed deleted on `lite` as before (both are `main`-only by design). Also caught and fixed one
`lite`-only leftover the merge didn't touch - the Upload Statement page's uncategorised-merchant
nudge (`app.py`) still imported the old static `CATEGORIES` symbol, since it has no counterpart on
`main` and so wasn't part of the merge's diff at all. Compiled and functionally tested both branches'
`categoriser.py` before pushing; confirmed no other stale `CATEGORIES` references remained on either
branch. Pushed both `main` (`origin`) and `lite` (`lite` remote).

---

## Maintenance convention

At the end of every session, update this file: tick off completed checklist items, add any newly
discovered issues to §7, recompute the progress percentage in §6, refresh §8's priority list, and add
a new dated entry to §9. When Jonathan says "continue with PLAN.md" at the start of a session, read
this file in full before taking any other action.
