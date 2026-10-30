from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from tickets.models import Ticket
from .models import ImportRow, RowStatus, UploadBatch, UploadStatus, UploadType
from .services.importer import process_upload


class UploadModelTests(TestCase):
    def test_batch_tracks_import_counts(self):
        batch = UploadBatch.objects.create(
            original_filename="sanitized-sample.xlsx",
            upload_type=UploadType.INCREMENTAL,
            total_rows=3, inserted_rows=1, updated_rows=1, rejected_rows=1,
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
            batch=batch, row_number=2, incident_number=ticket.incident_number,
            status=RowStatus.INSERTED, ticket=ticket,
        )
        self.assertEqual(row.batch, batch)
        self.assertEqual(row.ticket, ticket)


class TicketImportServiceTests(TestCase):
    def make_batch(self, upload_type=UploadType.INCREMENTAL):
        return UploadBatch.objects.create(original_filename="sample.csv", upload_type=upload_type)

    def make_csv(self, payload):
        return SimpleUploadedFile("sample.csv", payload.encode("utf-8"), content_type="text/csv")

    def test_incremental_insert_and_audit(self):
        batch = self.make_batch()
        process_upload(
            batch=batch,
            file_obj=self.make_csv("Incident Number,Title,Status,Category\nINC-3001,Email issue,In Progress,IT\n"),
        )
        batch.refresh_from_db()
        self.assertEqual(batch.status, UploadStatus.COMPLETED)
        self.assertEqual(batch.inserted_rows, 1)
        self.assertEqual(batch.rows.get().status, RowStatus.INSERTED)

    def test_duplicate_incident_in_one_file_rejected(self):
        batch = self.make_batch()
        process_upload(
            batch=batch,
            file_obj=self.make_csv("Incident Number,Title\nINC-3002,First\nINC-3002,Duplicate\n"),
        )
        batch.refresh_from_db()
        self.assertEqual(batch.inserted_rows, 1)
        self.assertEqual(batch.rejected_rows, 1)

    def test_full_report_requires_scope(self):
        batch = self.make_batch(UploadType.FULL)
        with self.assertRaises(ValueError):
            process_upload(batch=batch, file_obj=self.make_csv("Incident Number\nINC-3003\n"))
        batch.refresh_from_db()
        self.assertEqual(batch.status, UploadStatus.FAILED)

    def test_custom_header_mapping(self):
        batch = self.make_batch()
        process_upload(
            batch=batch,
            file_obj=self.make_csv("Ticket ID,Summary\nINC-3004,Password reset\n"),
            field_map={"incident_number": "Ticket ID", "title": "Summary"},
        )
        self.assertTrue(Ticket.objects.filter(incident_number="INC-3004", title="Password reset").exists())


class UploadApiTests(TestCase):
    def test_upload_endpoint_requires_staff_authentication(self):
        response = APIClient().get("/api/uploads/")
        self.assertEqual(response.status_code, 403)
