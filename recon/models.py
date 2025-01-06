import uuid
from django.db import models


class ReconciliationRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    source_file = models.CharField(max_length=512)
    reference_file = models.CharField(max_length=512)
    matched_count = models.IntegerField(default=0)
    unmatched_count = models.IntegerField(default=0)
    discrepancy_count = models.IntegerField(default=0)
    total_source = models.IntegerField(default=0)
    total_reference = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} [{self.status}]"


class Transaction(models.Model):
    class Source(models.TextChoices):
        UPLOAD = "upload", "Uploaded file"
        REFERENCE = "reference", "Reference file"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(ReconciliationRun, on_delete=models.CASCADE, related_name="transactions")
    source = models.CharField(max_length=20, choices=Source.choices)
    external_id = models.CharField(max_length=255, blank=True)
    date = models.DateField()
    description = models.TextField()
    amount_cents = models.BigIntegerField()
    currency = models.CharField(max_length=3, default="ZAR")
    raw_row = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["run", "source"]),
            models.Index(fields=["date"]),
            models.Index(fields=["amount_cents"]),
        ]

    def __str__(self) -> str:
        return f"{self.date} {self.description[:40]} {self.amount_cents}"


class Discrepancy(models.Model):
    class Kind(models.TextChoices):
        AMOUNT_MISMATCH = "amount_mismatch", "Amount mismatch"
        MISSING_IN_REFERENCE = "missing_reference", "Missing in reference"
        MISSING_IN_SOURCE = "missing_source", "Missing in source"
        DATE_MISMATCH = "date_mismatch", "Date mismatch"
        DUPLICATE = "duplicate", "Duplicate transaction"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(ReconciliationRun, on_delete=models.CASCADE, related_name="discrepancies")
    kind = models.CharField(max_length=30, choices=Kind.choices)
    source_transaction = models.ForeignKey(
        Transaction, null=True, blank=True, on_delete=models.SET_NULL, related_name="source_discrepancies"
    )
    reference_transaction = models.ForeignKey(
        Transaction, null=True, blank=True, on_delete=models.SET_NULL, related_name="reference_discrepancies"
    )
    delta_cents = models.BigIntegerField(null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["run", "kind"]),
        ]

    def __str__(self) -> str:
        return f"{self.kind} on run {self.run_id}"
