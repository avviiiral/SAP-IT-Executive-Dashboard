from django.urls import path

from .views import (
    DashboardBacklogView, DashboardBreakdownsView, DashboardSummaryView,
    DashboardTicketListView, DashboardTrendsView,
)

urlpatterns = [
    path("summary/", DashboardSummaryView.as_view(), name="analytics-summary"),
    path("trends/", DashboardTrendsView.as_view(), name="analytics-trends"),
    path("breakdowns/", DashboardBreakdownsView.as_view(), name="analytics-breakdowns"),
    path("backlog/", DashboardBacklogView.as_view(), name="analytics-backlog"),
    path("tickets/", DashboardTicketListView.as_view(), name="analytics-tickets"),
]
