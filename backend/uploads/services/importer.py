"""Transactional ticket import with isolated row-level failures."""
import hashlib

from django.db import IntegrityError, transaction
from django.utils import timezone

from tickets.models import Ticket
from uploads.models import ImportRow, RowStatus, UploadStatus, UploadType

from .file_reader import read_tabular_file
from .validator import resolve_field_map, validate_field_map, validate_row

UPDATE_FIELDS = (
    "title", "status", "source_status", "category", "source_category",
    "subcategory", "plant_code", "channel", "source_channel", "assignee",
    "created_at_source", "resolved_at", "source_updated_at", "resolution_days", "due_at", "raw_source_data",
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
    try:
        mapping = validate_field_map(field_map)
        headers, source_rows = read_tabular_file(file_obj, batch.original_filename)
        mapping = resolve_field_map(mapping, headers, explicit=field_map is not None)
        if mapping["incident_number"] not in headers:
            raise ImportExecutionError(
                f"Required source column not found: {mapping['incident_number']}"
            )
        if batch.upload_type == UploadType.FULL and not snapshot_scope.strip():
            raise ImportExecutionError("Full report uploads require an explicit snapshot_scope.")
        digest = _file_sha256(file_obj)
    except Exception as exc:
        batch.status = UploadStatus.FAILED
        batch.completed_at = timezone.now()
        batch.error_summary = str(exc)
        batch.save(update_fields=("status", "completed_at", "error_summary"))
        if isinstance(exc, ImportExecutionError):
            raise
        raise ImportExecutionError(str(exc)) from exc

    imported_at = timezone.now()
    counts = {"inserted": 0, "updated": 0, "unchanged": 0, "rejected": 0}
    seen = set()
    batch.status = UploadStatus.PROCESSING
    batch.started_at = imported_at
    batch.snapshot_scope = snapshot_scope.strip()
    batch.file_sha256 = digest
    batch.metadata = {
        **(batch.metadata or {}), "source_headers": headers, "field_map": mapping,
    }
    batch.save(update_fields=(
        "status", "started_at", "snapshot_scope", "file_sha256", "metadata",
    ))

    with transaction.atomic():
        for source in source_rows:
            row_number = int(source["__row_number__"])
            incident = str(source.get(mapping["incident_number"]) or "").strip()
            audit_source = {
                key: (value.isoformat() if hasattr(value, "isoformat") else value)
                for key, value in source.items()
            }
            ticket = None
            row_status = RowStatus.REJECTED
            error = ""
            try:
                values = validate_row(source, mapping)
                incident = values["incident_number"]
                if incident in seen:
                    raise ValueError(f"Duplicate incident number '{incident}' in this file.")
                seen.add(incident)

                # A savepoint keeps a database-level row failure from breaking the
                # surrounding batch transaction and its remaining audit records.
                with transaction.atomic():
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
            except (ValueError, TypeError, IntegrityError) as exc:
                ticket = None
                error = str(exc)
                row_status = RowStatus.REJECTED
                counts["rejected"] += 1

            ImportRow.objects.create(
                batch=batch, row_number=row_number,
                incident_number=incident[:100], status=row_status,
                error_message=error, source_data=audit_source,
                ticket=ticket, processed_at=imported_at,
            )

        # Only '*' currently means a complete enterprise-wide snapshot. We do not
        # infer plant/category scope from a string and never delete or auto-resolve.
        if (
            batch.upload_type == UploadType.FULL
            and counts["rejected"] == 0
            and snapshot_scope.strip() == "*"
        ):
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
    return batch
