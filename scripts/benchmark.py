"""
Throughput benchmark for the reconciliation matcher.

Generates two synthetic transaction sets and runs the full match loop.
Run with: python scripts/benchmark.py
"""
import os
import sys
import time
import random
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from unittest.mock import MagicMock
from recon.matchers import find_best_match

DESCRIPTIONS = [
    "Shoprite Checkers",
    "Woolworths Food",
    "Capitec Bank fee",
    "Monthly salary deposit",
    "Vodacom airtime",
    "FNB monthly fee",
    "Netflix subscription",
    "Uber Eats delivery",
    "Pick n Pay",
    "Dischem pharmacy",
]


def make_mock_txn(seed: int, amount_offset: int = 0):
    rng = random.Random(seed)
    txn = MagicMock()
    txn.id = str(seed)
    txn.date = date(2025, 1, 1) + timedelta(days=rng.randint(0, 89))
    txn.description = rng.choice(DESCRIPTIONS) + f" {rng.randint(1000, 9999)}"
    txn.amount_cents = rng.randint(500, 500000) + amount_offset
    txn.currency = "ZAR"
    return txn


def run_benchmark(n: int = 5000) -> None:
    source = [make_mock_txn(i) for i in range(n)]
    reference = [make_mock_txn(i, amount_offset=0) for i in range(n)]

    start = time.perf_counter()
    for txn in source:
        candidates = [r for r in reference if abs((txn.date - r.date).days) <= 1][:20]
        find_best_match(txn, candidates, tolerance_cents=50, date_tolerance_days=1, description_threshold=70)
    elapsed = time.perf_counter() - start

    rps = n / elapsed
    print(f"Processed {n:,} transactions in {elapsed:.2f}s → {rps:,.0f} records/sec")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    run_benchmark(n)
