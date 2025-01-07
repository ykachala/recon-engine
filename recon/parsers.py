import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Iterator

from recon.models import Transaction


class ParseError(Exception):
    pass


def _parse_amount_cents(value: str) -> int:
    cleaned = value.strip().replace(",", "").replace(" ", "")
    try:
        return int(Decimal(cleaned) * 100)
    except InvalidOperation:
        raise ParseError(f"Cannot parse amount: {value!r}")


def _parse_date(value: str) -> date:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            from datetime import datetime
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise ParseError(f"Cannot parse date: {value!r}")


def iter_csv_rows(content: str) -> Iterator[dict]:
    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames is None:
        raise ParseError("CSV has no header row")
    for row in reader:
        yield dict(row)


def row_to_transaction_data(row: dict) -> dict:
    field_aliases = {
        "date": ["date", "transaction_date", "txn_date", "value_date"],
        "description": ["description", "narration", "details", "reference", "memo"],
        "amount": ["amount", "debit", "credit", "value", "amount_zar"],
        "id": ["id", "transaction_id", "txn_id", "ref", "reference_number"],
        "currency": ["currency", "ccy"],
    }

    def find_field(aliases: list[str], row: dict) -> str:
        row_lower = {k.lower(): v for k, v in row.items()}
        for alias in aliases:
            if alias in row_lower:
                return row_lower[alias]
        raise ParseError(f"Could not find field with aliases {aliases} in row keys: {list(row.keys())}")

    raw_date = find_field(field_aliases["date"], row)
    raw_amount = find_field(field_aliases["amount"], row)
    raw_description = find_field(field_aliases["description"], row)

    try:
        external_id = find_field(field_aliases["id"], row)
    except ParseError:
        external_id = ""

    try:
        currency = find_field(field_aliases["currency"], row)
    except ParseError:
        currency = "ZAR"

    return {
        "date": _parse_date(raw_date),
        "amount_cents": _parse_amount_cents(raw_amount),
        "description": raw_description.strip(),
        "external_id": external_id,
        "currency": currency.upper()[:3],
        "raw_row": row,
    }
