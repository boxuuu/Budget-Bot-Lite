# Budget Bot

> See `PLAN.md` for current progress, known issues, and next actions — read it before starting work
> on this project, and update it at the end of any session that changes the codebase.

## What this is
Budget Bot is a personal finance app built in Python/Streamlit for Jonathan Cummins, based in Manchester, UK.
It runs entirely locally on a MacBook Air M3 (24GB RAM) and uses Ollama for local LLM capabilities.
The app parses Chase bank statement PDFs, stores transactions in a local SQLite database, categorises
them using Ollama (Llama 3.2), and displays spending analysis, charts, and a net worth tracker.

## Tech stack
- **Frontend:** Streamlit
- **Database:** SQLite via SQLAlchemy
- **LLM:** Ollama running two local models for two different jobs — `llama3.2` (3B, fast) for batch
  merchant categorisation, `qwen2.5:14b` (slower, better reasoning) for the chat assistant's
  tool-calling and advice
- **Web search:** ddgs (DuckDuckGo) for merchant categorisation context
- **PDF parsing:** PyMuPDF (fitz)
- **Charts:** Plotly
- **Language:** Python 3.9

## Project structure
- `app.py` — main Streamlit app, all pages and navigation
- `database.py` — SQLite models and transaction functions (Transaction model)
- `categoriser.py` — merchant categorisation logic using known rules + Ollama fallback (with ddgs web search context)
- `networth.py` — net worth/asset tracking models and functions (AssetValue model)
- `budget.py` — personal and household budget models and functions (PersonalBudgetItem, HouseholdBudgetItem, BudgetSetting)
- `analytics.py` — shared cross-page calculations: chronological month-sorting, savings-rate
  calculation (net of savings-pot transfers), used by both the Dashboard and Chat
- `chat.py` — Ollama chat interface with spending context and tool-calling for category/net worth updates
- `.streamlit/config.toml` — theme config (brand accent colour only, so the native light/dark/system
  toggle keeps working)
- `budget_bot.db` — SQLite database (do not delete)
- `start.sh` — shell script to launch the app

## Pages (sidebar navigation)
1. **Dashboard** — KPI row (Net Worth, Total Spent, Monthly Average, Savings Rate), category pie
   chart (top 6 categories + "Other categories"), Top 10 Merchants table, monthly spending trend chart
2. **Net Worth** — asset tracking with time-series graphs, imported from Worth It app export
3. **Personal Budget** — live-editable Money In/Money Out grids, manually-entered total income (minus salary sacrifice), and computed income-minus-expenses/money-per-week figures
4. **Household Budget** — live-editable bills grid (service, provider, renewal date, amount) with a computed total, and an editable percentage split between the two people in the household
5. **Upload Statement** — PDF upload and transaction parsing for Chase bank statements
6. **View Transactions** — full transaction table with month, merchant, and category filters and categorisation buttons
7. **Manage Categories** — review and correct merchant categories

There is no standalone Chat page — the chat interface (natural language questions, category
fixes, and net worth updates, with a Confirm/Cancel click required before writing to the database)
lives permanently in the sidebar below the page navigation, rendered on every page regardless of
which one is selected. It uses Streamlit's inline `st.chat_input` positioning (only pins to the
bottom of the viewport when placed directly in the main body) with a fixed-height `st.container`
for scrollable message history.

## Database models
### Transaction (database.py)
- id, date (String), description (String), amount (Float), category (String), month (String)

### AssetValue (networth.py)
- id, asset_name (String), tag (String), value (Float), recorded_at (DateTime)

### PersonalBudgetItem (budget.py)
- id, section (String — 'Money In' or 'Money Out'), name (String), amount (Float)
- No history — editing overwrites the current figure (unlike AssetValue). "Money In" items are
  reference-only and not summed by any formula; the actual income figure used in calculations is
  a separate manually-entered setting (see BudgetSetting) since Jonathan doesn't have a full
  salary-sacrifice breakdown to derive it from.

### HouseholdBudgetItem (budget.py)
- id, service (String), provider (String), renewal_date (String, informational only), amount (Float)
- Amount is displayed as "New House" in the UI (a permanent label, not a house-move leftover) but
  kept as a generic column name in the schema.

### BudgetSetting (budget.py)
- key (String, primary key), value (String, cast to float at the call site)
- Generic key/value table. Two keys in use: `personal_total_income` (manual override for Personal
  Budget) and `household_split_percent` (editable % split between the two people in the household).

## Categories used
Salary, Groceries, Eating Out & Takeaway, Coffee & Beans, Shopping, Transport, Health & Fitness,
Subscriptions, Phone & Internet, Insurance & Finance, Savings & Investments, Charity,
Bills & Utilities, Rent & Housing, Other

Salary is income only (identified via "From B E" transactions) and is never included in spending
totals. Savings & Investments figures used for the Savings Rate calculation (Dashboard KPI and Chat)
are net of transfers to/from Jonathan's named savings pots (Fun Money, Round up, Emergency Fund,
Wedding, Overflow) — money moving back out of a pot reduces the figure rather than being invisible.
This netting applies only to the Savings Rate calculation, not to the Dashboard's general spending
views (pie chart, Total Spent, trend chart), which stay gross/unmodified by design.

## Coding preferences
- No emojis anywhere in the UI
- Keep code clean and well commented
- Streamlit pages use elif page == "Page Name": pattern
- All pages must have unique keys on any selectbox or widget to avoid duplicate element errors
- Virtual environment is at ~/budget-bot/venv — always assume it is active
- To run the app: streamlit run app.py
- Ollama must be running separately for LLM features to work

## Current data
- 935 transactions loaded from January to June 2026 (Chase bank statements)
- Net worth data imported from Worth It app export going back to 2024
- Assets tracked: Private Pension (AJ Bell), Emergency Fund, Barclays Shares (Equate),
  Coinbase, Stocks & Shares ISA (AJ Bell), Workplace Pension (L&G)

## Known issues to be aware of
- Duplicate widget key errors: always add unique key= arguments to all Streamlit widgets
- Ollama context window: do not send all 935 raw transactions to Ollama at once,
  use summaries instead
- PDF parser is tuned for Chase UK statement format specifically

## What to build next
- Budget targets vs actuals on the Dashboard
- Month-on-month comparison charts