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
| 7. Data Accuracy Refinements | Complete (git commit pending) |
| 8. Budget Targets & Comparisons | Not Started |

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
- [ ] Commit today's changes to git (`analytics.py`, `categoriser.py`, `chat.py` are currently
      modified but uncommitted)

### Stage 8 — Budget Targets & Comparisons (not started)
- [ ] Budget targets vs actuals on the Dashboard
- [ ] Month-on-month comparison charts

## 6. Progress

**~92% complete** (35 of 38 checklist items done). The only fully unstarted stage is budget
targets/comparisons (Stage 8); everything else is built and verified. The one open item elsewhere is
committing today's uncommitted changes (Stage 7).

## 7. Known Issues

- **Chat model reliability**: the local `qwen2.5:14b` model occasionally misfires a tool call on an
  ordinary question (~1 in 5 in testing) or produces malformed output (wrong script, leaked JSON) on
  elliptical follow-ups. Mitigated with a detect-and-retry guard, not eliminated — this is a
  probabilistic limitation of running a 14B model locally, not a bug to "fix" outright.
- **Net worth projections can look extreme**: the growth rate is blended (market performance +
  Jonathan's own contributions, not a pure investment return), so long-horizon projections can produce
  very large, headline-grabbing figures. Caveated in the UI/chat text, but worth remembering when
  reading them.
- **Cosmetic currency formatting**: Dashboard's Savings Rate tile still renders negative values as
  `£-1,461/mo` instead of `-£1,461/mo` — fixed in `chat.py` during the Stage 7 refinement but
  deliberately not touched in `app.py` (out of scope for that change). Trivial one-line fix whenever
  it's worth doing.
- **Uncommitted changes**: `analytics.py`, `categoriser.py`, and `chat.py` have real, verified changes
  from today (2026-07-16) not yet committed to git.
- **PDF parser scope**: tuned specifically for Chase UK statement format — pre-existing, documented
  limitation, not something to fix unless a new statement format needs supporting.
- **Savings & Investments netting scope**: deliberately does *not* apply to Dashboard's general
  spending views (Total Spent, pie chart, trend line, top merchants) — only to the Savings Rate figure
  specifically. This was a considered design decision (applying it more broadly breaks the pie chart,
  which can't render a negative slice, and would make "Total Spent" misleadingly drop), not an
  oversight — but worth knowing if the numbers ever look inconsistent between the Dashboard and Chat.

## 8. Next Actions

1. **Commit and push today's Stage 7 changes** (Salary category, savings-pot netting) — currently
   sitting uncommitted in the working tree.
2. **Build budget targets vs actuals on the Dashboard** (Stage 8) — compare Personal/Household Budget
   figures against real transaction spend per category.
3. **Build month-on-month comparison charts** (Stage 8).
4. *(Minor)* Fix the cosmetic negative-currency formatting on the Dashboard's Savings Rate tile to
   match the fix already made in `chat.py`.
5. *(Deferred decision, revisit if it comes up)* Decide whether Dashboard's general spending views
   should ever reflect savings-pot netting, now that the Chat/Savings Rate figure does.

## 9. Session Log

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

---

## Maintenance convention

At the end of every session, update this file: tick off completed checklist items, add any newly
discovered issues to §7, recompute the progress percentage in §6, refresh §8's priority list, and add
a new dated entry to §9. When Jonathan says "continue with PLAN.md" at the start of a session, read
this file in full before taking any other action.
