# Budget Bot

## What this is
This is the **lite** edition of Budget Bot, a personal finance app built in Python/Streamlit. It's a
fork of a private build that adds local Ollama-based AI (merchant categorisation fallback and a chat
assistant) — this edition deliberately has none of that, so it can be shared and run by anyone
without needing a local LLM set up. It runs entirely locally, with your data staying in a local
SQLite database on your own machine. The app parses bank statement CSV exports from two separate
accounts — a personal card and a household joint account, kept in completely separate database
tables so household data never affects personal figures — stores transactions in a local SQLite
database, categorises them via a rules list plus your own saved corrections, and displays spending
analysis, charts, and a net worth tracker.

## Tech stack
- **Frontend:** Streamlit
- **Database:** SQLite via SQLAlchemy
- **CSV parsing:** Python's built-in `csv` module, via a profile-driven engine (see `csv_import.py`)
- **Charts:** Plotly
- **Language:** Python 3.9

## Project structure
- `app.py` — main Streamlit app, all pages and navigation
- `database.py` — SQLite models and transaction functions (Transaction model — your personal
  Chase transactions only)
- `household_transactions.py` — a completely separate table/pipeline for the household's joint
  Santander account (HouseholdTransaction, HouseholdRecurringChargeDismissal models) — deliberately
  isolated from `database.py` so it's structurally impossible for household data to leak into the
  Dashboard or Personal Budget, which only ever query `database.Transaction`
- `categoriser.py` — merchant categorisation logic, checked in order: a user's own past correction
  (`CategoryRule` table, exact merchant match), then hardcoded `KNOWN_RULES` (substring match). No AI
  fallback in this edition — anything neither matches is left `Uncategorised` for a manual fix on the
  Manage Categories page, which then saves a `CategoryRule` so it's covered for good.
  `categorise_all`/`recategorise_all` take the Transaction model class as a parameter, so the same
  logic works for both `database.Transaction` and `household_transactions.HouseholdTransaction`
- `networth.py` — net worth/asset tracking models and functions (AssetValue model)
- `budget.py` — personal and household budget models and functions (PersonalBudgetItem, HouseholdBudgetItem, BudgetSetting)
- `analytics.py` — shared cross-page calculations: chronological month-sorting, savings-rate
  calculation, recurring-charge detection, used by the Dashboard, Personal Budget, and Household
  Budget (works on either Transaction table, since it only relies on shared attribute names —
  date/description/amount/category/month)
- `goals.py` — savings/spend-ceiling goals with streaks (Goal model, append-only like AssetValue - a
  new target always takes effect next month, never retroactively, and any edit resets its streak)
- `csv_import.py` — bank-agnostic CSV statement parsing: a `BankCsvProfile` dataclass (delimiter,
  column names, date format) plus one shared `parse_bank_csv()` engine, so a new bank is a new
  profile rather than a new parser. `CHASE` and `SANTANDER` profiles are the two currently defined
- `.streamlit/config.toml` — theme config (brand accent colour only, so the native light/dark/system
  toggle keeps working)
- `budget_bot.db` — SQLite database (do not delete)
- `start.sh` — shell script to launch the app

## Pages (sidebar navigation)
1. **Dashboard** — KPI row (Net Worth, Total Spent, Monthly Average, Savings Rate — shown as a
   percentage with the £/mo as a secondary delta), category pie chart and monthly Spending & Savings
   trend chart (both with independent All/1yr/YTD/6mo/1mo time filters, matching the Net Worth page's
   pattern), Top 10 Merchants table
2. **Net Worth** — asset tracking with time-series graphs, imported from Worth It app export, a
   per-asset Growth % column on the main Assets list (colour-coded, follows the page's time filter)
3. **Personal Budget** — live-editable Money In/Money Out grids, manually-entered total income (minus
   salary sacrifice), computed income-minus-expenses/money-per-week figures, a real "Actual monthly
   spend" figure from transactions (not just the manual budget total), and a Recurring Charges
   checklist (merchants paid ≥2 of the last 3 months, with Add to budget / dismiss actions — dismissals
   expire after 6 months rather than hiding a merchant forever)
4. **Household Budget** — live-editable bills grid (service, provider, renewal date, amount) with a
   computed total and an editable % split between two editable-name household members (no names
   hardcoded in the UI), and the same Actual-spend/Recurring-Charges pattern as Personal Budget but
   sourced from the separate Santander `HouseholdTransaction` table. Categorisation itself (bulk +
   manual correction) lives on the Manage Categories page's Household tab, not here
5. **Goals** — a Savings Goal and a Discretionary Spend Ceiling, each with a streak (consecutive
   complete months hit), a "so far this month" progress figure, and a "Set a new target" form
   pre-filled with a suggested value from recent history. A new target only ever takes effect next
   month, and any edit resets the streak. Also has a compact tile on the Dashboard
6. **Upload Statement** — two side-by-side upload boxes: Personal (Chase, feeds the Dashboard/
   Personal Budget) and Household (Santander, feeds only the Household Budget page). Both accept a
   bank CSV export, parsed via `csv_import.py`'s profile-driven `parse_bank_csv()` engine (see Tech
   stack/Project structure above) rather than a bank-specific parser
7. **View Transactions** — full transaction table with month, merchant, and category filters and
   categorisation buttons (personal Chase transactions only)
8. **Manage Categories** — Personal/Household tabs (same pattern as View Transactions), each with its
   own bulk categorise/re-categorise actions and a merchant table whose Category column is directly
   editable (a dropdown per row via `st.data_editor`), with a "Save changes" button that applies every
   edited row at once - a correction always persists via `CategoryRule`, regardless of which tab it's
   made from

There is no Chat/AI assistant in this edition — see "What this is" above.

## Database models
### Transaction (database.py)
- id, date (String), description (String), amount (Float), category (String), month (String)
- Your personal Chase card only.

### HouseholdTransaction (household_transactions.py)
- Same shape as Transaction (id, date, description, amount, category, month), but a completely
  separate table for the joint Santander account. Nothing outside `household_transactions.py` and
  the Household Budget page queries this table.

### CategoryRule (categoriser.py)
- merchant (String, primary key, lowercased exact match), category (String)
- Created/overwritten automatically whenever a category edit is saved on the Manage Categories
  page, so a manual correction survives future statement uploads and full re-categorisations
  instead of resetting to `Uncategorised` every time. Checked before `KNOWN_RULES`, so a human
  correction always wins over the hardcoded rules. Shared across `database.Transaction` and
  `household_transactions.HouseholdTransaction`, same as `KNOWN_RULES`.

### HouseholdRecurringChargeDismissal (household_transactions.py)
- id, merchant (String), reason (String — 'already_budgeted' or 'not_recurring'), dismissed_at (DateTime)
- Mirrors `budget.RecurringChargeDismissal` but kept in a separate table so dismissing a merchant on
  the Household Recurring Charges checklist can never suppress it on the Personal one. Dismissals
  expire after 6 months (`DISMISSAL_EXPIRY_DAYS`) rather than lasting forever.

### AssetValue (networth.py)
- id, asset_name (String), tag (String), value (Float), recorded_at (DateTime)

### PersonalBudgetItem (budget.py)
- id, section (String — 'Money In' or 'Money Out'), name (String), amount (Float)
- No history — editing overwrites the current figure (unlike AssetValue). "Money In" items are
  reference-only and not summed by any formula; the actual income figure used in calculations is
  a separate manually-entered setting (see BudgetSetting), for anyone who doesn't have a full
  salary-sacrifice breakdown to derive it from automatically.

### HouseholdBudgetItem (budget.py)
- id, service (String), provider (String), renewal_date (String, informational only), amount (Float)
- Amount is displayed as "New House" in the UI (a permanent label, not a house-move leftover) but
  kept as a generic column name in the schema.

### BudgetSetting (budget.py)
- key (String, primary key), value (String, cast to float at the call site)
- Generic key/value table. Keys in use: `personal_total_income` (manual override for Personal
  Budget), `household_split_percent` (editable % split between the two people in the household), and
  `household_person1_name`/`household_person2_name` (editable display names for the Household Budget
  Split card, default "Person 1"/"Person 2" — no names hardcoded in the UI).

### RecurringChargeDismissal (budget.py)
- id, merchant (String), reason (String — 'already_budgeted' or 'not_recurring'), dismissed_at (DateTime)
- Backs Personal Budget's Recurring Charges checklist. Same shape/purpose as
  `household_transactions.HouseholdRecurringChargeDismissal`, kept as a separate table for the same
  reason (so Personal and Household dismissals never cross-contaminate).

### Goal (goals.py)
- id, goal_type (String — 'savings' or 'spend'), target_amount (Float), effective_month (String,
  'Mon YYYY'), created_at (DateTime)
- Append-only, like AssetValue — editing a goal never overwrites the current row, it inserts a new
  one with a future effective_month (always "next calendar month" — see `next_effective_month()`),
  so past months keep being judged by whatever target actually governed them at the time. Streaks
  (`calculate_streak()`) only count months governed by the CURRENT (most recently set) row, which is
  what makes any edit reset progress toward the goal.

## Categories used
User-editable via a `Category` table (`categoriser.py`), managed from the Manage Categories page's
"Manage category list" expander (`get_categories`/`add_category`/`remove_category`) rather than a
hardcoded list. Seeded on first use from `DEFAULT_CATEGORIES`: Salary, Groceries, Eating Out &
Takeaway, Shopping, Transport, Health & Fitness, Subscriptions, Phone & Internet, Insurance &
Finance, Savings & Investments, Charity, Bills & Utilities, Rent & Housing, Other. "Coffee & Beans"
was folded into Eating Out & Takeaway (2026-08-19) — too narrow a default, and its only three
`KNOWN_RULES` entries were hyper-local Manchester coffee shops, not generic merchants. "Savings &
Investments" is in `PROTECTED_CATEGORIES` and can't be removed via the UI, since the Savings Rate
KPI, the Dashboard's trend-chart/top-merchants splits, and the Goals page's discretionary-spend
calculation all match it by exact string, not by list membership — deleting it wouldn't crash those
features, just silently break them.

Salary is income only and is never included in spending totals. `analytics.py`'s salary detection is
still hardcoded to one specific payer string (`"From B E"`) inherited from the private build - it
won't match a different user's payslip description, so the Savings Rate KPI shows "N/A" until this
is genericised or a user manually categorises one salary transaction as `Salary` (which then
persists via `CategoryRule` for future statements, same as any other correction). Savings &
Investments figures used for the Savings Rate calculation (Dashboard KPI and the trend chart's
Savings line) are net of transfers to/from a set of named savings pots, also still hardcoded from the
private build (Round up, Emergency Fund, Wedding, Overflow) — money moving back out of a pot reduces
the figure rather than being invisible. Fun Money is excluded entirely, in both directions, since it
behaves as a discretionary spending buffer rather than genuine savings, not a store of value. This
treatment applies only to the Savings Rate/trend-line calculation, not to the Dashboard's general
spending views (pie chart, Total Spent, top merchants), which stay gross/unmodified by design. Both
the salary string and the pot names are candidates for making user-configurable later.

## Coding preferences
- No emojis anywhere in the UI
- Keep code clean and well commented
- Streamlit pages use elif page == "Page Name": pattern
- All pages must have unique keys on any selectbox or widget to avoid duplicate element errors
- Virtual environment is at ~/budget-bot/venv — always assume it is active
- To run the app: streamlit run app.py

## Known issues to be aware of
- Duplicate widget key errors: always add unique key= arguments to all Streamlit widgets
- CSV statement parsing (`csv_import.py`) is profile-driven, not bank-specific code — the `CHASE`
  and `SANTANDER` profiles just describe each bank's delimiter/column names/date format. A new
  bank's export is a new `BankCsvProfile`, not a new parser function, as long as it fits the "one
  header row, one row per transaction, either a single signed amount column or separate debit/credit
  columns" shape most UK bank CSV exports follow