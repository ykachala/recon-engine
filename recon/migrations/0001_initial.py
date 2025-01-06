import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies: list = []

    operations = [
        migrations.CreateModel(
            name="ReconciliationRun",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("status", models.CharField(
                    choices=[("pending", "Pending"), ("running", "Running"), ("complete", "Complete"), ("failed", "Failed")],
                    default="pending", max_length=20,
                )),
                ("source_file", models.CharField(max_length=512)),
                ("reference_file", models.CharField(max_length=512)),
                ("matched_count", models.IntegerField(default=0)),
                ("unmatched_count", models.IntegerField(default=0)),
                ("discrepancy_count", models.IntegerField(default=0)),
                ("total_source", models.IntegerField(default=0)),
                ("total_reference", models.IntegerField(default=0)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Transaction",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="transactions", to="recon.reconciliationrun")),
                ("source", models.CharField(
                    choices=[("upload", "Uploaded file"), ("reference", "Reference file")],
                    max_length=20,
                )),
                ("external_id", models.CharField(blank=True, max_length=255)),
                ("date", models.DateField()),
                ("description", models.TextField()),
                ("amount_cents", models.BigIntegerField()),
                ("currency", models.CharField(default="ZAR", max_length=3)),
                ("raw_row", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Discrepancy",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="discrepancies", to="recon.reconciliationrun")),
                ("kind", models.CharField(
                    choices=[
                        ("amount_mismatch", "Amount mismatch"),
                        ("missing_reference", "Missing in reference"),
                        ("missing_source", "Missing in source"),
                        ("date_mismatch", "Date mismatch"),
                        ("duplicate", "Duplicate transaction"),
                    ],
                    max_length=30,
                )),
                ("source_transaction", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="source_discrepancies", to="recon.transaction")),
                ("reference_transaction", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reference_discrepancies", to="recon.transaction")),
                ("delta_cents", models.BigIntegerField(blank=True, null=True)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AddIndex(
            model_name="reconciliationrun",
            index=models.Index(fields=["status"], name="recon_recon_status_idx"),
        ),
        migrations.AddIndex(
            model_name="reconciliationrun",
            index=models.Index(fields=["created_at"], name="recon_recon_created_idx"),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(fields=["run", "source"], name="recon_txn_run_source_idx"),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(fields=["date"], name="recon_txn_date_idx"),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(fields=["amount_cents"], name="recon_txn_amount_idx"),
        ),
        migrations.AddIndex(
            model_name="discrepancy",
            index=models.Index(fields=["run", "kind"], name="recon_disc_run_kind_idx"),
        ),
    ]
