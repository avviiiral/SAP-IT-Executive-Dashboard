from datetime import date, datetime, timedelta, timezone as dt_timezone

from django.test import TestCase
from rest_framework.test import APIClient

from tickets.models import Ticket, TicketCategory, TicketChannel, TicketStatus


class DashboardAnalyticsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.apr_1 = datetime(2026, 4, 1, 9, 0, tzinfo=dt_timezone.utc)
        self.apr_2 = datetime(2026, 4, 2, 9, 0, tzinfo=dt_timezone.utc)
        self.apr_3 = datetime(2026, 4, 3, 9, 0, tzinfo=dt_timezone.utc)
        self._ticket("INC-APR-001", self.apr_1, TicketStatus.RESOLVED, 0.5)
        self._ticket("INC-APR-002", self.apr_2, TicketStatus.RESOLVED, 2)
        self._ticket("INC-APR-003", self.apr_3, TicketStatus.IN_PROGRESS, None)
        self._ticket(
            "INC-LEGACY-001",
            datetime(2026, 3, 31, 9, 0, tzinfo=dt_timezone.utc),
            TicketStatus.IN_PROGRESS,
            None,
        )

    def _ticket(self, number, created, status, days):
        return Ticket.objects.create(
            incident_number=number,
            title=f"Test {number}",
            status=status,
            source_status=status.label,
            category=TicketCategory.SAP,
            source_category="SAP",
            subcategory="MDM",
            plant_code="3001",
            channel=TicketChannel.WEBAPP,
            source_channel="WebApp",
            assignee="SAP Team",
            created_at_source=created,
            resolved_at=(created + timedelta(days=days)) if days is not None else None,
            resolution_days=days,
            due_at=None,
        )

    def test_summary_excludes_legacy_from_kpis_but_keeps_it_in_backlog(self):
        response = self.client.get("/api/analytics/summary/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_tickets"], 3)
        self.assertEqual(response.data["resolved_tickets"], 2)
        self.assertEqual(response.data["open_backlog"], 2)
        self.assertEqual(response.data["resolution_rate"], 0.666667)
        self.assertEqual(response.data["average_resolution_days"], 1.25)
        self.assertEqual(response.data["resolved_within_one_day_rate"], 0.5)

    def test_plant_and_status_filters(self):
        response = self.client.get("/api/analytics/summary/?plant=3001&status=RESOLVED")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_tickets"], 2)
        self.assertEqual(response.data["open_backlog"], 0)

    def test_invalid_month_returns_validation_error(self):
        response = self.client.get("/api/analytics/summary/?month=April")
        self.assertEqual(response.status_code, 400)

    def test_monthly_trends_ignore_month_filter_but_apply_other_filters(self):
        response = self.client.get("/api/analytics/trends/?month=2026-04&plant=3001")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["monthly"]), 1)
        self.assertEqual(response.data["monthly"][0]["month"], "2026-04")
        self.assertEqual(response.data["monthly"][0]["tickets"], 3)

    def test_backlog_includes_legacy_open_tickets(self):
        response = self.client.get("/api/analytics/backlog/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_open"], 2)
        self.assertTrue(any(row["legacy"] for row in response.data["results"]))

    def test_ticket_list_is_paginated(self):
        response = self.client.get("/api/analytics/tickets/?page=1&page_size=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 4)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["total_pages"], 2)
