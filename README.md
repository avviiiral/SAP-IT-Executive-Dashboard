# SAP & IT Executive Dashboard

An interactive executive dashboard for SAP and IT service desk analytics.

## Technology stack

- Frontend: Angular
- Backend: Django REST Framework
- Databases: SQLite (local development) and PostgreSQL (production)
- Data processing: Pandas and OpenPyXL
- Charts: Apache ECharts

## Current backend foundation

- Environment-based SQLite/PostgreSQL selection
- Canonical ticket model keyed by incident number
- Upload batch and row-level import audit models
- Separate ticket status and full-snapshot presence tracking
- Django admin registrations for tickets and upload history

## Local backend setup

1. Create and activate a virtual environment in `backend`.
2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` inside `backend`.
4. Keep `DB_ENGINE=sqlite` for local development.
5. Apply migrations and run tests:

   ```powershell
   python manage.py check
   python manage.py makemigrations tickets uploads
   python manage.py migrate
   python manage.py test tickets uploads
   ```

See [database configuration](docs/backend-database-configuration.md) and [data model](docs/data-model.md).

## Import behavior planned

Incremental uploads insert or update by incident number. Full reports are reconciled as snapshots only within an explicitly declared scope. Missing records are marked as absent from the latest snapshot; they are never silently deleted or marked resolved.

Actual business reports, database files, and local environment secrets must not be committed to this public repository.
