from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone

Base = declarative_base()

class AssetValue(Base):
    __tablename__ = 'asset_values'
    
    id = Column(Integer, primary_key=True)
    asset_name = Column(String)
    tag = Column(String)
    value = Column(Float)
    recorded_at = Column(DateTime)

def get_networth_db():
    engine = create_engine('sqlite:///budget_bot.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def import_from_worthit(filepath):
    import openpyxl
    import ast

    wb = openpyxl.load_workbook(filepath, read_only=True)
    db = get_networth_db()
    imported = 0
    skipped_sheets = []

    # Skip the overview sheet
    asset_sheets = [s for s in wb.sheetnames if s != 'Overview']

    for sheet_name in asset_sheets:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))

        # Parse key fields from sheet
        data = {}
        for row in rows:
            if row[0] in ('name', 'tag', 'is_archived', 'values', 'values_market'):
                data[row[0]] = row[1]

        # Skip archived assets
        if data.get('is_archived') == 'true':
            skipped_sheets.append(data.get('name', sheet_name))
            continue

        asset_name = data.get('name', sheet_name)
        tag = data.get('tag', 'Other')
        # Clean tag of emojis for cleaner display
        tag = tag.encode('ascii', 'ignore').decode('ascii').strip()
        if not tag:
            tag = 'Other'

        # Parse values - combine manual and market values
        all_values = {}
        for key in ('values', 'values_market'):
            raw = data.get(key, '{}')
            if raw and raw != '{}':
                try:
                    parsed = ast.literal_eval(str(raw))
                    all_values.update(parsed)
                except:
                    pass

        # Convert timestamps and save
        for ts_ms, value in all_values.items():
            if not value:
                continue
            recorded_at = datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc).replace(tzinfo=None)

            # Check for duplicate
            exists = db.query(AssetValue).filter_by(
                asset_name=asset_name,
                recorded_at=recorded_at
            ).first()

            if not exists:
                db.add(AssetValue(
                    asset_name=asset_name,
                    tag=tag,
                    value=float(value),
                    recorded_at=recorded_at
                ))
                imported += 1

    db.commit()
    db.close()
    return imported, skipped_sheets

def get_all_asset_history():
    db = get_networth_db()
    records = db.query(AssetValue).order_by(AssetValue.recorded_at).all()
    db.close()
    return records

def get_asset_names():
    db = get_networth_db()
    names = db.query(AssetValue.asset_name).distinct().all()
    db.close()
    return [n[0] for n in names]

def update_asset_value(asset_name, value, tag=None):
    db = get_networth_db()

    # Get tag from existing records if not provided
    if not tag:
        existing = db.query(AssetValue).filter_by(
            asset_name=asset_name
        ).first()
        tag = existing.tag if existing else 'Other'

    db.add(AssetValue(
        asset_name=asset_name,
        tag=tag,
        value=float(value),
        recorded_at=datetime.utcnow()
    ))
    db.commit()
    db.close()

def delete_asset(asset_name):
    db = get_networth_db()
    db.query(AssetValue).filter_by(asset_name=asset_name).delete()
    db.commit()
    db.close()

def delete_asset_value(record_id):
    db = get_networth_db()
    db.query(AssetValue).filter_by(id=record_id).delete()
    db.commit()
    db.close()

def get_asset_tags():
    db = get_networth_db()
    tags = db.query(AssetValue.tag).distinct().all()
    db.close()
    return sorted(t[0] for t in tags if t[0])