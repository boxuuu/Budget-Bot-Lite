from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timedelta

Base = declarative_base()

class HouseholdTransaction(Base):
    """Deliberately a separate table from database.Transaction, not a
    shared table with an account tag - Jonathan's Chase card and the
    household's Santander account must never be mixed. Keeping them in
    different tables makes that structural (nothing outside this module
    even knows this table exists) rather than a matter of remembering an
    account filter in every Dashboard/Chat/Personal Budget query."""
    __tablename__ = 'household_transactions'

    id = Column(Integer, primary_key=True)
    date = Column(String)
    description = Column(String)
    amount = Column(Float)
    category = Column(String, default='Uncategorised')
    month = Column(String)

class HouseholdRecurringChargeDismissal(Base):
    """Same purpose as budget.RecurringChargeDismissal, but a separate
    table so dismissing a merchant on the Household checklist can never
    accidentally suppress it on the Personal one, or vice versa."""
    __tablename__ = 'household_recurring_charge_dismissals'

    id = Column(Integer, primary_key=True)
    merchant = Column(String)
    reason = Column(String)   # 'already_budgeted' or 'not_recurring'
    dismissed_at = Column(DateTime)

DISMISSAL_EXPIRY_DAYS = 180

def get_household_transactions_db():
    engine = create_engine('sqlite:///budget_bot.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def amount_to_float(amount_str):
    cleaned = amount_str.replace('£', '').replace(',', '').strip()
    return float(cleaned)

def save_household_transactions(transactions):
    """Same shape and duplicate-detection logic as database.save_transactions
    - takes the same {'Date', 'Description', 'Amount'} dicts parse_transactions()
    already produces, so the existing (Chase-tuned) PDF parser can be reused
    as a starting point. Santander's statement layout is very likely
    different in some way (date format, column order, multi-line
    descriptions) - this hasn't been tested against a real Santander
    statement yet, so the first real upload may need parser adjustments."""
    db = get_household_transactions_db()
    saved = 0
    skipped = 0

    for t in transactions:
        exists = db.query(HouseholdTransaction).filter_by(
            date=t['Date'],
            description=t['Description'],
            amount=amount_to_float(t['Amount'])
        ).first()

        if not exists:
            parts = t['Date'].split()
            month = f"{parts[1]} {parts[2]}"

            db.add(HouseholdTransaction(
                date=t['Date'],
                description=t['Description'],
                amount=amount_to_float(t['Amount']),
                month=month
            ))
            saved += 1
        else:
            skipped += 1

    db.commit()
    db.close()
    return saved, skipped

def load_all_household_transactions():
    db = get_household_transactions_db()
    transactions = db.query(HouseholdTransaction).all()
    db.close()
    return transactions

def get_household_active_dismissals():
    db = get_household_transactions_db()
    cutoff = datetime.utcnow() - timedelta(days=DISMISSAL_EXPIRY_DAYS)
    rows = db.query(HouseholdRecurringChargeDismissal).filter(
        HouseholdRecurringChargeDismissal.dismissed_at >= cutoff
    ).all()
    result = {r.merchant: {'reason': r.reason, 'dismissed_at': r.dismissed_at} for r in rows}
    db.close()
    return result

def dismiss_household_recurring_charge(merchant, reason):
    db = get_household_transactions_db()
    existing = db.query(HouseholdRecurringChargeDismissal).filter_by(merchant=merchant).first()
    if existing:
        existing.reason = reason
        existing.dismissed_at = datetime.utcnow()
    else:
        db.add(HouseholdRecurringChargeDismissal(merchant=merchant, reason=reason, dismissed_at=datetime.utcnow()))
    db.commit()
    db.close()

def undismiss_household_recurring_charge(merchant):
    db = get_household_transactions_db()
    db.query(HouseholdRecurringChargeDismissal).filter_by(merchant=merchant).delete()
    db.commit()
    db.close()
