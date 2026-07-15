from collections import defaultdict
from datetime import datetime

def month_sort_key(month_label):
    """Transaction.month is a string like 'Apr 2026' - sorting it directly
    puts months in alphabetical order (Apr, Feb, Jan...), not chronological.
    Parse it into a real date so 'most recent month' actually means that."""
    return datetime.strptime(month_label, '%b %Y')

def calculate_savings_rate(transactions):
    """Computes salary/savings-rate figures from a list of Transaction
    objects. Salary is identified via "From B E" transactions (confirmed as
    Jonathan's salary); one month per year typically includes his annual
    bonus, so the median across months (robust to that outlier) is used as
    the typical monthly figure. Savings is the "Savings & Investments"
    spending category.

    Returns a dict: income_by_month, bonus_month, typical_monthly_income,
    savings_by_month, avg_savings, min_savings, max_savings, savings_rate.
    All numeric values are 0 and dicts empty if there's no spending data."""
    by_month_category = defaultdict(lambda: defaultdict(float))
    income_by_month = defaultdict(float)

    for t in transactions:
        if t.amount < 0:
            by_month_category[t.month][t.category] += abs(t.amount)
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
