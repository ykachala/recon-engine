import pytest
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from recon.models import ReconciliationRun


class TestRunAPI(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("recon.views.run_reconciliation.delay")
    def test_create_run_returns_202(self, mock_delay):
        response = self.client.post(
            "/api/v1/runs/",
            {
                "name": "March billing reconciliation",
                "source_file": "/data/march_transactions.csv",
                "reference_file": "/data/march_reference.csv",
            },
            format="json",
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "pending"
        assert data["name"] == "March billing reconciliation"
        mock_delay.assert_called_once()

    @patch("recon.views.run_reconciliation.delay")
    def test_run_appears_in_list(self, mock_delay):
        self.client.post(
            "/api/v1/runs/",
            {"name": "Test run", "source_file": "/a", "reference_file": "/b"},
            format="json",
        )
        response = self.client.get("/api/v1/runs/")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_run_detail_returns_404_for_unknown(self):
        response = self.client.get("/api/v1/runs/00000000-0000-0000-0000-000000000000/")
        assert response.status_code == 404

    @patch("recon.views.run_reconciliation.delay")
    def test_discrepancy_list_empty_on_new_run(self, mock_delay):
        create_resp = self.client.post(
            "/api/v1/runs/",
            {"name": "Empty run", "source_file": "/a", "reference_file": "/b"},
            format="json",
        )
        run_id = create_resp.json()["id"]
        response = self.client.get(f"/api/v1/runs/{run_id}/discrepancies/")
        assert response.status_code == 200
        assert response.json() == []
