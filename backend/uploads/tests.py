from django.test import TestCase

from tickets.models import Ticket
from .models import ImportRow, RowStatus, UploadBatch, UploadType


class UploadModelTests(TestCase):
    def test_batch_tracks_import_counts(self):
        batch = UploadBatch.objects.create(
            original_filename="sanitized-sample.xlsx",
            upload_type=UploadType.INCREMENTAL,
            total_rows=3,
            inserted_rows=1,
            updated_rows=1,
            rejected_rows=1,
        )
        self.assertEqual(
            batch.inserted_rows + batch.updated_rows + batch.rejected_rows,
            batch.total_rows,
        )

    def test_import_row_is_linked_to_ticket_and_batch(self):
        batch = UploadBatch.objects.create(
            original_filename="sample.csv", upload_type=UploadType.FULL
        )
        ticket = Ticket.objects.create(incident_number="INC-2001")
        row = ImportRow.objects.create(
            batch=batch,
            row_number=2,
            incident_number=ticket.incident_number,
            status=RowStatus.INSERTED,
            ticket=ticket,
        )
        self.assertEqual(row.batch, batch)
        self.assertEqual(row.ticket, ticket)
