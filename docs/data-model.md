# SAP & IT Executive Dashboard — data model

## Ticket

One current-state record per external incident number. `incident_number` is the stable unique business key for incremental imports.

The model stores normalized dimensions used by dashboard filters (status, category, subcategory, plant, channel, assignee) and source values alongside selected normalized enums to preserve unknown source labels.

Source timestamps are stored separately from Django's audit timestamps:
- `created_at_source`: ticket creation date from the source report
- `resolved_at`: source resolution date, when available
- `source_updated_at`: source system update time, when available
- `created_on` / `updated_on`: when this database record was created/changed

## UploadBatch and ImportRow

Every submitted file has an `UploadBatch` containing its type, lifecycle state, checksum, counts, upload identity, and optional snapshot scope. Each parsed source row can be audited through an `ImportRow` with a result status and error description.

Store actual uploaded workbooks outside Git in the configured media directory. Do not commit real service desk reports or raw business data to this public repository.

## Import semantics

### Incremental

- Validate each incident number.
- Insert an incident if it does not exist.
- Update an incident if it already exists.
- Retain row-level inserted/updated/unchanged/rejected outcomes.
- Do not infer deletions from records absent in an incremental file.

### Full snapshot

A full report represents a complete view of its declared `snapshot_scope`. Reconciliation must be limited to that exact scope. A report with no scope must not automatically reconcile the entire enterprise dataset unless the caller explicitly declares it to be enterprise-wide.

After a full batch has been parsed and validated successfully:
- Mark records included in the snapshot as seen and clear their missing marker.
- Mark existing records in the same scope but absent from the snapshot as missing from the latest snapshot.
- Never change a ticket's status to resolved solely because it was absent.
- Never physically delete tickets as a side effect of snapshot reconciliation.

Use a database transaction for the reconciliation operation. Failed or partially parsed uploads must not change snapshot membership.

The current models provide the persistence foundation; import services and APIs will implement these rules in a later step.

## SQLite and PostgreSQL compatibility

Use Django ORM and portable field types/constraints. The same migrations should be applied independently to each database. Switching `DB_ENGINE` changes the active database; it does not transfer records between databases.
