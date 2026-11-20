# SehatSetu frontend

Run the app from `backend/` with `.venv/Scripts/python.exe manage.py runserver`, then open `http://localhost:8000`. Django serves the frontend and API from the same origin.

For separate frontend hosting, set `window.MEDI_API_BASE` in `index.html` to the deployed API base URL before the `app.js` script and add that frontend origin to the backend's `CORS_ALLOWED_ORIGINS` environment variable.

The pharmacy, lab and test CSVs in `backend/data/` are sample data, not verified live listings or quotes. From `backend/`, load/update them with `.venv/Scripts/python.exe manage.py import_local_catalog`. This command is safe to rerun. The medicine catalogue's imported MRP is used as a reference benchmark, including pack-normalized comparisons for compatible alternatives; it is not a pharmacy quote or live availability. No pharmacy-price CSV is supplied, so pharmacy-specific medicine comparisons remain empty until verified prices are added.

Medicine imports can be previewed with `.venv/Scripts/python.exe manage.py import_medicines --dry-run`. Repeating an import that already matches the database is a no-op. If the catalog differs, the command stops; `--replace` is explicit and should only be used after a database backup. It refuses replacement while pharmacy prices reference medicines.

See [../DEPLOYMENT.md](../DEPLOYMENT.md) for the Docker deployment setup.
