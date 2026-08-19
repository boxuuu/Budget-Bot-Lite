from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class CategoryRule(Base):
    """A merchant -> category override, created automatically whenever a
    correction is made on the Manage Categories page, so a manual fix
    sticks for future statement uploads instead of resetting to
    Uncategorised every time the same merchant reappears. Checked before
    KNOWN_RULES, since a human correction should always win over the
    hardcoded rules. Keyed on the exact (lowercased) merchant description -
    the same granularity the Manage Categories correction already applies
    at - rather than a substring, so correcting one merchant can never
    accidentally reclassify an unrelated one."""
    __tablename__ = 'category_rules'

    merchant = Column(String, primary_key=True)  # lowercased, exact match
    category = Column(String)

class Category(Base):
    """The user-editable list of spending categories offered throughout the
    app (Manage Categories dropdowns, Ollama's prompt, chat's tool schema).
    Seeded from DEFAULT_CATEGORIES on first use, then lives entirely in the
    database - add_category/remove_category let a user extend or trim the
    list from there. sort_order preserves a sensible dropdown order (Salary
    first, Other last) instead of falling back to alphabetical."""
    __tablename__ = 'categories'

    name = Column(String, primary_key=True)
    sort_order = Column(Integer)

def get_categoriser_db():
    engine = create_engine('sqlite:///budget_bot.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def get_user_rule(merchant_name):
    db = get_categoriser_db()
    rule = db.query(CategoryRule).filter_by(merchant=merchant_name.lower()).first()
    db.close()
    return rule.category if rule else None

def save_user_rule(merchant_name, category):
    db = get_categoriser_db()
    key = merchant_name.lower()
    rule = db.query(CategoryRule).filter_by(merchant=key).first()
    if rule:
        rule.category = category
    else:
        db.add(CategoryRule(merchant=key, category=category))
    db.commit()
    db.close()

DEFAULT_CATEGORIES = [
    "Salary",
    "Groceries",
    "Eating Out & Takeaway",
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

# Categories the rest of the app depends on by exact name, not just as a
# label - deleting them wouldn't crash anything, but would silently break
# real features. "Savings & Investments" is matched by exact string in the
# Savings Rate KPI, the Dashboard's trend-chart/top-merchants splits, and
# the Goals page's discretionary-spend calculation (see analytics.py,
# goals.py, app.py) - removable elsewhere, never here.
PROTECTED_CATEGORIES = {"Savings & Investments"}

def get_categories():
    """The current category list, in display order. Seeds the categories
    table from DEFAULT_CATEGORIES the first time this is ever called (a
    fresh database has no rows yet) - after that, the database is the only
    source of truth, so add_category/remove_category changes persist."""
    db = get_categoriser_db()
    if db.query(Category).count() == 0:
        for i, name in enumerate(DEFAULT_CATEGORIES):
            db.add(Category(name=name, sort_order=i))
        db.commit()
    categories = [c.name for c in db.query(Category).order_by(Category.sort_order).all()]
    db.close()
    return categories

def add_category(name):
    """Adds a new category at the end of the list. Returns False (no-op)
    for a blank name or one that already exists (case-sensitive - matching
    Category.name's exact-string usage everywhere else)."""
    name = name.strip()
    if not name:
        return False
    db = get_categoriser_db()
    if db.query(Category).filter_by(name=name).first():
        db.close()
        return False
    next_order = db.query(Category).count()
    db.add(Category(name=name, sort_order=next_order))
    db.commit()
    db.close()
    return True

def remove_category(name):
    """Removes a category from the selectable list. Returns False (no-op)
    for a protected category. Deliberately does NOT touch transactions
    already tagged with this category - they keep showing/filtering
    normally everywhere (categories are read from the data itself, not
    this list), they just can't be re-selected here going forward."""
    if name in PROTECTED_CATEGORIES:
        return False
    db = get_categoriser_db()
    category = db.query(Category).filter_by(name=name).first()
    if category:
        db.delete(category)
        db.commit()
    db.close()
    return True

# Known rules for recognisable UK-wide merchants/brands - applied before
# anything is left Uncategorised for manual review (there's no AI fallback
# in this build). Kept deliberately generic: entries that only made sense
# for one household's own accounts (a salary reference string, a specific
# plumber, a specific council, an internal account nickname) have been
# removed - a new user's manual corrections on the Manage Categories page
# cover those instead, and persist automatically via the CategoryRule table
# above from then on.
KNOWN_RULES = {
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
    "oddy knocky": "Eating Out & Takeaway",
    "kickback": "Eating Out & Takeaway",
    "coffeehit": "Eating Out & Takeaway",
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
    "hospice": "Charity",
    "give-star": "Charity",
    "hsbc": "Insurance & Finance",
    "aviva": "Insurance & Finance",
    "homeprotect": "Insurance & Finance",
    "surewise": "Insurance & Finance",
    "zurich": "Insurance & Finance",
    "tsb": "Insurance & Finance",
    "tv licence": "Bills & Utilities",
    "brsk": "Phone & Internet",
    # Common UK household bill providers
    "octopus": "Bills & Utilities",
    "nationwide b s": "Rent & Housing",
    "united utilities": "Bills & Utilities",
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
    # every branch/location would show up as a distinct "unique merchant"
    # left Uncategorised for the same non-answer.
    "cash withdrawal": "Other",
}

def apply_known_rules(merchant_name):
    merchant_lower = merchant_name.lower()
    for keyword, category in KNOWN_RULES.items():
        if keyword in merchant_lower:
            return category
    return None

# Some banks (Santander) redact a transaction's description down to mostly
# asterisks, but still expose a "Type" column (DD/Card Payment/Cash Back/
# etc.) separately. Type alone can't identify most categories - a Direct
# Debit could be a mortgage, Netflix, or a gym membership - but "Cash Back"
# is a clean exception, same reasoning as the "cash withdrawal" rule above:
# what it was actually spent on is unknowable regardless of merchant text.
TYPE_RULES = {
    'cashback': 'Other',
}

def apply_type_rule(transaction_type):
    if not transaction_type:
        return None
    # Strips spaces/punctuation before matching, so "Cash Back", "CASHBACK"
    # and "Cash-back" all normalize the same way regardless of how a given
    # bank happens to format the value
    normalized = ''.join(ch for ch in transaction_type.lower() if ch.isalnum())
    return TYPE_RULES.get(normalized)

def categorise_all(db_session, Transaction):
    """Categorises every transaction a rule (user-saved or hardcoded)
    matches, and leaves the rest as Uncategorised - there's no AI fallback
    in this build, so an unmatched merchant needs a manual fix on the
    Manage Categories page (which then saves a CategoryRule and covers it
    for good)."""
    uncategorised = db_session.query(Transaction).filter_by(category='Uncategorised').all()

    if not uncategorised:
        return 0, 0

    rules_applied = 0

    # Type-based rule first (e.g. Cash Back -> Other) - per-transaction
    # rather than per-merchant, since it's independent of description
    # entirely. Only ever matches on a model with a transaction_type column
    # (HouseholdTransaction currently) - Transaction has none, so
    # getattr(..., None) makes this a no-op there.
    remaining = []
    for t in uncategorised:
        type_category = apply_type_rule(getattr(t, 'transaction_type', None))
        if type_category:
            t.category = type_category
            rules_applied += 1
            print(f"  [type rule] {t.description[:40]} -> {type_category}")
        else:
            remaining.append(t)

    unique_merchants = list(set(t.description for t in remaining))

    print(f"Categorising {len(unique_merchants)} unique merchants...")

    merchant_map = {}
    for merchant in unique_merchants:
        # A user's own past correction always wins over the hardcoded rules
        category = get_user_rule(merchant) or apply_known_rules(merchant)
        if category:
            merchant_map[merchant] = category
            rules_applied += 1
            print(f"  [rule] {merchant} -> {category}")
        else:
            print(f"  [no rule] {merchant} -> left Uncategorised")

    # Apply to all transactions a rule actually matched
    still_uncategorised = 0
    for t in remaining:
        if t.description in merchant_map:
            t.category = merchant_map[t.description]
        else:
            still_uncategorised += 1

    db_session.commit()
    return rules_applied, still_uncategorised

def recategorise_all(db_session, Transaction):
    # Reset all categories and redo from scratch
    all_transactions = db_session.query(Transaction).all()
    for t in all_transactions:
        t.category = 'Uncategorised'
    db_session.commit()
    return categorise_all(db_session, Transaction)
