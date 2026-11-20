# SehatSetu frontend

Run the Django API from `backend/` with `.venv/Scripts/python.exe manage.py runserver`, then serve this folder with `python -m http.server 5173 --directory frontend` from the repository root. Open `http://localhost:5173`.

The frontend calls `http://127.0.0.1:8000/api` by default. Set `window.MEDI_API_BASE` before `app.js` in `index.html` if the API runs elsewhere.

The pharmacy, lab and test CSVs in `backend/data/` are sample data, not verified live listings or quotes. From `backend/`, load/update them with `.venv/Scripts/python.exe manage.py import_local_catalog`. This command is safe to rerun. The medicine catalogue's imported MRP is used as a reference benchmark, including pack-normalized comparisons for compatible alternatives; it is not a pharmacy quote or live availability. No pharmacy-price CSV is supplied, so pharmacy-specific medicine comparisons remain empty until verified prices are added.

Medicine imports can be previewed with `.venv/Scripts/python.exe manage.py import_medicines --dry-run`. Repeating an import that already matches the database is a no-op. If the catalog differs, the command stops; `--replace` is explicit and should only be used after a database backup. It refuses replacement while pharmacy prices reference medicines.
