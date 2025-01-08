from rest_framework import serializers

from recon.models import Discrepancy, ReconciliationRun, Transaction


class ReconciliationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReconciliationRun
        fields = [
            "id", "name", "status",
            "matched_count", "unmatched_count", "discrepancy_count",
            "total_source", "total_reference",
            "started_at", "completed_at", "created_at",
        ]
        read_only_fields = [
            "id", "status",
            "matched_count", "unmatched_count", "discrepancy_count",
            "total_source", "total_reference",
            "started_at", "completed_at", "created_at",
        ]


class RunCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    source_file = serializers.CharField(max_length=512)
    reference_file = serializers.CharField(max_length=512)


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ["id", "source", "external_id", "date", "description", "amount_cents", "currency"]


class DiscrepancySerializer(serializers.ModelSerializer):
    source_transaction = TransactionSerializer(read_only=True)
    reference_transaction = TransactionSerializer(read_only=True)

    class Meta:
        model = Discrepancy
        fields = [
            "id", "kind", "delta_cents", "note",
            "source_transaction", "reference_transaction",
            "created_at",
        ]
