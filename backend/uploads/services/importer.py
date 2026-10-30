"""Transactional ticket import service with row-level audit results."""
import hashlib

from django.db import transaction
from django.utils import timezone

from tickets.models import Ticket
from uploads.models import ImportRow, RowStatus, UploadStatus, UploadType

from .file_reader import read_tabular_file
from .validator import validate_field_map, validate_row

UPDATE_FIELDS = (
    "title", "status", "source_status", "category", "source_category",
    "subcategory", "plant_code", "channel", "source_channel", "assignee",
    "created_at_source", "resolved_at", "resolution_days", "due_at", "raw_source_data",
)


class ImportExecutionError(ValueError):
    pass


def _file_sha256(file_obj):
    digest = hashlib.sha256()
    original = file_obj.tell() if hasattr(file_obj, "tell") else 0
    if hasattr(file_obj, "chunks"):
        for chunk in file_obj.chunks():
            digest.update(chunk)
    else:
        while True:
            chunk = file_obj.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    if hasattr(file_obj, "seek"):
        file_obj.seek(original)
    return digest.hexdigest()


def process_upload(*, batch, file_obj, field_map=None, snapshot_scope=""):
    mapping = validate_field_map(field_map)
    batch.status = UploadStatus.PROCESSING
    batch.started_at = timezone.now()
    batch.snapshot_scope = snapshot_scope.strip()
    batch.save(update_fields=("status", "started_at", "snapshot_scope"))
    try:
        headers, source_rows = read_tabular_file(file_obj, batch.original_filename)
        if mapping["incident_number"] not in headers:
            raise ImportExecutionError(
                f"Required source column not found: {mapping['incident_number']}"
            )
        if batch.upload_type == UploadType.FULL and not snapshot_scope.strip():
            raise ImportExecutionError("Full report uploads require an explicit snapshot_scope.")

        batch.file_sha256 = _file_sha256(file_obj)
        batch.metadata = {
            **(batch.metadata or {}),
            "source_headers": headers,
            "field_map": mapping,
        }
        counts = {"inserted": 0, "updated": 0, "unchanged": 0, "rejected": 0}
        seen = set()
        imported_at = timezone.now()

        with transaction.atomic():
            for source in source_rows:
                row_number = int(source["__row_number__"])
                incident = str(source.get(mapping["incident_number"]) or "").strip()
                ticket = None
                row_status = RowStatus.REJECTED
                error = ""
                audit_source = {
                    key: (value.isoformat() if hasattr(value, "isoformat") else value)
                    for key, value in source.items()
                }
                try:
                    values = validate_row(source, mapping)
                    incident = values["incident_number"]
                    if incident in seen:
                        raise ValueError(f"Duplicate incident number '{incident}' in this file.")
                    seen.add(incident)
                    ticket = Ticket.objects.filter(incident_number=incident).first()
                    if ticket is None:
                        ticket = Ticket.objects.create(**values)
                        row_status = RowStatus.INSERTED
                        counts["inserted"] += 1
                    elif all(getattr(ticket, name) == values[name] for name in UPDATE_FIELDS):
                        row_status = RowStatus.UNCHANGED
                        counts["unchanged"] += 1
                    else:
                        for name in UPDATE_FIELDS:
                            setattr(ticket, name, values[name])
                        ticket.missing_from_latest_full_snapshot = False
                        ticket.save()
                        row_status = RowStatus.UPDATED
                        counts["updated"] += 1
                    if batch.upload_type == UploadType.FULL:
                        ticket.last_seen_in_full_snapshot_at = imported_at
                        ticket.missing_from_latest_full_snapshot = False
                        ticket.save(update_fields=(
                            "last_seen_in_full_snapshot_at",
                            "missing_from_latest_full_snapshot", "updated_on",
                        ))
                except (ValueError, TypeError) as exc:
                    error = str(exc)
                    counts["rejected"] += 1
                ImportRow.objects.create(
                    batch=batch, row_number=row_number,
                    incident_number=incident[:100], status=row_status,
                    error_message=error, source_data=audit_source,
                    ticket=ticket, processed_at=imported_at,
                )

            # Missing-record inference is deliberately disabled for plant/other scopes
            # until their exact field semantics are approved. '*' explicitly denotes
            # an enterprise-wide complete report.
            if batch.upload_type == UploadType.FULL and counts["rejected"] == 0 and snapshot_scope.strip() == "*":
                Ticket.objects.exclude(last_seen_in_full_snapshot_at=imported_at).update(
                    missing_from_latest_full_snapshot=True
                )

            batch.total_rows = len(source_rows)
            batch.inserted_rows = counts["inserted"]
            batch.updated_rows = counts["updated"]
            batch.unchanged_rows = counts["unchanged"]
            batch.rejected_rows = counts["rejected"]
            batch.status = (
                UploadStatus.COMPLETED_WITH_ERRORS if counts["rejected"]
                else UploadStatus.COMPLETED
            )
            batch.completed_at = timezone.now()
            batch.error_summary = (
                f"{counts['rejected']} row(s) were rejected." if counts["rejected"] else ""
            )
            batch.save()
    except Exception as exc:
        batch.status = UploadStatus.FAILED
        batch.completed_at = timezone.now()
        batch.error_summary = str(exc)
        batch.save(update_fields=("status", "completed_at", "error_summary", "file_sha256", "metadata"))
        if isinstance(exc, ImportExecutionError):
            raise
        raise ImportExecutionError(str(exc)) from exc
    return batch
