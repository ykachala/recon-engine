from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView

from recon.models import Discrepancy, ReconciliationRun
from recon.serializers import (
    DiscrepancySerializer,
    ReconciliationRunSerializer,
    RunCreateSerializer,
)
from recon.tasks import run_reconciliation


class ReconciliationRunListView(APIView):
    def get(self, request: Request) -> Response:
        runs = ReconciliationRun.objects.all()[:100]
        return Response(ReconciliationRunSerializer(runs, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = RunCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        run = ReconciliationRun.objects.create(
            name=data["name"],
            source_file=data["source_file"],
            reference_file=data["reference_file"],
        )
        run_reconciliation.delay(str(run.id))

        return Response(
            ReconciliationRunSerializer(run).data,
            status=status.HTTP_202_ACCEPTED,
        )


class ReconciliationRunDetailView(RetrieveAPIView):
    queryset = ReconciliationRun.objects.all()
    serializer_class = ReconciliationRunSerializer
    lookup_field = "id"


class DiscrepancyListView(ListAPIView):
    serializer_class = DiscrepancySerializer

    def get_queryset(self):
        run_id = self.kwargs["run_id"]
        qs = Discrepancy.objects.filter(run_id=run_id).select_related(
            "source_transaction", "reference_transaction"
        )
        kind = self.request.query_params.get("kind")
        if kind:
            qs = qs.filter(kind=kind)
        return qs
