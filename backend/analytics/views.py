from rest_framework.response import Response
from rest_framework.views import APIView

from .services import (
    dashboard_backlog, dashboard_breakdowns, dashboard_summary,
    dashboard_ticket_list, dashboard_trends,
)


class DashboardSummaryView(APIView):
    def get(self, request):
        return Response(dashboard_summary(request.query_params))


class DashboardTrendsView(APIView):
    def get(self, request):
        return Response(dashboard_trends(request.query_params))


class DashboardBreakdownsView(APIView):
    def get(self, request):
        return Response(dashboard_breakdowns(request.query_params))


class DashboardBacklogView(APIView):
    def get(self, request):
        try:
            limit = min(max(int(request.query_params.get("limit", 100)), 1), 500)
        except (TypeError, ValueError):
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"limit": "Must be an integer between 1 and 500."})
        return Response(dashboard_backlog(request.query_params, limit=limit))


class DashboardTicketListView(APIView):
    def get(self, request):
        return Response(dashboard_ticket_list(request.query_params))
