# Budget Bot Lite

A personal finance app that runs entirely on your own machine. It parses your bank statement CSV
exports, categorises transactions (using a rules list plus corrections you make yourself — no AI, no
cloud), and gives you a spending dashboard, a net worth tracker, and live-editable personal and
household budgets. Your data stays in a local SQLite database on your computer — nothing is sent
anywhere.

This is the **lite** edition: a fork of a private build that adds local AI (Ollama) for smarter
categorisation and a chat assistant. Lite leaves both of those out, so anyone can run it without
setting up a local LLM.

## Requirements

- Python 3.9+
- A bank statement CSV export to import (supports Chase and Santander UK exports out of the box —
  see `csv_import.py` if you want to add another bank's format)

## Setup

```bash
git clone <this repo's URL>
cd budget-bot-lite

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

## Running

```bash
./start.sh
```

or directly:

```bash
source venv/bin/activate
streamlit run app.py
```

Streamlit will open the app in your browser (usually `http://localhost:8501`). On first run the
database is empty — head to **Upload Statement** to import your first CSV export.

## Notes

- `budget_bot.db` is your local database — back it up if you want to keep your history safe, and
  don't delete it.
- Personal and household transactions are kept in completely separate tables, so household data
  never affects your personal figures (and vice versa).
- See `claude.md` for a full breakdown of the app's structure, pages, and data model if you're
  extending it yourself.
