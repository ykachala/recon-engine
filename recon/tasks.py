import logging
from datetime import datetime, timezone

from celery import shared_task
from django.conf import settings
from django.db import transaction as db_transaction

from recon.matchers import find_best_match
from recon.models import Discrepancy, ReconciliationRun, Transaction
from recon.parsers import ParseError, iter_csv_rows, row_to_transaction_data

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def run_reconciliation(self, run_id: str) -> dict:
    try:
        run = ReconciliationRun.objects.get(id=run_id)
    except ReconciliationRun.DoesNotExist:
        logger.error("ReconciliationRun %s not found", run_id)
        return {"error": "run_not_found"}

    run.status = ReconciliationRun.Status.RUNNING
    run.started_at = datetime.now(timezone.utc)
    run.save(update_fields=["status", "started_at"])

    try:
        _process_run(run)
        run.status = ReconciliationRun.Status.COMPLETE
    except Exception as exc:
        logger.exception("Reconciliation run %s failed", run_id)
        run.status = ReconciliationRun.Status.FAILED
        run.save(update_fields=["status", "completed_at", "updated_at"])
        raise self.retry(exc=exc)
    finally:
        run.completed_at = datetime.now(timezone.utc)
        run.save(update_fields=["status", "completed_at", "matched_count", "unmatched_count", "discrepancy_count"])

    return {
        "run_id": str(run.id),
        "matched": run.matched_count,
        "unmatched": run.unmatched_count,
        "discrepancies": run.discrepancy_count,
    }


def _process_run(run: ReconciliationRun) -> None:
    from pathlib import Path

    source_content = Path(run.source_file).read_text()
    reference_content = Path(run.reference_file).read_text()

    source_txns = _load_transactions(run, source_content, Transaction.Source.UPLOAD)
    reference_txns = _load_transactions(run, reference_content, Transaction.Source.REFERENCE)

    run.total_source = len(source_txns)
    run.total_reference = len(reference_txns)

    tolerance_cents = settings.RECON_AMOUNT_TOLERANCE_CENTS
    date_tolerance = settings.RECON_DATE_TOLERANCE_DAYS
    fuzzy_threshold = settings.RECON_FUZZY_DESCRIPTION_THRESHOLD

    matched_ref_ids: set[str] = set()
    discrepancies: list[Discrepancy] = []
    matched_count = 0

    for source_txn in source_txns:
        available = [r for r in reference_txns if str(r.id) not in matched_ref_ids]
        result = find_best_match(source_txn, available, tolerance_cents, date_tolerance, fuzzy_threshold)

        if result is None:
            discrepancies.append(
                Discrepancy(
                    run=run,
                    kind=Discrepancy.Kind.MISSING_IN_REFERENCE,
                    source_transaction=source_txn,
                    note=f"No reference match found for {source_txn.description[:80]}",
                )
            )
        elif result.delta_cents != 0:
            matched_ref_ids.add(str(result.reference.id))
            matched_count += 1
            discrepancies.append(
                Discrepancy(
                    run=run,
                    kind=Discrepancy.Kind.AMOUNT_MISMATCH,
                    source_transaction=source_txn,
                    reference_transaction=result.reference,
                    delta_cents=result.delta_cents,
                    note=f"Fuzzy match; delta {result.delta_cents} cents",
                )
            )
        else:
            matched_ref_ids.add(str(result.reference.id))
            matched_count += 1

    for ref_txn in reference_txns:
        if str(ref_txn.id) not in matched_ref_ids:
            discrepancies.append(
                Discrepancy(
                    run=run,
                    kind=Discrepancy.Kind.MISSING_IN_SOURCE,
                    reference_transaction=ref_txn,
                    note=f"Reference transaction not found in source: {ref_txn.description[:80]}",
                )
            )

    with db_transaction.atomic():
        Discrepancy.objects.bulk_create(discrepancies, batch_size=500)

    run.matched_count = matched_count
    run.unmatched_count = len(source_txns) - matched_count
    run.discrepancy_count = len(discrepancies)


def _load_transactions(run: ReconciliationRun, content: str, source: str) -> list[Transaction]:
    txns: list[Transaction] = []
    for row in iter_csv_rows(content):
        try:
            data = row_to_transaction_data(row)
        except ParseError as e:
            logger.warning("Skipping unparseable row in run %s: %s", run.id, e)
            continue
        txns.append(
            Transaction(
                run=run,
                source=source,
                **data,
            )
        )
    Transaction.objects.bulk_create(txns, batch_size=1000)
    return list(Transaction.objects.filter(run=run, source=source))
