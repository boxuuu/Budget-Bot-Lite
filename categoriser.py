import ollama
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

CATEGORIES = [
    "Salary",
    "Groceries",
    "Eating Out & Takeaway",
    "Coffee & Beans",
    "Shopping",
    "Transport",
    "Health & Fitness",
    "Subscriptions",
    "Phone & Internet",
    "Insurance & Finance",
    "Savings & Investments",
    "Charity",
    "Bills & Utilities",
    "Rent & Housing",
    "Other"
]

# Known rules - these are applied before Ollama is even consulted
# Add to this list as you correct things on the Manage Categories page
KNOWN_RULES = {
    # Income, not spend - checked first since it's conceptually distinct
    # from everything else in this dict
    "from b e": "Salary",
    "tesco": "Groceries",
    "aldi": "Groceries",
    "asda": "Groceries",
    "morrisons": "Groceries",
    "sainsbury": "Groceries",
    "creamline": "Groceries",
    "one stop": "Groceries",
    "deliveroo": "Eating Out & Takeaway",
    "uber eats": "Eating Out & Takeaway",
    "letsorderfood": "Eating Out & Takeaway",
    "foodhub": "Eating Out & Takeaway",
    "mcdonald": "Eating Out & Takeaway",
    "greggs": "Eating Out & Takeaway",
    "domino": "Eating Out & Takeaway",
    "nando": "Eating Out & Takeaway",
    "kfc": "Eating Out & Takeaway",
    "oddy knocky": "Coffee & Beans",
    "kickback": "Coffee & Beans",
    "coffeehit": "Coffee & Beans",
    "two wombats": "Eating Out & Takeaway",
    "station south": "Eating Out & Takeaway",
    "pod point": "Transport",
    "uber": "Transport",
    "excel parking": "Transport",
    "smart parking": "Transport",
    "tesla": "Transport",
    "vodafone": "Phone & Internet",
    "plusnet": "Phone & Internet",
    "apple": "Subscriptions",
    "applecare": "Subscriptions",
    "patreon": "Subscriptions",
    "steam": "Subscriptions",
    "real debrid": "Subscriptions",
    "eneba": "Subscriptions",
    "microsoft": "Subscriptions",
    "itv": "Subscriptions",
    "paypal": "Subscriptions",
    "aj bell": "Savings & Investments",
    "a j bell": "Savings & Investments",
    "sippdeal": "Savings & Investments",
    "sprive": "Savings & Investments",
    "jetts": "Health & Fitness",
    "hivejiujitsu": "Health & Fitness",
    "empire grappling": "Health & Fitness",
    "hospice": "Charity",
    "give-star": "Charity",
    "hsbc": "Insurance & Finance",
    "aviva": "Insurance & Finance",
    "homeprotect": "Insurance & Finance",
    "surewise": "Insurance & Finance",
    "house acc": "Rent & Housing",
    "wedding": "Savings & Investments",
    "emergency fund": "Savings & Investments",
    "fun money": "Savings & Investments",
    "overflow": "Savings & Investments",
    "round up": "Savings & Investments",
    "holidays": "Savings & Investments",
    "amazon": "Shopping",
    "ebay": "Shopping",
    "etsy": "Shopping",
    "dunelm": "Shopping",
    "b & q": "Shopping",
    "wickes": "Shopping",
    "b&m": "Shopping",
    "argos": "Shopping",
    "adidas": "Shopping",
    "allsaints": "Shopping",
    "vinted": "Shopping",
    "hmv": "Shopping",
    "ao.com": "Shopping",
    "flexispot": "Shopping",
    # What the cash was actually spent on is unknowable from the
    # transaction alone - "Other" is the honest answer here, not a
    # categoriser failure. Description includes the withdrawal location
    # (e.g. "Cash withdrawal, E, LEIGH, WN7 1QX"), so without this rule
    # every branch/location produces a distinct "unique merchant" that
    # burns a separate Ollama + web search call for the same non-answer.
    "cash withdrawal": "Other",
}

def apply_known_rules(merchant_name):
    merchant_lower = merchant_name.lower()
    for keyword, category in KNOWN_RULES.items():
        if keyword in merchant_lower:
            return category
    return None

def get_merchant_context(merchant_name, all_transactions):
    matching = [t for t in all_transactions if t.description == merchant_name]
    if not matching:
        return ""
    
    amounts = [abs(t.amount) for t in matching]
    avg_amount = sum(amounts) / len(amounts)
    frequency = len(matching)
    
    return f"Appears {frequency} times, average amount £{avg_amount:.2f}"

def search_merchant_web(merchant_name):
    """Look up a merchant online to help the categoriser figure out what
    kind of business it is. Returns "" (same as no context) on any failure -
    the caller doesn't need to know whether the search worked.

    Queries avoid the words "UK company", which reliably rank Companies
    House registration pages first - those only confirm a business exists,
    never what it actually does (a pub named "Overdraught" turned up nothing
    but Companies House boilerplate under the old query). Leading with a
    Manchester-anchored query instead favours local review/listing results.
    Any Companies House snippet that still slips through is filtered out."""
    from ddgs import DDGS

    queries = [
        f"{merchant_name} Manchester",
        f"{merchant_name} what kind of business",
    ]

    for query in queries:
        try:
            results = DDGS().text(query, max_results=3)
            useful = [
                r.get('body', '') for r in results
                if 'companies house' not in r.get('body', '').lower()
            ]
            snippets = " ".join(useful[:2])
            if snippets:
                print(f"  [web] {merchant_name} -> found")
                return snippets[:400].replace('\n', ' ')
        except Exception:
            continue

    print(f"  [web] {merchant_name} -> none")
    return ""

def categorise_with_ollama(merchant_name, context, web_context=""):
    prompt = f"""You are a UK personal finance assistant categorising bank transactions for someone based in Manchester.

Categorise this merchant into exactly one of these categories:
{chr(10).join(f'- {c}' for c in CATEGORIES)}

Merchant: {merchant_name}
Context: {context}
Web search info: {web_context}

Some guidance:
- Coffee shops and specialty coffee roasters = Coffee & Beans
- Restaurants, pubs, bars, fast food, takeaway apps = Eating Out & Takeaway
- Supermarkets and food delivery services = Groceries
- Gym memberships, martial arts, sport = Health & Fitness
- Streaming, gaming, digital subscriptions = Subscriptions
- Clothing, electronics, home goods = Shopping
- Pension, ISA, savings transfers = Savings & Investments
- If it looks like a pub or bar based on the name = Eating Out & Takeaway
- If unsure between Shopping and Other, pick Shopping for retail names

Reply with only the category name, nothing else.
"""
    
    response = ollama.chat(
        model='llama3.2',
        messages=[{'role': 'user', 'content': prompt}]
    )
    
    result = response['message']['content'].strip()
    
    if result in CATEGORIES:
        return result
    return "Other"

def categorise_all(db_session, Transaction):
    all_transactions = db_session.query(Transaction).all()
    uncategorised = [t for t in all_transactions if t.category == 'Uncategorised']
    
    if not uncategorised:
        return 0, 0
    
    unique_merchants = list(set(t.description for t in uncategorised))
    rules_applied = 0
    ollama_used = 0
    
    print(f"Categorising {len(unique_merchants)} unique merchants...")
    
    merchant_map = {}
    for merchant in unique_merchants:
        # Try known rules first
        category = apply_known_rules(merchant)
        if category:
            merchant_map[merchant] = category
            rules_applied += 1
            print(f"  [rule] {merchant} -> {category}")
        else:
            # Fall back to Ollama, with web search context to help it figure
            # out what kind of business an unfamiliar merchant actually is
            context = get_merchant_context(merchant, all_transactions)
            web_context = search_merchant_web(merchant)
            category = categorise_with_ollama(merchant, context, web_context)
            merchant_map[merchant] = category
            ollama_used += 1
            print(f"  [ollama] {merchant} -> {category}")
    
    # Apply to all transactions
    for t in uncategorised:
        t.category = merchant_map[t.description]
    
    db_session.commit()
    return rules_applied, ollama_used

def recategorise_all(db_session, Transaction):
    # Reset all categories and redo from scratch
    all_transactions = db_session.query(Transaction).all()
    for t in all_transactions:
        t.category = 'Uncategorised'
    db_session.commit()
    return categorise_all(db_session, Transaction)