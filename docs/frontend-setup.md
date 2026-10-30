# Angular executive dashboard

The app is in `frontend/` and consumes the read-only Django analytics API.

## Requirements
- Node.js 20.19+ or 22.12+ (Node 22 LTS recommended)
- npm 10+

## Local setup
Start Django:
```powershell
cd backend
python manage.py migrate
python manage.py runserver
```
In another terminal:
```powershell
cd frontend
npm install
npm start
```
Open the Angular dev URL (normally http://localhost:4200).

Development API base URL: `http://127.0.0.1:8000/api` in `src/environments/environment.ts`. Production uses same-origin `/api` in `environment.prod.ts`; configure the web server to proxy `/api/` to Django.

The dashboard loads summary, trends, breakdowns and backlog together. Month/date bounds, plant, category, subcategory, assignee, status and channel filters are sent as shared query parameters. No ticket data or credentials are bundled. Analytics GET endpoints currently permit anonymous access under DRF's `IsAuthenticatedOrReadOnly` policy; upload endpoints remain staff-only. The paginated tickets endpoint is available in the API; a dedicated ticket explorer is a subsequent increment.

## Build
```powershell
npm run build
```
Output: `dist/sap-it-executive-dashboard/browser`.
