import uuid

from django.conf import settings
from django.db import models


class UploadType(models.TextChoices):
    INCREMENTAL = "INCREMENTAL", "Incremental"
    FULL = "FULL", "Full report"


class UploadStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS", "Completed with errors"
    FAILED = "FAILED", "Failed"


class RowStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    INSERTED = "INSERTED", "Inserted"
    UPDATED = "UPDATED", "Updated"
    UNCHANGED = "UNCHANGED", "Unchanged"
    REJECTED = "REJECTED", "Rejected"


class UploadBatch(models.Model):
    """Audit record for one imported workbook or CSV report."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_filename = models.CharField(max_length=255)
    stored_file = models.FileField(upload_to="ticket_uploads/%Y/%m/", blank=True)
    file_sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    upload_type = models.CharField(max_length=20, choices=UploadType.choices)
    status = models.CharField(max_length=30, choices=UploadStatus.choices, default=UploadStatus.PENDING)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_upload_batches",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    total_rows = models.PositiveIntegerField(default=0)
    inserted_rows = models.PositiveIntegerField(default=0)
    updated_rows = models.PositiveIntegerField(default=0)
    unchanged_rows = models.PositiveIntegerField(default=0)
    rejected_rows = models.PositiveIntegerField(default=0)
    snapshot_scope = models.CharField(max_length=150, blank=True)
    error_summary = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-uploaded_at",)
        indexes = [
            models.Index(fields=("upload_type", "status", "uploaded_at"), name="upload_type_status_date_idx"),
        ]

    def __str__(self):
        return f"{self.original_filename} ({self.upload_type})"


class ImportRow(models.Model):
    """Per-row result for import audit and troubleshooting."""

    batch = models.ForeignKey(UploadBatch, on_delete=models.CASCADE, related_name="rows")
    row_number = models.PositiveIntegerField()
    incident_number = models.CharField(max_length=100, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=RowStatus.choices, default=RowStatus.PENDING)
    error_message = models.TextField(blank=True)
    source_data = models.JSONField(default=dict, blank=True)
    ticket = models.ForeignKey(
        "tickets.Ticket",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="import_rows",
    )
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("row_number",)
        constraints = [
            models.UniqueConstraint(fields=("batch", "row_number"), name="unique_import_batch_row")
        ]
        indexes = [
            models.Index(fields=("batch", "status"), name="import_batch_row_status_idx"),
        ]

    def __str__(self):
        return f"Batch {self.batch_id} row {self.row_number}: {self.status}"
