# Budget Bot

## What this is
Budget Bot is a personal finance app built in Python/Streamlit for Jonathan Cummins, based in Manchester, UK.
It runs entirely locally on a MacBook Air M3 (24GB RAM) and uses Ollama for local LLM capabilities.
The app parses Chase bank statement PDFs, stores transactions in a local SQLite database, categorises
them using Ollama (Llama 3.2), and displays spending analysis, charts, and a net worth tracker.

## Tech stack
- **Frontend:** Streamlit
- **Database:** SQLite via SQLAlchemy
- **LLM:** Ollama running Llama 3.2 locally, with tool-calling for chat-driven updates
- **Web search:** ddgs (DuckDuckGo) for merchant categorisation context
- **PDF parsing:** PyMuPDF (fitz)
- **Charts:** Plotly
- **Language:** Python 3.9

## Project structure
- `app.py` — main Streamlit app, all pages and navigation
- `database.py` — SQLite models and transaction functions (Transaction model)
- `categoriser.py` — merchant categorisation logic using known rules + Ollama fallback (with ddgs web search context)
- `networth.py` — net worth/asset tracking models and functions (AssetValue model)
- `chat.py` — Ollama chat interface with spending context and tool-calling for category/net worth updates
- `budget_bot.db` — SQLite database (do not delete)
- `start.sh` — shell script to launch the app

## Pages (sidebar navigation)
1. **Dashboard** — spending metrics, category bar chart, monthly trend line, top 10 transactions
2. **Net Worth** — asset tracking with time-series graphs, imported from Worth It app export
3. **Chat** — natural language interface powered by Ollama for questions, category fixes, and net worth updates (proposed changes require a Confirm/Cancel click before writing to the database)
4. **Upload Statement** — PDF upload and transaction parsing for Chase bank statements
5. **View Transactions** — full transaction table with month filter and categorisation buttons
6. **Manage Categories** — review and correct merchant categories

## Database models
### Transaction (database.py)
- id, date (String), description (String), amount (Float), category (String), month (String)

### AssetValue (networth.py)
- id, asset_name (String), tag (String), value (Float), recorded_at (DateTime)

## Categories used
Groceries, Eating Out & Takeaway, Coffee & Beans, Shopping, Transport, Health & Fitness,
Subscriptions, Phone & Internet, Insurance & Finance, Savings & Investments, Charity,
Bills & Utilities, Rent & Housing, Other

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