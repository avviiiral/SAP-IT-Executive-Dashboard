"""Transactional ticket import service with row-level audit history."""
from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from tickets.models import Ticket
from uploads.models import ImportRow, RowStatus, UploadBatch, UploadStatus, UploadType

from .file_reader import read_tabular_file
from .validator import validate_field_map, validate_row


IMPORTABLE_FIELDS = (
    "title",
    "status",
    "source_status",
    "category",
    "source_category",
    "subcategory",
    "plant_code",
    "channel",
    "source_channel",
    "assignee",
    "created_at_source",
    "resolved_at",
    "resolution_days",
    "due_at",
    "raw_source_data",
)


class ImportExecutionError(ValueError):
    """Raised when a batch cannot be safely processed."""


def sha256_file(file_obj) -> str:
    digest = hashlib.sha256()
    position = file_obj.tell() if hasattr(file_obj, "tell") else None
    for chunk in file_obj.chunks() if hasattr(file_obj, "chunks") else iter(lambda: file_obj.read(1024 * 1024), b""):
        digest.update(chunk)
    if position is not None:
        file_obj.seek(position)
    return digest.hexdigest()


def _same_values(ticket: Ticket, values: dict[str, Any]) -> bool:
    return all(getattr(ticket, field) == values[field] for field in IMPORTABLE_FIELDS)


def process_upload(
    *,
    batch: UploadBatch,
    file_obj,
    field_map: dict[str, str] | None = None,
    snapshot_scope: str = "",
) -> UploadBatch:
    """Process one upload. FULL reconciliation is limited to an explicit scope.

    A full report with rejected rows does not reconcile missing incidents, avoiding
    accidental disappearance of records because of malformed input.
    """
    mapping = validate_field_map(field_map)
    batch.status = UploadStatus.PROCESSING
    batch.started_at = timezone.now()
    batch.snapshot_scope = snapshot_scope.strip()
    batch.save(update_fields=("status", "started_at", "snapshot_scope"))

    try:
        headers, source_rows = read_tabular_file(file_obj, batch.original_filename)
        missing_headers = sorted({mapping["incident_number"]} - set(headers))
        if missing_headers:
            raise ImportExecutionError(
                "Required source column not found: " + ", ".join(missing_headers)
            )
        if batch.upload_type == UploadType.FULL and not snapshot_scope.strip():
            raise ImportExecutionError("Full report uploads require an explicit snapshot_scope.")

        batch.file_sha256 = sha256_file(file_obj)
        batch.metadata = {
            **(batch.metadata or {}),
            "source_headers": headers,
            "field_map": mapping,
        }

        counters = {"inserted": 0, "updated": 0, "unchanged": 0, "rejected": 0}
        seen_incidents: set[str] = set()
        processed_at = timezone.now()

        with transaction.atomic():
            for source in source_rows:
                row_number = int(source["__row_number__"])
                audit_source = {
                    key: (value.isoformat() if hasattr(value, "isoformat") else value)
                    for key, value in source.items()
                }
                incident_number = str(source.get(mapping["incident_number"]) or "").strip()
                status = RowStatus.REJECTED
                error_message = ""
                ticket = None

                try:
                    values = validate_row(source, mapping)
                    incident_number = values["incident_number"]
                    if incident_number in seen_incidents:
                        raise ValueError(f"Duplicate incident number '{incident_number}' in this file.")
                    seen_incidents.add(incident_number)

                    ticket = Ticket.objects.filter(incident_number=incident_number).first()
                    if ticket is None:
                        ticket = Ticket.objects.create(incident_number=incident_number, **values)
                        status = RowStatus.INSERTED
                        counters["inserted"] += 1
                    elif _same_values(ticket, values):
                        status = RowStatus.UNCHANGED
                        counters["unchanged"] += 1
                    else:
                        for field in IMPORTABLE_FIELDS:
                            setattr(ticket, field, values[field])
                        ticket.missing_from_latest_full_snapshot = False
                        ticket.save()
                        status = RowStatus.UPDATED
                        counters["updated"] += 1

                    if batch.upload_type == UploadType.FULL:
                        ticket.last_seen_in_full_snapshot_at = processed_at
                        ticket.missing_from_latest_full_snapshot = False
                        ticket.save(update_fields=(
                            "last_seen_in_full_snapshot_at",
                            "missing_from_latest_full_snapshot",
                            "updated_on",
                        ))
                except (ValueError, TypeError) as exc:
                    error_message = str(exc)
                    counters["rejected"] += 1

                ImportRow.objects.create(
                    batch=batch,
                    row_number=row_number,
                    incident_number=incident_number[:100],
                    status=status,
                    error_message=error_message,
                    source_data=audit_source,
                    ticket=ticket,
                    processed_at=processed_at,
                )

            # Do not infer missing records from a partial/invalid full report.
            if batch.upload_type == UploadType.FULL and counters["rejected"] == 0:
                existing = Ticket.objects.exclude(last_seen_in_full_snapshot_at=processed_at)
                # Scope is currently a required audit boundary, not an assumed plant filter.
                # Until the source report defines a stable scope expression, never mark
                # enterprise-wide records missing.
                if snapshot_scope == "*":
                    existing.update(missing_from_latest_full_snapshot=True)

            batch.total_rows = len(source_rows)
            batch.inserted_rows = counters["inserted"]
            batch.updated_rows = counters["updated"]
            batch.unchanged_rows = counters["unchanged"]
            batch.rejected_rows = counters["rejected"]
            batch.status = (
                UploadStatus.COMPLETED_WITH_ERRORS
                if counters["rejected"]
                else UploadStatus.COMPLETED
            )
            batch.completed_at = timezone.now()
            batch.error_summary = (
                f"{counters['rejected']} row(s) were rejected."
                if counters["rejected"]
                else ""
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
