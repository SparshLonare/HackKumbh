# SehatSetu

SehatSetu is a Django API and mobile-first frontend for comparing medicine catalogue reference prices and diagnostic-test listings.

## Backend setup

From `backend/`, create and activate a virtual environment, then install dependencies and initialize SQLite:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
```

The raw medicine source CSV is in `backend/data/raw/`. Generate the cleaned catalog and import it with:

```powershell
python clean_data.py
python manage.py import_medicines
python manage.py import_local_catalog
```

Start the API with `python manage.py runserver`.

## Frontend

Follow [frontend/README.md](frontend/README.md) to serve the static frontend locally. Medicine MRP values are catalogue references, not pharmacy quotes or live stock. The pharmacy and lab CSVs are sample data.

## Configuration

The development settings use a local-only fallback key. Set `DJANGO_SECRET_KEY` for deployments, set `DJANGO_DEBUG=false`, and provide comma-separated `DJANGO_ALLOWED_HOSTS` values. Keep credentials in environment variables; do not commit `.env` files.
