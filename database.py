from sqlalchemy import create_engine, Column, String, Float, Integer
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    date = Column(String)
    description = Column(String)
    amount = Column(Float)
    category = Column(String, default='Uncategorised')
    month = Column(String)

def get_db():
    engine = create_engine('sqlite:///budget_bot.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def amount_to_float(amount_str):
    cleaned = amount_str.replace('£', '').replace(',', '').strip()
    return float(cleaned)

def save_transactions(transactions):
    db = get_db()
    saved = 0
    skipped = 0
    
    for t in transactions:
        exists = db.query(Transaction).filter_by(
            date=t['Date'],
            description=t['Description'],
            amount=amount_to_float(t['Amount'])
        ).first()
        
        if not exists:
            parts = t['Date'].split()
            month = f"{parts[1]} {parts[2]}"
            
            new_transaction = Transaction(
                date=t['Date'],
                description=t['Description'],
                amount=amount_to_float(t['Amount']),
                month=month
            )
            db.add(new_transaction)
            saved += 1
        else:
            skipped += 1
    
    db.commit()
    db.close()
    return saved, skipped

def load_all_transactions():
    db = get_db()
    transactions = db.query(Transaction).all()
    db.close()
    return transactions

def get_months():
    db = get_db()
    months = db.query(Transaction.month).distinct().all()
    db.close()
    return [m[0] for m in months]