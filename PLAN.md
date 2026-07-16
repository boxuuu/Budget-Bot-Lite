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
- [x] Monthly spending trend chart
- [x] `analytics.py`: shared chronological month-sorting + savings-rate calculation, used by both
      the Dashboard and Chat (previously duplicated, buggy logic — now one source of truth)

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

1. **Subscription audit** — a view listing every recurring/subscription-style charge (Subscriptions
   category: Claude, iCloud, Patreon, Steam, Microsoft, etc.) with total monthly burn. **Jonathan is
   actively interested in this one (2026-07-16) — see the expanded version below, currently the most
   likely next build.**
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

### Subscription audit, expanded (2026-07-16 discussion)
Jonathan's specific ask: not just a list of recurring charges, but something that cross-checks against
the **Personal Budget "Money Out" list** so nothing gets missed in either direction —
(a) *recurring charges with no matching Personal Budget line* (paying for something he forgot to
budget for, or forgot he's still paying for at all), and (b) *Personal Budget lines with no recent
matching transaction* (budgeted for something that's lapsed or been cancelled). This is a
reconciliation/detection feature (matched vs unmatched), not a numeric budget-vs-actual comparison —
which sidesteps the Stage 8 mapping-precision problem, since it only needs to answer "does this
recurring charge appear somewhere in the budget, yes or no," not "is the amount exactly right."
Several Personal Budget items already map to a specific known merchant/rule in `categoriser.py`
(BJJ/GYM → gym rules, Phone → Vodafone/Plusnet, SIPP/ISA → AJ Bell/Sippdeal, Claude/iCloud →
subscription rules), which is a more precise anchor than category-level matching. Not yet designed in
detail or built — next step if Jonathan wants to proceed is nailing down what counts as "recurring"
(e.g. appeared in ≥2 of the last 3 months) and how fuzzy the budget-item-to-merchant match should be.

## 7. Progress

**~95% complete** on the original 8-stage plan. Stage 7 fully done and pushed. Stage 8 has one
concrete win (Dashboard trend chart split into Spending vs Savings lines) and one deliberately
deferred decision (budget targets vs actuals — Jonathan is happy with raw data access instead, see
Known Issues). Separately, a new feature (subscription audit) is now under active discussion —
see Suggested Features above.

## 8. Known Issues

- **Chat model reliability**: the local `qwen2.5:14b` model occasionally misfires a tool call on an
  ordinary question (~1 in 5 in testing) or produces malformed output (wrong script, leaked JSON) on
  elliptical follow-ups. Mitigated with a detect-and-retry guard, not eliminated — this is a
  probabilistic limitation of running a 14B model locally, not a bug to "fix" outright.
- **Net worth projections can look extreme**: the growth rate is blended (market performance +
  Jonathan's own contributions, not a pure investment return), so long-horizon projections can produce
  very large, headline-grabbing figures. Caveated in the UI/chat text, but worth remembering when
  reading them.
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

1. **Design and build the expanded subscription audit** — cross-check recurring charges against the
   Personal Budget "Money Out" list in both directions (charges missing from the budget, budget lines
   with no recent matching charge). See "Subscription audit, expanded" under Suggested Features above
   for what's already been discussed; next step is nailing down the "recurring" and match-fuzziness
   definitions with Jonathan before writing code.
2. Resurface the other four Suggested Features ideas if Jonathan asks what's on the plan — none are
   committed to yet.

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

---

## Maintenance convention

At the end of every session, update this file: tick off completed checklist items, add any newly
discovered issues to §7, recompute the progress percentage in §6, refresh §8's priority list, and add
a new dated entry to §9. When Jonathan says "continue with PLAN.md" at the start of a session, read
this file in full before taking any other action.
