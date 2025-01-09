from datetime import date
import pytest

from recon.parsers import ParseError, iter_csv_rows, row_to_transaction_data


class TestIterCsvRows:
    def test_parses_standard_csv(self):
        content = "date,description,amount\n2025-03-01,Salary deposit,50000\n2025-03-02,Rent payment,-15000\n"
        rows = list(iter_csv_rows(content))
        assert len(rows) == 2
        assert rows[0]["description"] == "Salary deposit"

    def test_raises_on_no_header(self):
        with pytest.raises(ParseError, match="no header"):
            list(iter_csv_rows(""))


class TestRowToTransactionData:
    def test_parses_standard_row(self):
        row = {"date": "2025-03-15", "description": "Subscription", "amount": "450.00"}
        data = row_to_transaction_data(row)
        assert data["date"] == date(2025, 3, 15)
        assert data["amount_cents"] == 45000
        assert data["description"] == "Subscription"
        assert data["currency"] == "ZAR"

    def test_parses_south_african_date_format(self):
        row = {"transaction_date": "15/03/2025", "narration": "Transfer", "debit": "1000.00"}
        data = row_to_transaction_data(row)
        assert data["date"] == date(2025, 3, 15)

    def test_handles_comma_in_amount(self):
        row = {"date": "2025-03-01", "description": "Payroll", "amount": "45,000.00"}
        data = row_to_transaction_data(row)
        assert data["amount_cents"] == 4500000

    def test_raises_on_invalid_amount(self):
        row = {"date": "2025-03-01", "description": "Test", "amount": "not-a-number"}
        with pytest.raises(ParseError, match="Cannot parse amount"):
            row_to_transaction_data(row)

    def test_raises_on_missing_required_field(self):
        row = {"date": "2025-03-01", "description": "Missing amount field"}
        with pytest.raises(ParseError):
            row_to_transaction_data(row)
