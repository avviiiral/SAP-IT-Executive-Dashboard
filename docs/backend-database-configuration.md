# Backend database configuration

The backend supports SQLite and PostgreSQL through the same Django models and ORM. Select the database with `DB_ENGINE` in `backend/.env`.

## Local development with SQLite

Create `backend/.env` from `backend/.env.example`, then set:

```env
DB_ENGINE=sqlite
DJANGO_DEBUG=true
```

From the `backend` directory with the virtual environment activated:

```powershell
python manage.py check
python manage.py migrate
python manage.py shell -c "from django.db import connection; print(connection.vendor)"
```

The last command should print `sqlite`. Django creates `backend/db.sqlite3`.

## Running with PostgreSQL

Create the PostgreSQL database and user, then set the following in `backend/.env`:

```env
DB_ENGINE=postgresql
DB_NAME=sap_it_dashboard
DB_USER=postgres
DB_PASSWORD=your-local-password
DB_HOST=localhost
DB_PORT=5432
DJANGO_DEBUG=true
```

Run the same `check` and `migrate` commands. The last command should print `postgresql`.

For deployment, set `DJANGO_DEBUG=false`, provide a strong private `DJANGO_SECRET_KEY`, and set `DJANGO_ALLOWED_HOSTS` to the actual host names. Do not commit `.env` or database files.

## Important: database switching does not copy data

SQLite and PostgreSQL are independent databases. Running migrations creates the schema in the selected database; it does not copy application records from the other database. Use an explicit, tested data migration/export process when transferring real data between them.
