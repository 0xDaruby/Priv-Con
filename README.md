# PrivCon

PrivCon is a local-first document converter. It runs a Next.js interface and a FastAPI/LibreOffice conversion service on your computer so documents do not need to be sent to a third-party conversion service.

The MVP supports:

- Word (`.docx`) to PDF
- PowerPoint (`.pptx`) to PDF
- Excel (`.xlsx`) to PDF
- PDF merge
- PDF split by page or range
- Image (`.jpg`, `.jpeg`, `.png`) to PDF

## Recommended setup: Docker

Docker is the simplest way to run PrivCon because the backend image already contains Python, LibreOffice, and the required fonts. You do not need to install those dependencies separately on the host.

### Docker vocabulary in one minute

- An **image** is a reusable blueprint containing an application and its dependencies.
- A **container** is a running instance of an image. PrivCon runs one frontend container and one backend container.
- **Docker Compose** reads `docker-compose.yml` and starts those containers as one application.
- A **health check** asks a running container whether it is ready, rather than assuming that a started process is usable.
- A **network** lets the two containers find each other. PrivCon also publishes their ports to `127.0.0.1`, which means they are reachable from this computer but not exposed to the local network.

### Prerequisites

Use one of these supported Docker installations:

- **Windows:** Docker Desktop with the WSL 2 engine. Wait until Docker Desktop says **Engine running**.
- **macOS:** Docker Desktop. Wait until its engine has started.
- **Linux:** Docker Engine with the Docker Compose plugin. Make sure your user can run Docker commands.

Confirm that both Docker and Compose are available:

```console
docker --version
docker compose version
```

### Start PrivCon

Open PowerShell, Terminal, or a shell in the repository root—the folder containing this README—and run:

```console
docker compose up --build --wait
```

The first build takes longer because Docker downloads the base images and installs LibreOffice. Later builds reuse cached layers when their inputs have not changed.

When the command finishes:

- Open the app at <http://localhost:3000>
- Check the backend at <http://localhost:8000/api/health>

The health endpoint should return:

```json
{"status":"ok"}
```

`--build` builds images when needed. `--wait` keeps the command from reporting success until both services pass their health checks. Compose starts the services in the background because `--wait` implies detached mode.

### Inspect the running app

Show container state and health:

```console
docker compose ps
```

Follow both services' logs; press `Ctrl+C` to stop following the logs without stopping PrivCon:

```console
docker compose logs --follow
```

Follow only one service:

```console
docker compose logs --follow backend
docker compose logs --follow frontend
```

### Stop or rebuild

Stop PrivCon and remove its containers and private Compose network:

```console
docker compose down
```

This does not remove the built images. The next start can reuse them.

After pulling or editing source code, rebuild and restart:

```console
docker compose up --build --wait
```

If you need to force a completely fresh rebuild while troubleshooting:

```console
docker compose build --no-cache
docker compose up --wait
```

## How the local architecture works

Your browser talks to the frontend at `127.0.0.1:3000`. Conversion requests go to the backend at `127.0.0.1:8000`. Compose gives the containers a private bridge network, while the explicit `127.0.0.1` port bindings prevent LAN exposure.

Uploads and generated outputs live only in the backend container's controlled temporary directories. PrivCon cleans job files after success, failure, or cancellation and purges unclaimed crash debris when the backend starts. Compose does not create a named volume for uploads or outputs, so conversion files are not intentionally persisted outside the backend container.

PrivCon does not require a cloud conversion API, account, or authentication service. The portfolio link in the footer is ordinary external navigation; conversion files are never sent through it.

## Troubleshooting

### Docker cannot connect to the engine

On Windows or macOS, open Docker Desktop and wait for **Engine running**, then retry `docker compose up --build --wait`. On Linux, start the Docker service using your distribution's service manager.

### Port 3000 or 8000 is already in use

Check whether another PrivCon instance is running:

```console
docker compose ps
```

If it is, stop it with `docker compose down`. Otherwise stop the unrelated process using the occupied port before starting PrivCon.

### A service is unhealthy or exits

Inspect its recent logs:

```console
docker compose logs --tail 200 backend
docker compose logs --tail 200 frontend
```

Then check the resolved Compose configuration:

```console
docker compose config
```

### Docker Desktop has limited memory

Large presentations, spreadsheets, or image-heavy jobs can need more memory. Close other heavy workloads or increase Docker Desktop's memory allocation if conversions are terminated unexpectedly.

## Optional native development setup

Docker is recommended for normal use. Native development is useful when you want hot reload and direct access to each runtime.

### Backend

Install Python 3.12 and LibreOffice, then from `backend/` create a virtual environment and install dependencies.

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

macOS/Linux:

```bash
python3 -m venv venv
./venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
./venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If LibreOffice is not on `PATH`, set `LIBREOFFICE_PATH` in `backend/.env` to its executable. A typical Windows value is `C:\Program Files\LibreOffice\program\soffice.exe`; a typical macOS value is `/Applications/LibreOffice.app/Contents/MacOS/soffice`.

### Frontend

Install Node.js 24 and npm, then from `frontend/` run:

```console
npm ci
npm run dev
```

The checked-in `frontend/.env.local.example` points the browser to `http://localhost:8000`. Copy it to `.env.local` only when you need to override or extend local settings.

Windows users with the native dependencies already installed can alternatively double-click `start_privcon.bat` after completing the backend and frontend dependency installation once.

## Verification for contributors

Run the backend tests and formatting checks from `backend/`:

```console
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

Run the frontend checks from `frontend/`:

```console
npm run check
```

Validate the packaging from the repository root:

```console
docker compose config --quiet
docker compose up --build --wait
docker compose ps
```

## Configuration

The backend defaults are documented in `backend/.env.example`. The supplied Compose configuration sets the container paths, LibreOffice command, and allowed browser origin directly. Keep secrets and machine-specific overrides out of version control, and never commit `.env`, uploads, temporary conversion files, or generated outputs.
