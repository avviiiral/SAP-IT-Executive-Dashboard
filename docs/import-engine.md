# Ticket import engine

## API

- `POST /api/uploads/import/`: multipart import.
- `GET /api/uploads/`: latest 100 upload batches.

Both endpoints require an authenticated Django staff user.

## Multipart fields

- `file`: CSV, XLSX or XLSM, up to 20 MB.
- `upload_type`: `INCREMENTAL` or `FULL`.
- `snapshot_scope`: required for full reports.
- `field_map`: optional JSON mapping of canonical fields to exact source column headers.

Example:

```json
{
  "incident_number": "Ticket ID",
  "title": "Short Description",
  "status": "Current Status",
  "created_at_source": "Created On"
}
```

Supported canonical keys: incident_number, title, status, category, subcategory, plant_code, channel, assignee, created_at_source, resolved_at, resolution_days, due_at.

Default headers are illustrative; pass field_map to match the actual report export.

## Processing rules

- Incident number is required and is the upsert key.
- Duplicate incident numbers within one file: first valid row is processed; later duplicate rows are rejected.
- Canonical status/category/channel values are normalized while source labels are retained.
- Every non-empty source row gets an ImportRow audit record.
- Invalid rows are rejected individually; valid rows continue.
- Full reports require a scope identifier. Missing records are never deleted or auto-resolved.
- Scope values other than `*` do not yet drive missing-record detection. Use `*` only for a known complete enterprise-wide report. A plant or category scope requires an approved field-to-scope rule before reconciliation is enabled.

## Security and limits

- Staff-only endpoints.
- File type allowlist: CSV, XLSX, XLSM.
- Upload size limit: 20 MB at the application layer.
- Original upload files are not retained. File SHA-256, headers, mapping, row-level source values and outcomes are kept for audit.
- Production deployment should also enforce request-size limits at the reverse proxy, add malware scanning and move large imports to a background worker.
