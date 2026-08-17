from collections import defaultdict
from datetime import datetime
from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class SavingsBufferMerchant(Base):
    """A user-tagged merchant within the Savings & Investments category that
    behaves as a discretionary spending buffer rather than genuine savings -
    the data-driven equivalent of the private build's hardcoded "Fun Money"
    exclusion below, built from whatever a user's own transactions actually
    contain rather than one fixed name. Excluded entirely from the Savings
    Rate/trend-line calculation in both directions, same treatment as
    EXCLUDED_FROM_SAVINGS. Toggled from the Dashboard."""
    __tablename__ = 'savings_buffer_merchants'

    merchant = Column(String, primary_key=True)  # lowercased, exact match

def get_analytics_db():
    engine = create_engine('sqlite:///budget_bot.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def get_savings_buffer_merchants():
    db = get_analytics_db()
    merchants = {m.merchant for m in db.query(SavingsBufferMerchant).all()}
    db.close()
    return merchants

def set_savings_buffer_merchant(merchant_name, is_buffer):
    db = get_analytics_db()
    key = merchant_name.lower()
    existing = db.query(SavingsBufferMerchant).filter_by(merchant=key).first()
    if is_buffer and not existing:
        db.add(SavingsBufferMerchant(merchant=key))
    elif not is_buffer and existing:
        db.delete(existing)
    db.commit()
    db.close()

def month_sort_key(month_label):
    """Transaction.month is a string like 'Apr 2026' - sorting it directly
    puts months in alphabetical order (Apr, Feb, Jan...), not chronological.
    Parse it into a real date so 'most recent month' actually means that."""
    return datetime.strptime(month_label, '%b %Y')

def get_upload_checklist(existing_months, start_month="Jan 2026"):
    """List of (month_label, uploaded) tuples from start_month through the
    current month inclusive, e.g. [('Jan 2026', True), ('Feb 2026', False), ...].
    The end of the range is always "today's month", recomputed on every call -
    not stored - so the checklist grows by itself over time and a month is
    never dropped once it appears, even if it's still missing a statement."""
    cursor = month_sort_key(start_month)
    current = datetime.now().replace(day=1)
    checklist = []
    while cursor <= current:
        label = cursor.strftime('%b %Y')
        checklist.append((label, label in existing_months))
        cursor = datetime(cursor.year + 1, 1, 1) if cursor.month == 12 else datetime(cursor.year, cursor.month + 1, 1)
    return checklist

# Jonathan's named savings pots - money going TO these is a real saving,
# money coming FROM them back to the main account is money he already
# owned returning, not new income or new spending. Scoped explicitly to
# these 4 (rather than derived from KNOWN_RULES) so a one-directional
# Savings & Investments item like a pension contribution is never
# accidentally netted against nothing.
SAVINGS_POT_NAMES = ['round up', 'emergency fund', 'wedding', 'overflow']

# Fun Money behaves as a discretionary spending buffer, not real savings -
# large sums move in and a similarly large (often larger) sum moves back
# out within a month or two for actual spending. Excluded from the savings
# total in BOTH directions: a contribution isn't durable saving if it's
# earmarked to be spent, and a withdrawal isn't "un-saving" if the money
# was never really saved long-term. Confirmed with Jonathan 2026-07-17
# after finding it was the sole reason an otherwise strongly-positive
# Savings Rate (£2.6k-£8.7k/month of real pension/ISA/wedding/round-up
# saving) was showing negative - swamped by £3.9k-£11.8k/month of Fun
# Money churn that isn't really savings at all.
EXCLUDED_FROM_SAVINGS = ['fun money']

def is_savings_transfer(description):
    return any(pot in description.lower() for pot in SAVINGS_POT_NAMES)

def is_excluded_from_savings(description, buffer_merchants=None):
    if buffer_merchants and description.lower() in buffer_merchants:
        return True
    return any(name in description.lower() for name in EXCLUDED_FROM_SAVINGS)

def format_gbp(amount, decimals=2):
    """£123.45 for positive/zero, -£123.45 (not £-123.45) for negative -
    needed since Savings & Investments figures can be net-negative."""
    return f"-£{abs(amount):,.{decimals}f}" if amount < 0 else f"£{amount:,.{decimals}f}"

def net_spend_amount(amount, description, buffer_merchants=None):
    """How much a transaction contributes to a spend/category total: 0 for
    anything matching EXCLUDED_FROM_SAVINGS or a user-tagged
    SavingsBufferMerchant (buffer_merchants, see is_excluded_from_savings);
    the full amount for a real outflow; for money returning from a named
    savings pot (positive amount, matches SAVINGS_POT_NAMES) it nets
    NEGATIVELY, since it's money already owned coming back, not new
    spending or income. Everything else contributes 0."""
    if is_excluded_from_savings(description, buffer_merchants):
        return 0
    if amount < 0:
        return abs(amount)
    if amount > 0 and is_savings_transfer(description):
        return -amount
    return 0

def calculate_savings_rate(transactions):
    """Computes salary/savings-rate figures from a list of Transaction
    objects. Salary is identified via "From B E" transactions; one month
    per year typically includes an annual bonus, so the median across
    months (robust to that outlier) is used as the typical monthly figure.
    Savings is the "Savings & Investments" category, netted via
    net_spend_amount() so money moving back out of a named savings pot
    reduces the figure rather than being invisible - this can legitimately
    make a month's (or the overall) savings figure negative when
    withdrawals outweigh contributions.

    Returns a dict: income_by_month, bonus_month, typical_monthly_income,
    savings_by_month, avg_savings, min_savings, max_savings, savings_rate.
    All numeric values are 0 and dicts empty if there's no spending data."""
    buffer_merchants = get_savings_buffer_merchants()
    by_month_category = defaultdict(lambda: defaultdict(float))
    income_by_month = defaultdict(float)

    for t in transactions:
        net = net_spend_amount(t.amount, t.description, buffer_merchants)
        if net:
            by_month_category[t.month][t.category] += net
        if t.amount > 0 and t.description.lower().startswith('from b e'):
            income_by_month[t.month] += t.amount

    months_sorted = sorted(by_month_category.keys(), key=month_sort_key)

    savings_category = "Savings & Investments"
    savings_by_month = {m: by_month_category[m].get(savings_category, 0.0) for m in months_sorted}
    savings_values = list(savings_by_month.values())
    avg_savings = sum(savings_values) / len(savings_values) if savings_values else 0
    min_savings = min(savings_values) if savings_values else 0
    max_savings = max(savings_values) if savings_values else 0

    bonus_month = max(income_by_month, key=income_by_month.get) if income_by_month else None
    income_values = sorted(income_by_month.values())
    typical_monthly_income = income_values[len(income_values) // 2] if income_values else 0

    savings_rate = (avg_savings / typical_monthly_income * 100) if typical_monthly_income else 0

    return {
        'income_by_month': dict(income_by_month),
        'bonus_month': bonus_month,
        'typical_monthly_income': typical_monthly_income,
        'savings_by_month': savings_by_month,
        'avg_savings': avg_savings,
        'min_savings': min_savings,
        'max_savings': max_savings,
        'savings_rate': savings_rate,
    }

def get_monthly_spend(transactions):
    """{month: total_spend} - gross outflow, excluding Savings & Investments
    (saved, not spent), same definition used everywhere else "spend" is
    shown (Dashboard trend chart's "Spending" line, calculate_avg_monthly_
    spend below). Used by the Goals page for its spend-goal streak and
    suggested-target calculations, which need a per-month breakdown rather
    than one overall average."""
    by_month = defaultdict(float)
    for t in transactions:
        if t.amount < 0 and t.category != 'Savings & Investments':
            by_month[t.month] += abs(t.amount)
    return dict(by_month)

def calculate_avg_monthly_spend(transactions):
    """Real average monthly outflow: gross spend, excluding Savings &
    Investments (saved, not spent) - same definition as the Dashboard
    trend chart's "Spending" line. Salary needs no explicit exclusion since
    it's income only and never has a negative amount. 0 if there's no
    spending data."""
    by_month = get_monthly_spend(transactions)
    return sum(by_month.values()) / len(by_month) if by_month else 0

def get_recurring_charges(transactions, min_months=2, window_months=3):
    """Merchants with a real outflow (excluding Savings & Investments) in
    at least `min_months` of the most recent `window_months` months of
    data - a simple, robust definition of "recurring" that tolerates a
    subscription's amount or exact day shifting slightly, unlike matching
    on exact amount. Used to surface bills/subscriptions that may be
    missing from the Personal Budget's Money Out list. Returns a list of
    {merchant, category, months_seen, avg_amount} dicts, sorted by
    avg_amount descending."""
    months_sorted = sorted({t.month for t in transactions}, key=month_sort_key)
    recent_months = set(months_sorted[-window_months:])

    by_merchant = defaultdict(lambda: {'category': '', 'months': set(), 'amounts': []})
    for t in transactions:
        if t.amount < 0 and t.category != 'Savings & Investments' and t.month in recent_months:
            entry = by_merchant[t.description]
            entry['category'] = t.category
            entry['months'].add(t.month)
            entry['amounts'].append(abs(t.amount))

    recurring = [
        {
            'merchant': merchant,
            'category': data['category'],
            'months_seen': len(data['months']),
            'avg_amount': sum(data['amounts']) / len(data['amounts']),
        }
        for merchant, data in by_merchant.items()
        if len(data['months']) >= min_months
    ]
    return sorted(recurring, key=lambda x: x['avg_amount'], reverse=True)
