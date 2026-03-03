# InfraPulse

InfraPulse is a lightweight Flask + SQLite dashboard for DevOps engineers to log and track infrastructure incidents per project, with a clean UI and simple admin-only access.

## Features

- **Admin-only sign-in**: Credentials come from `ADMIN_USERNAME` and `ADMIN_PASSWORD` env vars, defaulting to `admin/admin` if not provided.
- **Project management**: Create projects representing services, clusters, environments, etc.
- **Incident logging**: For each project, log incidents with:
  - Title and description
  - Severity (critical/high/medium/low)
  - Downtime in minutes
  - Occurred-at timestamp
  - Resolution notes
  - Resolved / open status (with quick toggle)
- **Dashboard views**:
  - Project-wise open vs closed incident counts (bar chart)
  - Historical incidents per month (line chart)
- **SQLite storage**: Data stored in a SQLite file, easy to back up and mount as a volume.
- **Dockerized**: Simple container image with a mountable data directory.

## Running locally (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

export ADMIN_USERNAME=admin
export ADMIN_PASSWORD=admin
export SECRET_KEY="change-me"

python app.py
```

Then open `http://localhost:5000` and log in with your admin credentials.

## Running with Docker

Build the image:

```bash
docker build -t infrapulse .
```

Run with a mounted data volume:

```bash
mkdir -p data

docker run --rm \
  -p 5000:5000 \
  -e ADMIN_USERNAME=admin \
  -e ADMIN_PASSWORD=admin \
  -e SECRET_KEY="change-me" \
  -v "$(pwd)/data:/app/data" \
  --name infrapulse \
  infrapulse
```

The SQLite database will be created at `/app/data/infra_pulse.db` inside the container, mapped to `./data` on the host.

## Configuration

- **Admin credentials**
  - `ADMIN_USERNAME` (default: `admin`)
  - `ADMIN_PASSWORD` (default: `admin`)
- **Flask secret key**
  - `SECRET_KEY` (default: `dev-secret-change-me`)
- **SQLite path**
  - `SQLITE_DB_PATH` (default in app: `./data/infra_pulse.db`)

## Data model

- **Project**
  - `id`
  - `name`
  - `description`
  - `created_at`
- **Incident**
  - `id`
  - `project_id` (FK to Project)
  - `title`
  - `description`
  - `severity` (`critical`, `high`, `medium`, `low`)
  - `downtime_minutes`
  - `is_resolved`
  - `resolution_summary`
  - `occurred_at`
  - `resolved_at`

## Notes

- This app is designed as a simple, single-admin tool. If you need multi-user access or RBAC, you can extend the models and auth layer accordingly.
- Charts are rendered client-side using Chart.js via CDN.

