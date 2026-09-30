# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

CloudForge is a Render/Vercel-style PaaS: a user submits a Git repo URL, the backend clones it, generates or reuses a Dockerfile, builds an image, and runs it as a container on the local Docker daemon while streaming logs to a React UI. The long-term plan is a move to AWS EKS (see `roadmap_eks.md`), but everything today runs on a single Docker host.

## Working with the maintainer

`AGENTS.md` (also loaded as project instructions) applies: the maintainer is learning, so respond in Turkish, explain non-obvious concepts and the cross-file flow after significant changes, state the DB operation type (SELECT/INSERT/UPDATE/DELETE) for DB changes, and **never commit or push unless asked**. Small changes need only a short explanation.

`AGENTS.md`, `roadmap.md`, `roadmap_eks.md`, `proje.md`, `render-vercel-platform-plani.md`, `pyrefly.toml` and `pyrightconfig.json` are in `.gitignore` — they exist locally but are not in the repo. `roadmap.md` is the source of truth for what is done vs. planned (current branch `feature/build-cache` = item 1.4.4; 1.4.5 timeout/resource guard is next).

Project skills live in `.claude/skills/` (`cloudforge-devops`, `docker`, `fastapi`, `kubernetes`, `security`, `terraform`); use them for tasks in those areas.

## Commands

```bash
cp .env.example .env                 # then adjust; .env is gitignored

# Full stack (postgres, redis, backend on :8000 with --reload, celery worker)
docker compose up --build

# Run pieces on the host instead (needs postgres + redis reachable, e.g. `docker compose up postgres redis`)
uvicorn main:app --reload
celery -A tasks.worker.celery_app worker --loglevel=info   # on Windows add: --pool=solo

# Frontend (Vite dev server on :5173)
cd frontend && npm install && npm run dev
cd frontend && npm run lint          # eslint; also `npm run build`
```

**There is no test suite** (no `tests/`, no pytest). CI (`.github/workflows/ci.yml`, on push/PR to `main` and `develop`) runs only these, which you can reproduce locally:

```bash
python -m compileall -q .
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics   # blocking
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=120 --statistics   # advisory
docker compose config
docker build -f Dockerfile .
```

Type checking is editor-only (pyright `basic` / pyrefly configs, Python 3.13 venv in `venv/`; the CI/Docker image uses Python 3.11 — keep code compatible with both). Pyrefly's SQLAlchemy errors are known noise.

Git flow: `feature/*` → `develop` → `main`, via PRs.

## Architecture

### Deploy pipeline (the core flow — spans 6 files)

```
React (frontend/src/App.jsx)
 → POST /deploy (main.py)         creates Deployment row (QUEUED), enqueues Celery task
 → Redis broker
 → tasks/worker.py: build_and_deploy_task
     git_service.clone_repo → temp dir
     crud.get_build_settings (optional per-project overrides)
     detector_service.process_dockerfile → (message, container_port, build_path)
     docker_service.build_image  (docker-py, streams build chunks)
     crud.get_decrypted_env_dict_for_project → env vars injected
     docker_service.run_container (random free host port)
     crud.update_deployment_status → SUCCESS/FAILED
```

- **Two separate uses of Redis:** Celery broker/result backend, *and* pub/sub channel `logs_{deploy_id}` for live logs. `main.py`'s `/ws/logs/{deploy_id}` WebSocket subscribes to that channel; the worker always publishes the literal string `"EOF"` in `finally`, which is how the socket knows to close. Late subscribers get nothing (pub/sub is not persisted) — persistent logs come from `Deployment.build_logs`.
- `worker.emit_log()` does both things at once: publishes to Redis **and** appends to `Deployment.build_logs` in Postgres (opening a fresh `SessionLocal()` each call — the worker does not use FastAPI's `get_db`).
- `deploy_id` (8-char uuid hex generated in `main.py`) is the `Deployment.id` and also names everything downstream: image `cloudforge-app:{deploy_id}`, container `cf-app-{deploy_id}`. `docker_service.list_containers` finds user apps by the `cf-app-` name filter, so keep that prefix.
- Both `backend` and `worker` containers mount `/var/run/docker.sock` and `.:/app` — user-app containers are siblings on the host daemon, not nested. Untrusted user code is built and run there with no timeout/resource limits yet (roadmap 1.4.5).
- The worker catches all exceptions and *returns* an error dict rather than raising, so Celery task state is `SUCCESS` even for failed deploys; the truth is `Deployment.status`.

### Dockerfile detection (`services/detector_service.py`, `dockerfile_templates.py`)

`process_dockerfile` picks by file presence, in order: existing `Dockerfile` (used as-is, port from `EXPOSE` or the override) → `package.json` (Node: Vite/CRA/Next/server/static variants) → `requirements.txt`/`pyproject.toml` (Python, finds ASGI module, adds uvicorn if missing) → otherwise raises. For generated cases it **writes the Dockerfile into the cloned repo** and returns it. `ProjectBuildSettings` (root dir, install/build/start command, output dir, port) override detection; `root_directory` is path-traversal-checked by `_safe_join_repo_path`. Templates are multi-stage, non-root, and use `--ignore-scripts` for npm — preserve those properties when editing them.

### Backend layout

`main.py` holds all routes (auth, projects, build-settings, env vars, deploy, deployments, containers, websocket) → `db/crud.py` (all queries; takes a `Session`) → `db/models.py` (SQLAlchemy 2.0 `Mapped[]` style, string hex-uuid PKs) with Pydantic models in `db/schemas.py`. `services/` are stateless helpers with no DB access except via crud. Comments, docstrings and user-facing messages are in Turkish — match that.

Things that differ from what you might assume:
- **No migrations.** `Alembic` is in `requirements.txt` but unused; `Base.metadata.create_all()` runs at import time in `main.py`. Changing an existing model does not alter existing tables — flag this when touching `models.py`.
- **Auth is optional, not enforced.** `get_current_user` returns `None` when there is no/invalid token, and most routes (projects, env vars, deploy, container stop/delete) don't check ownership. JWT (HS256, 7-day, `services/auth_service.py`) is only actually required by `/auth/me`. Don't assume a route is protected.
- **Container endpoints return HTTP 200 with `{"status": "error"}`** on failure instead of raising `HTTPException`.
- **Secrets:** env vars are Fernet-encrypted (`services/crypto_service.py`, key = SHA-256 of `CLOUDFORGE_ENCRYPTION_KEY`) and only decrypted in the worker at run time; API responses return `value_masked`. `decrypt_secret` swallows errors and returns `""`, so a changed key silently yields empty env vars. Both `CLOUDFORGE_ENCRYPTION_KEY` and `JWT_SECRET_KEY` have insecure hard-coded fallbacks and are absent from `.env.example` — never rely on the fallbacks outside local dev, and never log or echo these values.
- Env config read directly via `os.getenv`: `DATABASE_URL`, `REDIS_URL`/`REDIS_HOST`/`REDIS_PORT`, `JWT_SECRET_KEY`, `CLOUDFORGE_ENCRYPTION_KEY`. Note `docker-compose.yml` hard-codes `DATABASE_URL` for the containers, so `.env` only affects host-run processes and postgres init.

### Frontend

Single-file React 19 + Vite + Tailwind app (`frontend/src/App.jsx`) with `API_BASE = 'http://localhost:8000'` and a `ws://localhost:8000` WebSocket URL hard-coded; backend CORS is wide open. No router or test setup yet.

## Local MCP setup (not in the repo)

Claude Code has read-only `aws`, `kubernetes` and `docker` MCP servers registered at local scope (`~/.claude.json`), alongside the GitHub plugin. AWS uses the assume-role profile `cloudforge-mcp-readonly` (us-east-1) with the proxy's `--read-only` flag, so it exposes docs/region tools only, not resource APIs. The Docker MCP server has no read-only mode; its write tools are blocked via `permissions.deny` in `.claude/settings.local.json` — don't remove those. The kubeconfig still points at a deleted EKS cluster, so Kubernetes MCP calls fail until a new cluster exists.
