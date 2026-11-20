# Deploy with Render and Vercel

The backend runs on Render with PostgreSQL. Vercel serves the static frontend. The Vercel build writes the backend URL from `API_BASE_URL`; the browser then calls Render directly, so the Render service must allow the Vercel site origin through `CORS_ALLOWED_ORIGINS`.

## 1. Deploy the backend on Render

1. In Render, create a Blueprint and select this GitHub repository. Render reads `render.yaml` from the repository root.
2. Apply the Blueprint. It creates a Python web service and PostgreSQL database. The service installs dependencies, collects static files, and runs migrations when it starts.
3. After it is live, copy the service URL, for example `https://sehatsetu-api.onrender.com`.

The Blueprint uses Render's free PostgreSQL plan to avoid selecting a paid plan for you. Render currently expires free PostgreSQL databases after 30 days; upgrade the database before then if you need it to keep running and retain data. See [Render's free plan limits](https://render.com/docs/free).

Render sets `RENDER_EXTERNAL_HOSTNAME`, which the Django settings add to `ALLOWED_HOSTS`. The Blueprint generates `DJANGO_SECRET_KEY` and sets `DJANGO_DEBUG=false`.

## 2. Deploy the frontend on Vercel

1. Import the same GitHub repository in Vercel. Keep the project root set to the repository root; `vercel.json` runs the build script, which copies the frontend into `vercel-build/` for static hosting.
2. Add the Vercel environment variable `API_BASE_URL` with the Render URL plus `/api`, for example `https://sehatsetu-api.onrender.com/api`.
3. Deploy or redeploy the frontend.

## 3. Allow the Vercel site in Render

Copy the Vercel production origin, such as `https://your-project.vercel.app`, then add it in the Render backend environment as `CORS_ALLOWED_ORIGINS`. Use the origin only (scheme and hostname, no path or trailing slash). Redeploy the Render service after changing the variable. If you add a custom frontend domain, include that origin too, comma-separated.

## 4. Import the catalog data

The database starts empty. Open the Render service shell and run these commands from the repository root:

```sh
cd backend
python clean_data.py
python manage.py import_medicines
python manage.py import_local_catalog
```

The raw medicine CSV is included in the repository. The cleaned CSV is generated during import and is not committed. The included pharmacy, lab, and test listings are sample data; medicine MRPs are catalogue references, not live pharmacy quotes.

To create an admin login, run `python manage.py createsuperuser` in the Render shell. Keep database backups and do not use sample provider prices as live offers.
