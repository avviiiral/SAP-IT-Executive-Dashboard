from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Ticket, TicketStatus


class TicketModelTests(TestCase):
    def test_incident_number_is_unique(self):
        Ticket.objects.create(incident_number="INC-1001", status=TicketStatus.OPEN)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Ticket.objects.create(incident_number="INC-1001", status=TicketStatus.OPEN)

    def test_snapshot_absence_does_not_change_ticket_status(self):
        ticket = Ticket.objects.create(
            incident_number="INC-1002",
            status=TicketStatus.IN_PROGRESS,
            missing_from_latest_full_snapshot=True,
        )
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, TicketStatus.IN_PROGRESS)
        self.assertTrue(ticket.missing_from_latest_full_snapshot)
