# SAP & IT Executive Dashboard

An executive dashboard for SAP and IT service desk analytics.

## Technology stack
- Frontend: Angular 20, Apache ECharts
- Backend: Django REST Framework
- Databases: SQLite (local development) and PostgreSQL (production)
- Data processing: Pandas and OpenPyXL

## Current capabilities
- Canonical incident/ticket model and audited spreadsheet-import foundation
- Read-only analytics API for executive KPIs, trends, breakdowns, backlog health and ticket drill-down
- Responsive Angular executive dashboard with shared reporting filters
- Real business reports, database files and local environment secrets must not be committed to this public repository

## Backend setup
1. Create and activate a virtual environment in `backend`.
2. Install dependencies: `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` inside `backend`.
4. Keep `DB_ENGINE=sqlite` for local development.
5. Run `python manage.py migrate`, then `python manage.py runserver`.

See [database configuration](docs/backend-database-configuration.md), [data model](docs/data-model.md), [import engine](docs/import-engine.md) and [analytics API](docs/analytics-api.md).

## Frontend setup
See [Angular frontend setup](docs/frontend-setup.md).

## Import safety
Incremental uploads insert or update by incident number. Full reports are reconciled as snapshots only within an explicitly declared scope. Missing records are marked as absent from the latest snapshot; they are never silently deleted or marked resolved.
