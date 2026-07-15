import ollama
import json
import difflib
from database import get_db, Transaction
from categoriser import CATEGORIES
from networth import get_asset_names

def get_spending_context(db):
    transactions = db.query(Transaction).all()
    
    if not transactions:
        return "No transactions in the database yet."
    
    from collections import defaultdict
    by_category = defaultdict(float)
    by_month = defaultdict(float)
    by_month_category = defaultdict(lambda: defaultdict(float))
    unique_merchants = defaultdict(lambda: {'category': '', 'total': 0, 'count': 0})
    
    for t in transactions:
        if t.amount < 0:
            amt = abs(t.amount)
            by_category[t.category] += amt
            by_month[t.month] += amt
            by_month_category[t.month][t.category] += amt
            unique_merchants[t.description]['category'] = t.category
            unique_merchants[t.description]['total'] += amt
            unique_merchants[t.description]['count'] += 1
    
    category_summary = "\n".join([
        f"- {cat}: £{total:.2f}" 
        for cat, total in sorted(by_category.items(), key=lambda x: x[1], reverse=True)
    ])
    
    month_summary = "\n".join([
        f"- {month}: £{total:.2f}" 
        for month, total in sorted(by_month.items())
    ])

    month_category_summary = ""
    for month in sorted(by_month_category.keys()):
        month_category_summary += f"\n{month}:\n"
        for cat, total in sorted(by_month_category[month].items(), key=lambda x: x[1], reverse=True):
            month_category_summary += f"  - {cat}: £{total:.2f}\n"

    merchant_summary = "\n".join([
        f"- {merchant}: {data['category']} (£{data['total']:.2f} total, {data['count']} transactions)"
        for merchant, data in sorted(unique_merchants.items())
    ])
    
    return f"""
TOTAL SPENDING BY CATEGORY (Jan-Jun 2026):
{category_summary}

TOTAL SPENDING BY MONTH:
{month_summary}

SPENDING BY MONTH AND CATEGORY:
{month_category_summary}

ALL MERCHANTS (name: category, total spent, number of transactions):
{merchant_summary}
"""

def get_system_prompt(context):
    return f"""You are Budget Bot, a personal finance assistant for Jonathan based in Manchester, UK.

You have DIRECT ACCESS to all of Jonathan's bank transactions from January to June 2026.
The data is provided below — use it to answer questions accurately and confidently.
Do not say you don't have access to data. All the data you need is right here.

{context}

Available categories:
{chr(10).join(f'- {c}' for c in CATEGORIES)}

You can:
1. Answer questions about spending using the exact figures from the data above
2. Call the update_category tool when Jonathan tells you a merchant's category is wrong
3. Call the update_networth tool when Jonathan tells you a new value for one of his tracked assets

Always use the actual numbers from the data. Be specific, concise and helpful.
Only call a tool when Jonathan states a definite new value or correction, not for hypothetical
questions. If the asset, merchant, or category he means is ambiguous, ask a clarifying question
in plain text instead of guessing and calling the tool with incomplete or uncertain arguments.
"""

def build_tools(asset_names):
    return [
        {
            "type": "function",
            "function": {
                "name": "update_networth",
                "description": (
                    "Record a new value for an existing tracked asset when Jonathan states a "
                    "new balance, e.g. 'my ISA is now £45,000'. Only call this when a definite "
                    "new value is stated, not for questions."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "asset_name": {
                            "type": "string",
                            "description": "The asset being updated",
                            "enum": asset_names
                        },
                        "value": {
                            "type": "number",
                            "description": "The new value in GBP"
                        }
                    },
                    "required": ["asset_name", "value"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "update_category",
                "description": (
                    "Change the spending category for a merchant when Jonathan says a category "
                    "is wrong, e.g. 'change Deliveroo to Eating Out & Takeaway'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "merchant_name": {
                            "type": "string",
                            "description": "Merchant/transaction description to update"
                        },
                        "new_category": {
                            "type": "string",
                            "description": "The correct category",
                            "enum": CATEGORIES
                        }
                    },
                    "required": ["merchant_name", "new_category"]
                }
            }
        }
    ]

def resolve_fuzzy(value, choices, cutoff=0.6):
    """Local models can garble enum strings that contain special characters
    (e.g. '&', parentheses) when returned via tool calls. Never trust a
    tool-call argument that's supposed to be one of a closed set of values -
    always resolve it back to the real string first."""
    if value in choices:
        return value

    matches = difflib.get_close_matches(value, choices, n=1, cutoff=cutoff)
    if matches:
        return matches[0]

    lowered = {c.lower(): c for c in choices}
    matches = difflib.get_close_matches(value.lower(), list(lowered.keys()), n=1, cutoff=cutoff)
    return lowered[matches[0]] if matches else None

def update_category(merchant_name, new_category):
    db = get_db()
    transactions = db.query(Transaction).filter(
        Transaction.description.ilike(f"%{merchant_name}%")
    ).all()
    
    if not transactions:
        db.close()
        return 0
    
    for t in transactions:
        t.category = new_category
    
    db.commit()
    count = len(transactions)
    db.close()
    return count

def chat_with_budget_bot(messages, user_message):
    """Returns {"text": str, "pending_action": None | dict}. A pending_action
    describes an update the model wants to make, for the caller to show as a
    confirmation before anything is actually written to the database -
    nothing here ever writes on its own."""
    db = get_db()
    context = get_spending_context(db)
    db.close()

    system_prompt = get_system_prompt(context)

    # Build message history for Ollama
    ollama_messages = [
        {'role': 'system', 'content': system_prompt}
    ]

    # Add conversation history
    for msg in messages:
        ollama_messages.append({
            'role': msg['role'],
            'content': msg['content']
        })

    # Add the new user message
    ollama_messages.append({
        'role': 'user',
        'content': user_message
    })

    asset_names = get_asset_names()

    response = ollama.chat(
        model='llama3.2',
        messages=ollama_messages,
        tools=build_tools(asset_names)
    )

    tool_calls = response['message'].get('tool_calls')
    if not tool_calls:
        return {"text": response['message']['content'], "pending_action": None}

    call = tool_calls[0]
    name = call['function']['name']
    args = call['function']['arguments']

    if name == 'update_networth':
        resolved_asset = resolve_fuzzy(args.get('asset_name', ''), asset_names)
        try:
            value = float(str(args.get('value', '')).replace('£', '').replace(',', ''))
        except ValueError:
            value = None

        if not resolved_asset or value is None:
            text = (
                f"I couldn't confidently match that to one of your tracked assets: "
                f"{', '.join(asset_names)}. Could you clarify?"
            )
            return {"text": text, "pending_action": None}

        text = f"Update {resolved_asset} to £{value:,.2f}?"
        return {
            "text": text,
            "pending_action": {
                "type": "update_networth",
                "asset_name": resolved_asset,
                "value": value,
                "display": text
            }
        }

    if name == 'update_category':
        merchant_name = args.get('merchant_name', '')
        resolved_category = resolve_fuzzy(args.get('new_category', ''), CATEGORIES)

        db = get_db()
        count = db.query(Transaction).filter(
            Transaction.description.ilike(f"%{merchant_name}%")
        ).count()
        db.close()

        if not resolved_category or count == 0:
            text = f"I couldn't find any transactions matching '{merchant_name}'. Could you clarify the merchant name?"
            return {"text": text, "pending_action": None}

        text = f"Update {count} transaction(s) matching '{merchant_name}' to {resolved_category}?"
        return {
            "text": text,
            "pending_action": {
                "type": "update_category",
                "merchant_name": merchant_name,
                "new_category": resolved_category,
                "count": count,
                "display": text
            }
        }

    return {"text": response['message']['content'], "pending_action": None}