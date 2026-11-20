# Deployment

The repository includes a Dockerfile for a single-service deployment. Django serves the frontend, API, and collected static files from the same origin. Use a managed PostgreSQL database for deployment; SQLite remains the local development default.

## Deploy from GitHub

Use a hosting provider that builds a Dockerfile from the repository root. Configure these environment variables in the provider dashboard:

| Variable | Value |
| --- | --- |
| `DJANGO_DEBUG` | `false` |
| `DJANGO_SECRET_KEY` | A new random secret; generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DJANGO_ALLOWED_HOSTS` | Your app hostname, without `https://` |
| `DATABASE_URL` | The provider's PostgreSQL connection URL |
| `CORS_ALLOWED_ORIGINS` | Leave empty for same-origin frontend; otherwise comma-separated frontend origins including scheme |
| `CSRF_TRUSTED_ORIGINS` | If needed, comma-separated trusted origins including scheme |

The container runs migrations on startup and listens on the host-provided `PORT` (or `8000` locally). The Docker image collects and serves static assets with WhiteNoise.

## Load catalog data

The deployed database starts empty. After the first deploy, open the provider's application shell and run these commands from `/app/backend`:

```sh
python clean_data.py
python manage.py import_medicines
python manage.py import_local_catalog
```

The raw medicine CSV is included in the image; the cleaned CSV is generated during this one-time import and is not committed. The included pharmacy, lab, and test listings are sample data. Medicine MRP values are catalogue references, not live pharmacy quotes; do not present them as store-specific prices.

Keep the PostgreSQL database persistent and back it up. Do not use the development secret-key fallback or SQLite for a public deployment.

## Local container build

From the repository root:

```sh
docker build -t sehatsetu .
```

To run the container, provide the deployment environment variables above and a reachable PostgreSQL `DATABASE_URL`.
