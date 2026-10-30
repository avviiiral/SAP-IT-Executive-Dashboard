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

    def test_sap_export_headers_are_mapped_without_manual_field_map(self):
        batch = self.make_batch()
        csv_data = (
            "ORGID,COMID,PCODE,INCNO,CHANL,TITLE,STATUS,PRIORITY,CTGRY,"
            "SUB_CTGRY,REQ_BY,ASN_TO,DUE,createdAt,updatedAt,Cl-Weeks,Cr-Week\n"
            "BAGL,BGOI,3000,INCD100060,WebApp,Approval issue,Resolved,Low,"
            "SAP,SAP-PROJECT,sap@example.com,agent@example.com,GO Live Done,"
            "2025-06-07T00:00:00,2026-09-07T00:00:00,37,23\n"
            "BAGL,BGOI,3000,INCD100061,WebApp,Pending issue,In Progress,Low,"
            "SAP,SAP-PROJECT,sap@example.com,agent@example.com,On Hold,"
            "2026-10-01T00:00:00,2026-10-02T00:00:00,1,40\n"
        )
        process_upload(batch=batch, file_obj=self.make_csv(csv_data))

        resolved = Ticket.objects.get(incident_number="INCD100060")
        self.assertEqual(resolved.status, "RESOLVED")
        self.assertEqual(resolved.source_status, "Resolved")
        self.assertEqual(resolved.plant_code, "3000")
        self.assertEqual(resolved.channel, "WEBAPP")
        self.assertEqual(resolved.subcategory, "SAP-PROJECT")
        self.assertEqual(resolved.assignee, "agent@example.com")
        self.assertEqual(resolved.created_at_source.date().isoformat(), "2025-06-07")
        self.assertEqual(resolved.source_updated_at.date().isoformat(), "2026-09-07")
        self.assertEqual(resolved.resolved_at.date().isoformat(), "2026-09-07")
        self.assertIsNone(resolved.due_at)
        self.assertEqual(resolved.raw_source_data["DUE"], "GO Live Done")

        open_ticket = Ticket.objects.get(incident_number="INCD100061")
        self.assertEqual(open_ticket.status, "IN_PROGRESS")
        self.assertIsNone(open_ticket.resolved_at)
        self.assertEqual(open_ticket.source_updated_at.date().isoformat(), "2026-10-02")
        self.assertIsNone(open_ticket.due_at)


class UploadApiTests(TestCase):
    def test_upload_endpoint_requires_staff_authentication(self):
        response = APIClient().get("/api/uploads/")
        self.assertEqual(response.status_code, 403)
