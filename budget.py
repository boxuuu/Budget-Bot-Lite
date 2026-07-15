from sqlalchemy import create_engine, Column, String, Float, Integer
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class PersonalBudgetItem(Base):
    __tablename__ = 'personal_budget_items'

    id = Column(Integer, primary_key=True)
    section = Column(String)   # 'Money In' or 'Money Out'
    name = Column(String)
    amount = Column(Float)

class HouseholdBudgetItem(Base):
    __tablename__ = 'household_budget_items'

    id = Column(Integer, primary_key=True)
    service = Column(String)
    provider = Column(String)
    renewal_date = Column(String)   # free text, informational only
    amount = Column(Float)          # shown as "New House" in the UI - column itself stays generic

class BudgetSetting(Base):
    __tablename__ = 'budget_settings'

    key = Column(String, primary_key=True)
    value = Column(String)

def get_budget_db():
    engine = create_engine('sqlite:///budget_bot.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def get_personal_items(section):
    db = get_budget_db()
    items = db.query(PersonalBudgetItem).filter_by(section=section).all()
    result = [{'name': i.name, 'amount': i.amount} for i in items]
    db.close()
    return result

def replace_personal_section(section, items):
    """items: list of {'name': str, 'amount': float}. Wipes and reinserts
    every row for this section only - the other section is untouched.
    Runs as one transaction so a mid-write failure rolls back rather than
    leaving the section half-deleted."""
    db = get_budget_db()
    try:
        db.query(PersonalBudgetItem).filter_by(section=section).delete()
        for item in items:
            db.add(PersonalBudgetItem(
                section=section,
                name=item['name'],
                amount=float(item['amount'])
            ))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def get_personal_total_expenses():
    db = get_budget_db()
    items = db.query(PersonalBudgetItem).filter_by(section='Money Out').all()
    total = sum(i.amount for i in items)
    db.close()
    return total

def get_household_items():
    db = get_budget_db()
    items = db.query(HouseholdBudgetItem).all()
    result = [{
        'service': i.service,
        'provider': i.provider,
        'renewal_date': i.renewal_date,
        'amount': i.amount
    } for i in items]
    db.close()
    return result

def replace_household_items(items):
    """items: list of {'service','provider','renewal_date','amount'}. Wipes
    and reinserts the whole table. Runs as one transaction so a mid-write
    failure rolls back rather than leaving the table half-deleted."""
    db = get_budget_db()
    try:
        db.query(HouseholdBudgetItem).delete()
        for item in items:
            db.add(HouseholdBudgetItem(
                service=item.get('service', ''),
                provider=item.get('provider', ''),
                renewal_date=item.get('renewal_date', ''),
                amount=float(item['amount'])
            ))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def get_household_total():
    db = get_budget_db()
    items = db.query(HouseholdBudgetItem).all()
    total = sum(i.amount for i in items)
    db.close()
    return total

def get_setting(key, default=None):
    db = get_budget_db()
    setting = db.query(BudgetSetting).filter_by(key=key).first()
    value = setting.value if setting else default
    db.close()
    return value

def set_setting(key, value):
    db = get_budget_db()
    setting = db.query(BudgetSetting).filter_by(key=key).first()
    if setting:
        setting.value = str(value)
    else:
        db.add(BudgetSetting(key=key, value=str(value)))
    db.commit()
    db.close()

def get_personal_total_income():
    return float(get_setting('personal_total_income', 0))

def set_personal_total_income(value):
    set_setting('personal_total_income', value)

def get_household_split_percent():
    return float(get_setting('household_split_percent', 60))

def set_household_split_percent(value):
    set_setting('household_split_percent', value)
