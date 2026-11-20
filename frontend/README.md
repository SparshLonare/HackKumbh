# SehatSetu frontend

The frontend source is deployed to Vercel from the repository root. `vercel.json` runs a small build script and publishes `vercel-build/`. Set the Vercel environment variable `API_BASE_URL` to the Render API URL ending in `/api`, for example `https://your-api.onrender.com/api`.

For local development, run the Django app from `backend/` with `.venv/Scripts/python.exe manage.py runserver` and open `http://localhost:8000`. The checked-in `static/api-config.js` points to the same-origin `/api`; the Vercel build replaces it with the configured Render URL.

Medicine MRPs are catalogue references, not pharmacy quotes or live stock. The pharmacy, lab and test CSVs are sample data. See [../DEPLOYMENT.md](../DEPLOYMENT.md) for deployment and data import steps.
