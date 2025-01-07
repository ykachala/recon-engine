from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from fuzzywuzzy import fuzz  # type: ignore[import-untyped]

from recon.models import Transaction


@dataclass(frozen=True)
class MatchResult:
    source: Transaction
    reference: Transaction
    match_type: str
    confidence: float
    delta_cents: int


def exact_match(
    source: Transaction,
    reference: Transaction,
) -> Optional[MatchResult]:
    if (
        source.amount_cents == reference.amount_cents
        and source.date == reference.date
        and source.currency == reference.currency
    ):
        return MatchResult(
            source=source,
            reference=reference,
            match_type="exact",
            confidence=1.0,
            delta_cents=0,
        )
    return None


def fuzzy_amount_match(
    source: Transaction,
    reference: Transaction,
    tolerance_cents: int,
    date_tolerance_days: int,
    description_threshold: int,
) -> Optional[MatchResult]:
    amount_delta = abs(source.amount_cents - reference.amount_cents)
    date_delta = abs((source.date - reference.date).days)
    description_score = fuzz.token_sort_ratio(source.description, reference.description)

    if (
        amount_delta <= tolerance_cents
        and date_delta <= date_tolerance_days
        and description_score >= description_threshold
        and source.currency == reference.currency
    ):
        confidence = 1.0 - (amount_delta / max(abs(source.amount_cents), 1)) * 0.5
        return MatchResult(
            source=source,
            reference=reference,
            match_type="fuzzy",
            confidence=round(confidence, 4),
            delta_cents=source.amount_cents - reference.amount_cents,
        )
    return None


def find_best_match(
    source: Transaction,
    candidates: list[Transaction],
    tolerance_cents: int,
    date_tolerance_days: int,
    description_threshold: int,
) -> Optional[MatchResult]:
    for candidate in candidates:
        result = exact_match(source, candidate)
        if result:
            return result

    fuzzy_results: list[MatchResult] = []
    for candidate in candidates:
        result = fuzzy_amount_match(
            source,
            candidate,
            tolerance_cents,
            date_tolerance_days,
            description_threshold,
        )
        if result:
            fuzzy_results.append(result)

    if not fuzzy_results:
        return None

    return max(fuzzy_results, key=lambda r: r.confidence)
