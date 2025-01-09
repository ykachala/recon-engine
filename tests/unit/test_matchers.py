from datetime import date
import pytest
from unittest.mock import MagicMock

from recon.matchers import exact_match, find_best_match, fuzzy_amount_match


def make_txn(**kwargs):
    defaults = {
        "id": "00000000-0000-0000-0000-000000000001",
        "date": date(2025, 3, 15),
        "description": "Monthly subscription payment",
        "amount_cents": 45000,
        "currency": "ZAR",
    }
    defaults.update(kwargs)
    txn = MagicMock()
    for k, v in defaults.items():
        setattr(txn, k, v)
    return txn


class TestExactMatch:
    def test_matches_identical_transactions(self):
        source = make_txn()
        reference = make_txn(id="00000000-0000-0000-0000-000000000002")
        result = exact_match(source, reference)
        assert result is not None
        assert result.match_type == "exact"
        assert result.confidence == 1.0
        assert result.delta_cents == 0

    def test_no_match_on_amount_difference(self):
        source = make_txn(amount_cents=45000)
        reference = make_txn(amount_cents=45001)
        assert exact_match(source, reference) is None

    def test_no_match_on_date_difference(self):
        source = make_txn(date=date(2025, 3, 15))
        reference = make_txn(date=date(2025, 3, 16))
        assert exact_match(source, reference) is None

    def test_no_match_on_currency_difference(self):
        source = make_txn(currency="ZAR")
        reference = make_txn(currency="USD")
        assert exact_match(source, reference) is None


class TestFuzzyAmountMatch:
    def test_matches_within_tolerance(self):
        source = make_txn(amount_cents=45000, description="Shoprite grocery purchase")
        reference = make_txn(amount_cents=45050, description="Shoprite groceries")
        result = fuzzy_amount_match(source, reference, tolerance_cents=100, date_tolerance_days=1, description_threshold=60)
        assert result is not None
        assert result.match_type == "fuzzy"
        assert result.delta_cents == -50

    def test_no_match_exceeds_amount_tolerance(self):
        source = make_txn(amount_cents=45000)
        reference = make_txn(amount_cents=46000)
        result = fuzzy_amount_match(source, reference, tolerance_cents=100, date_tolerance_days=1, description_threshold=60)
        assert result is None

    def test_no_match_description_too_dissimilar(self):
        source = make_txn(description="Shoprite grocery purchase", amount_cents=45000)
        reference = make_txn(description="Amazon web services subscription fee", amount_cents=45010)
        result = fuzzy_amount_match(source, reference, tolerance_cents=100, date_tolerance_days=1, description_threshold=80)
        assert result is None


class TestFindBestMatch:
    def test_prefers_exact_over_fuzzy(self):
        source = make_txn(amount_cents=45000, date=date(2025, 3, 15), description="Exact payment")
        exact = make_txn(id="aaa", amount_cents=45000, date=date(2025, 3, 15), description="Exact payment")
        fuzzy = make_txn(id="bbb", amount_cents=45020, date=date(2025, 3, 15), description="Exact payment slightly off")
        result = find_best_match(source, [fuzzy, exact], tolerance_cents=50, date_tolerance_days=1, description_threshold=60)
        assert result is not None
        assert result.match_type == "exact"

    def test_returns_none_when_no_candidates(self):
        source = make_txn()
        result = find_best_match(source, [], tolerance_cents=0, date_tolerance_days=0, description_threshold=100)
        assert result is None
