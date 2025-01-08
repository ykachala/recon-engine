from django.urls import path

from recon import views

urlpatterns = [
    path("runs/", views.ReconciliationRunListView.as_view(), name="run-list"),
    path("runs/<uuid:id>/", views.ReconciliationRunDetailView.as_view(), name="run-detail"),
    path("runs/<uuid:run_id>/discrepancies/", views.DiscrepancyListView.as_view(), name="discrepancy-list"),
]
