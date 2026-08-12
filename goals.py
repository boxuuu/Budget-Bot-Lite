from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

Base = declarative_base()

class Goal(Base):
    """Append-only, like AssetValue - editing a goal never overwrites the
    current row, it inserts a new one with a future effective_month (see
    next_effective_month()). Past months keep being judged against whatever
    target was actually active at the time, so history never changes
    retroactively - and since calculate_streak() only counts months governed
    by the CURRENT (most recently set) row, every edit effectively resets
    progress toward the goal, without needing a separate "reset" flag.

    goal_type is 'savings' (hit = actual >= target) or 'spend' (hit = actual
    <= target). effective_month is a 'Mon YYYY' string, same format as
    Transaction.month, so it sorts with analytics.month_sort_key."""
    __tablename__ = 'goals'

    id = Column(Integer, primary_key=True)
    goal_type = Column(String)
    target_amount = Column(Float)
    effective_month = Column(String)
    created_at = Column(DateTime)

# Categories treated as fixed, non-negotiable costs and excluded from the
# spend-ceiling goal specifically - deliberately narrower than
# analytics.get_monthly_spend (used by the Dashboard's KPI/trend chart),
# which stays gross/unmodified by design since it's meant to show true
# total spend. Confirmed with Jonathan 2026-08-12: the spend goal should
# reflect discretionary spending he actually has control over month to
# month, not fixed bills he can't meaningfully flex.
NON_DISCRETIONARY_CATEGORIES = ['Rent & Housing', 'Bills & Utilities', 'Insurance & Finance', 'Phone & Internet']

def get_discretionary_monthly_spend(transactions):
    """{month: total_spend} - same gross-outflow-excluding-Savings&Investments
    definition as analytics.get_monthly_spend, but also excludes
    NON_DISCRETIONARY_CATEGORIES. Used only by the Goals page's spend
    ceiling and its Dashboard tile."""
    from collections import defaultdict
    by_month = defaultdict(float)
    for t in transactions:
        if t.amount < 0 and t.category != 'Savings & Investments' and t.category not in NON_DISCRETIONARY_CATEGORIES:
            by_month[t.month] += abs(t.amount)
    return dict(by_month)

def get_goals_db():
    engine = create_engine('sqlite:///budget_bot.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def get_all_goals(goal_type):
    """Every goal of this type ever set, oldest first."""
    db = get_goals_db()
    goals = db.query(Goal).filter_by(goal_type=goal_type).order_by(Goal.effective_month).all()
    db.close()
    return goals

def get_current_goal(goal_type):
    """The most recently SET goal of this type - not necessarily active yet,
    if it was set this month (it takes effect next month). None if no goal
    of this type has ever been set."""
    goals = get_all_goals(goal_type)
    return goals[-1] if goals else None

def set_goal(goal_type, target_amount, effective_month):
    db = get_goals_db()
    db.add(Goal(
        goal_type=goal_type,
        target_amount=target_amount,
        effective_month=effective_month,
        created_at=datetime.utcnow()
    ))
    db.commit()
    db.close()

def next_effective_month():
    """The earliest month a newly-set goal can govern - always the calendar
    month after the current one, so editing a goal can never change the
    judgement on the month you're currently in (or any past month)."""
    today = datetime.now()
    next_month = datetime(today.year + 1, 1, 1) if today.month == 12 else datetime(today.year, today.month + 1, 1)
    return next_month.strftime('%b %Y')

def get_active_goal_for_month(goal_type, month_label, all_goals=None):
    """The goal that actually governed a given month: the most recent row of
    this type with effective_month <= month_label. None if no goal of this
    type existed yet by that month."""
    from analytics import month_sort_key
    goals = all_goals if all_goals is not None else get_all_goals(goal_type)
    eligible = [g for g in goals if month_sort_key(g.effective_month) <= month_sort_key(month_label)]
    if not eligible:
        return None
    return max(eligible, key=lambda g: month_sort_key(g.effective_month))

def calculate_streak(goal_type, monthly_actuals):
    """monthly_actuals: {month_label: value} for COMPLETE months only - the
    caller excludes the current in-progress month, since judging a
    still-running month wouldn't be a fair final verdict.

    Walks backward from the most recent complete month, counting consecutive
    hits. Hit direction depends on goal_type: 'savings' needs actual >=
    target, 'spend' needs actual <= target. Only months governed by the
    CURRENT goal row count - the moment a month is found that predates the
    current row's effective_month, or was governed by an older/different
    row, the streak stops. This is what makes editing a goal "reset" it:
    right after an edit, the current row's effective_month is always next
    month, so zero complete months yet fall under it and the streak reads 0
    until real months start passing under the new target."""
    all_goals = get_all_goals(goal_type)
    if not all_goals:
        return 0

    from analytics import month_sort_key
    current_goal = all_goals[-1]
    months_sorted = sorted(monthly_actuals.keys(), key=month_sort_key, reverse=True)

    streak = 0
    for month_label in months_sorted:
        if month_sort_key(month_label) < month_sort_key(current_goal.effective_month):
            break
        active = get_active_goal_for_month(goal_type, month_label, all_goals)
        if active is None or active.id != current_goal.id:
            break
        actual = monthly_actuals[month_label]
        hit = actual >= active.target_amount if goal_type == 'savings' else actual <= active.target_amount
        if not hit:
            break
        streak += 1
    return streak
