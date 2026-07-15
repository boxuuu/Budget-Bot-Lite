import ollama
import json
import difflib
from datetime import datetime
from database import get_db, Transaction
from categoriser import CATEGORIES
from networth import get_asset_names, get_asset_name_tags, project_net_worth
from analytics import month_sort_key, calculate_savings_rate

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
        for month, total in sorted(by_month.items(), key=lambda x: month_sort_key(x[0]))
    ])

    month_category_summary = ""
    for month in sorted(by_month_category.keys(), key=month_sort_key):
        month_category_summary += f"\n{month}:\n"
        for cat, total in sorted(by_month_category[month].items(), key=lambda x: x[1], reverse=True):
            month_category_summary += f"  - {cat}: £{total:.2f}\n"

    merchant_summary = "\n".join([
        f"- {merchant}: {data['category']} (£{data['total']:.2f} total, {data['count']} transactions)"
        for merchant, data in sorted(unique_merchants.items())
    ])

    months_sorted = sorted(by_month.keys(), key=month_sort_key)
    avg_monthly_spend = sum(by_month.values()) / len(months_sorted) if months_sorted else 0

    savings_info = calculate_savings_rate(transactions)
    avg_savings = savings_info['avg_savings']
    min_savings = savings_info['min_savings']
    max_savings = savings_info['max_savings']
    typical_monthly_income = savings_info['typical_monthly_income']
    savings_rate = savings_info['savings_rate']
    bonus_month = savings_info['bonus_month']

    savings_by_month_summary = "\n".join([
        f"- {month}: £{amt:.2f}" for month, amt in savings_info['savings_by_month'].items()
    ])

    # Month-over-month change per category, computed here (not left to the
    # model) so it can reference exact percentages rather than guessing
    momentum_summary = "Not enough months of data yet for a month-over-month comparison."
    if len(months_sorted) >= 2:
        prev_month, latest_month = months_sorted[-2], months_sorted[-1]
        lines = []
        all_cats = set(by_month_category[prev_month]) | set(by_month_category[latest_month])
        for cat in sorted(all_cats):
            prev_amt = by_month_category[prev_month].get(cat, 0.0)
            latest_amt = by_month_category[latest_month].get(cat, 0.0)
            if prev_amt:
                pct = (latest_amt - prev_amt) / prev_amt * 100
                lines.append(f"- {cat}: £{prev_amt:.2f} -> £{latest_amt:.2f} ({pct:+.1f}%)")
            else:
                lines.append(f"- {cat}: £{prev_amt:.2f} -> £{latest_amt:.2f} (new spending this month)")
        momentum_summary = f"{prev_month} -> {latest_month}:\n" + "\n".join(lines)

    income_by_month_summary = "\n".join([
        f"- {month}: £{amt:.2f}" + (" (includes annual bonus)" if month == bonus_month else "")
        for month, amt in sorted(savings_info['income_by_month'].items(), key=lambda x: month_sort_key(x[0]))
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

AVERAGE MONTHLY SPEND (across {len(months_sorted)} months of data): £{avg_monthly_spend:.2f}

SAVINGS & INVESTMENTS SPEND BY MONTH (average £{avg_savings:.2f}/month, ranging from £{min_savings:.2f} to £{max_savings:.2f} - highly volatile, treat the average as a rough figure only):
{savings_by_month_summary}

MONTH-OVER-MONTH CATEGORY CHANGE (most recent two months):
{momentum_summary}

SALARY BY MONTH (identified via "From B E" transactions):
{income_by_month_summary}

TYPICAL MONTHLY SALARY (median, robust to the bonus month): £{typical_monthly_income:.2f}

CURRENT SAVINGS RATE: averaging £{avg_savings:.2f}/month into Savings & Investments, which is {savings_rate:.1f}% of typical monthly salary.
"""

def get_system_prompt(context):
    return f"""You are Budget Bot, a personal finance assistant for Jonathan based in Manchester, UK.
Always respond in English, regardless of the wording or complexity of the question.

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
4. Call the project_net_worth tool when Jonathan asks a forward-looking question about his net
   worth (e.g. "what will I have in 10 years?") - this returns a direct estimate, there's nothing
   to confirm, so just relay the answer. If he gives a target age instead of a number of years
   (e.g. "I'm 37, I want to retire at 55"), work out years yourself (55 - 37 = 18) and pass that.
   If he asks about a subset of his assets (e.g. "my combined pensions and ISA"), pass those exact
   asset names in the optional asset_names list so only that subset gets projected - don't decline
   or say you're missing data just because he asked for a subset rather than everything.
5. Give spending and savings suggestions using the average monthly spend, the Savings &
   Investments figures, the month-over-month category changes, and the savings rate provided above
6. Call the get_merchant_spending tool whenever Jonathan asks how much he's spent at a specific
   merchant, or how many times, or since when. ALWAYS use this tool for that rather than reading
   the ALL MERCHANTS list above - that list is long and it's easy to misread or miscount from it.
   The tool gives an exact, reliable answer; your own reading of the list does not.

Always use the actual numbers from the data. Be specific, concise and helpful.
Only call a tool when Jonathan states a definite new value or correction, not for hypothetical
questions. If the asset, merchant, or category he means is ambiguous, ask a clarifying question
in plain text instead of guessing and calling the tool with incomplete or uncertain arguments.

Jonathan's salary is identified via transactions matching "From B E" in the data above - use the
TYPICAL MONTHLY SALARY figure (not the bonus month) as his regular income for any savings-rate or
budgeting discussion. Do not invent, guess, or estimate any income figure beyond what's explicitly
shown above.
"""

def build_tools(asset_names, asset_tags=None):
    # Group assets by tag (e.g. "Pension") so the model can reliably match
    # plural/category phrasing like "my pensions" to the right asset names,
    # rather than guessing from the names alone
    asset_tags = asset_tags or {}
    by_tag = {}
    for asset_name, tag in asset_tags.items():
        by_tag.setdefault(tag, []).append(asset_name)
    asset_categories_text = "; ".join(
        f"{tag}: {', '.join(names)}" for tag, names in sorted(by_tag.items())
    )

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
        },
        {
            "type": "function",
            "function": {
                "name": "project_net_worth",
                "description": (
                    "Estimate what Jonathan's net worth will be N years from now, based on his "
                    "historical growth rate. This is a read-only calculation - it never changes "
                    "any data. Call this when Jonathan asks a forward-looking question like 'what "
                    "will my net worth be in 10 years?' or 'how much will I have by 2035?'. If he "
                    "gives an age instead of a year count, work out the number of years yourself."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "years": {
                            "type": "integer",
                            "description": "Number of years into the future to project, e.g. 10"
                        },
                        "asset_names": {
                            "type": "array",
                            "items": {"type": "string", "enum": asset_names},
                            "description": (
                                "Optional - only include this if Jonathan asked about a specific "
                                "subset of assets (e.g. 'my pensions and ISA'), not his whole net "
                                "worth. Omit entirely to project everything. Asset categories for "
                                "reference, so plural/category phrasing like 'my pensions' maps to "
                                f"every matching asset, not just one: {asset_categories_text}"
                            )
                        }
                    },
                    "required": ["years"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_merchant_spending",
                "description": (
                    "Look up exactly how much Jonathan has spent at a specific merchant, e.g. "
                    "'how much have I spent on Amazon?' or 'what's my total at Tesco?'. This is a "
                    "read-only database lookup, not a guess from memory - ALWAYS call this for any "
                    "question asking for a specific merchant's total, count, or spending history, "
                    "rather than trying to recall the figure from the merchant list above, which is "
                    "long and easy to misread."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "merchant_name": {
                            "type": "string",
                            "description": "The merchant name to search for, e.g. 'Amazon'"
                        }
                    },
                    "required": ["merchant_name"]
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

def looks_malformed(text):
    """Heuristic check for a bad generation from the local model: dropping
    into a non-English script (seen with Thai, mid-conversation, despite the
    system prompt saying English-only), or leaking raw tool-call-looking
    JSON fragments into the visible text instead of using a real tool call.
    Both have been observed on elliptical follow-up questions."""
    if not text or not text.strip():
        return True
    # 0x24F is the end of Latin Extended-B - covers English plus accented
    # Western European characters and the £ sign. Greek, Cyrillic, Hebrew,
    # Arabic, Thai and CJK all start well above this, so this catches a
    # script switch without false-flagging normal English text.
    non_latin = sum(1 for c in text if ord(c) > 0x24F)
    if non_latin > len(text) * 0.1:
        return True
    suspicious_markers = ['"function_name"', '"arguments":', 'function_name":']
    return any(marker in text for marker in suspicious_markers)

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
    asset_tags = get_asset_name_tags()

    response = ollama.chat(
        model='qwen2.5:14b',
        messages=ollama_messages,
        tools=build_tools(asset_names, asset_tags)
    )

    tool_calls = response['message'].get('tool_calls')
    if not tool_calls:
        content = response['message']['content']
        if looks_malformed(content):
            # Bad generation (wrong language, or leaked tool-call-looking
            # text) - silently retry once before showing anything to Jonathan
            retry_response = ollama.chat(
                model='qwen2.5:14b',
                messages=ollama_messages,
                tools=build_tools(asset_names, asset_tags)
            )
            retry_tool_calls = retry_response['message'].get('tool_calls')
            if retry_tool_calls:
                tool_calls = retry_tool_calls
                response = retry_response
            else:
                content = retry_response['message']['content']
                if looks_malformed(content):
                    content = "Sorry, I had trouble putting together a clear answer to that - could you rephrase the question?"
                return {"text": content, "pending_action": None}
        else:
            return {"text": content, "pending_action": None}

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

    if name == 'project_net_worth':
        # Local models can send years as "10", 10.0, etc. - be tolerant like
        # the other branches are with loosely-typed tool arguments.
        try:
            years = int(float(args.get('years', 0)))
        except (TypeError, ValueError):
            years = 0

        if years <= 0:
            return {"text": "How many years ahead would you like me to project?", "pending_action": None}

        # Optional subset (e.g. "just my pensions and ISA") - resolve each
        # name through the same fuzzy-match safety net as the other tools,
        # since these can arrive garbled too. Unmatched names are dropped
        # rather than failing the whole request.
        raw_subset = args.get('asset_names') or []
        resolved_subset = []
        for raw_name in raw_subset:
            resolved = resolve_fuzzy(raw_name, asset_names)
            if resolved and resolved not in resolved_subset:
                resolved_subset.append(resolved)

        subset = resolved_subset or None
        result = project_net_worth(years=years, asset_names=subset)
        scope_text = f"your {', '.join(subset)}" if subset else "your total net worth"

        if not result['ok']:
            if result['reason'] == 'no_data':
                text = f"I don't have any history recorded for {scope_text}, so I can't project anything."
            else:
                text = (
                    f"I don't have enough history for {scope_text} yet to project forward confidently "
                    f"(only {result['span_days']} days recorded). I'd want at least a few months "
                    f"of history before estimating a growth rate."
                )
            return {"text": text, "pending_action": None}

        text = (
            f"Based on {scope_text}'s history since {result['anchor_date']:%b %Y} "
            f"(£{result['anchor_value']:,.0f} now, growing at roughly {result['rate']*100:.1f}%/year), "
            f"a rough projection puts you at about £{result['projected_value']:,.0f} in {years} years.\n\n"
            f"Worth flagging: that growth rate is blended - it includes both market performance "
            f"and whatever you've personally added to your accounts over that period, not a pure "
            f"investment return. It's a straight-line projection from the past, not a guarantee - "
            f"markets and your own saving habits can both change."
        )
        return {"text": text, "pending_action": None}

    if name == 'get_merchant_spending':
        merchant_name = args.get('merchant_name', '')
        db = get_db()
        matches = db.query(Transaction).filter(
            Transaction.description.ilike(f"%{merchant_name}%")
        ).all()
        db.close()

        if not matches:
            text = f"I couldn't find any transactions matching '{merchant_name}'."
            return {"text": text, "pending_action": None}

        spending_txns = [t for t in matches if t.amount < 0]
        refund_txns = [t for t in matches if t.amount > 0]
        total_spent = sum(abs(t.amount) for t in spending_txns)
        total_refunds = sum(t.amount for t in refund_txns)
        dates = sorted(datetime.strptime(t.date, '%d %b %Y') for t in matches)

        text = (
            f"You've spent £{total_spent:,.2f} across {len(spending_txns)} transaction(s) matching "
            f"'{merchant_name}', from {dates[0]:%d %b %Y} to {dates[-1]:%d %b %Y}."
        )
        if total_refunds > 0:
            text += (
                f" There's also £{total_refunds:,.2f} in credits/refunds under the same name "
                f"across {len(refund_txns)} transaction(s) - not included in the spend total above, "
                f"worth checking those are genuine refunds and not something odd."
            )
        return {"text": text, "pending_action": None}

    return {"text": response['message']['content'], "pending_action": None}