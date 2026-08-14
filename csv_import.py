import csv
import html
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BankCsvProfile:
    """Describes one bank's CSV export shape - delimiter, column names, and
    date format - so a single generic engine (parse_bank_csv) can parse any
    bank without bank-specific parsing code. Adding a new bank later is a
    new profile, not a new parser. Amount is expressed either as one signed
    column (amount_column) or as separate debit/credit columns - the two
    shapes seen across UK bank CSV exports so far."""
    name: str
    delimiter: str
    date_column: str
    date_format: str
    description_column: str
    amount_column: str = None
    debit_column: str = None
    credit_column: str = None
    type_column: str = None  # optional - e.g. "DD"/"Card Payment"/"Cash Back",
                              # useful when the description itself is redacted


CHASE = BankCsvProfile(
    name="Chase",
    delimiter=",",
    date_column="Date",
    date_format="%d %B %Y",
    description_column="Transaction Description",
    amount_column="Amount",
)

SANTANDER = BankCsvProfile(
    name="Santander",
    delimiter=";",
    date_column="Date",
    date_format="%d/%m/%Y",
    description_column="Merchant/Description",
    amount_column="Debit/Credit",
    type_column="Type",
)


def decode_csv_bytes(raw_bytes):
    """Bank CSV exports aren't reliably UTF-8 - a Windows-originated export
    commonly uses cp1252, where a currency symbol like £ is a single byte
    (0xA3) that isn't valid UTF-8 on its own and raises UnicodeDecodeError.
    Tries UTF-8 first (utf-8-sig also transparently strips a BOM, common
    from Excel-saved exports), then cp1252, then latin-1 as a last resort -
    latin-1 maps every byte value to a character, so it's guaranteed to
    succeed even if some stranger encoding slips through."""
    for encoding in ('utf-8-sig', 'cp1252', 'latin-1'):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue

def _parse_amount(raw):
    """'-1,150.00' / '-£142.03' / '+£4.51' -> signed float. Stripping both
    the £ sign and thousands-separator commas covers every bank shape seen
    so far without needing per-bank amount parsing."""
    return float(raw.replace('£', '').replace(',', '').strip())


def parse_bank_csv(file_content, profile):
    """Parses raw CSV text (already decoded) into the same
    [{'Date': 'DD Mon YYYY', 'Description': str, 'Amount': '<sign>£X.XX'}, ...]
    shape the old PDF parsers produced - so everything downstream
    (save_transactions, save_household_transactions, duplicate detection,
    month derivation) needs zero changes. Driven entirely by `profile`, no
    bank-specific code. Returns [] if the expected header row can't be found."""
    rows = list(csv.reader(file_content.splitlines(), delimiter=profile.delimiter))

    header_idx = next((i for i, row in enumerate(rows) if profile.date_column in row), None)
    if header_idx is None:
        return []

    header = rows[header_idx]
    try:
        date_idx = header.index(profile.date_column)
        desc_idx = header.index(profile.description_column)
        amount_idx = header.index(profile.amount_column) if profile.amount_column else None
        debit_idx = header.index(profile.debit_column) if profile.debit_column else None
        credit_idx = header.index(profile.credit_column) if profile.credit_column else None
        # Optional and not in required_indices below - a row missing it
        # shouldn't be skipped, since the type is supplementary context, not
        # something the row's validity depends on
        type_idx = header.index(profile.type_column) if profile.type_column else None
    except ValueError:
        return []

    required_indices = [i for i in (date_idx, desc_idx, amount_idx, debit_idx, credit_idx) if i is not None]

    transactions = []
    for row in rows[header_idx + 1:]:
        if len(row) <= max(required_indices):
            continue

        # Any row that isn't a real transaction (title rows, footers, blank
        # lines) simply won't parse as a date here - that's what filters
        # them out, not a bank-specific "skip N rows" rule.
        try:
            date = datetime.strptime(row[date_idx].strip(), profile.date_format)
        except ValueError:
            continue

        if profile.amount_column:
            try:
                amount = _parse_amount(row[amount_idx])
            except ValueError:
                continue
        else:
            debit, credit = row[debit_idx].strip(), row[credit_idx].strip()
            if debit:
                amount = -abs(_parse_amount(debit))
            elif credit:
                amount = abs(_parse_amount(credit))
            else:
                continue

        description = html.unescape(row[desc_idx]).strip()
        txn_type = row[type_idx].strip() if type_idx is not None and len(row) > type_idx else ''

        transactions.append({
            'Date': date.strftime('%d %b %Y'),
            'Description': description,
            'Amount': f"{'-' if amount < 0 else ''}£{abs(amount):,.2f}",
            'Type': txn_type,
        })

    return transactions
