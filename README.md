# CloudForge — Self-Hosted PaaS Platform

CloudForge is a **Render / Vercel style Platform-as-a-Service** that you can run yourself. Give it a Git repository URL and it clones the code, detects the project type, builds a Docker image, runs the container on a free port and streams the build logs to the browser in real time.

## How It Works

1. A deploy request (`POST /deploy`) is stored in PostgreSQL with status `QUEUED`.
2. A **Celery** worker picks the job up from the Redis queue.
3. The repository is cloned with GitPython into a temporary folder.
4. The project type is detected. An existing `Dockerfile` is used as is; for Node.js (`package.json`) and Python (`requirements.txt`) projects a Dockerfile is generated automatically.
5. The Docker image is built and the container is started on a free host port.
6. Every log line is published to a Redis channel and delivered to the dashboard over a **WebSocket**. The status moves through `QUEUED → BUILDING → SUCCESS / FAILED`.

## Features

- One-call deploy from any Git repository
- Automatic Dockerfile generation for Node.js and Python apps
- Live build logs over WebSocket (Redis pub/sub)
- Project and deployment history stored in PostgreSQL
- Running container management: list, stop and remove
- React dashboard styled with Tailwind CSS

## Tech Stack

| Layer | Technology |
| --- | --- |
| API | FastAPI, Pydantic, Uvicorn |
| Background jobs | Celery, Redis |
| Database | PostgreSQL, SQLAlchemy, Alembic |
| Build and run | Docker SDK for Python, GitPython |
| Frontend | React 19, Vite, Tailwind CSS |

## API Overview

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/projects` | Create a project |
| `GET` | `/projects`, `/projects/{id}` | List projects / project details with deploy history |
| `POST` | `/deploy` | Queue a new deployment |
| `GET` | `/deployments`, `/deployments/{id}` | Deployment list / details |
| `GET` | `/status/{task_id}` | Celery task status |
| `GET` | `/containers` | List running containers |
| `POST` | `/containers/{id}/stop` | Stop a container |
| `DELETE` | `/containers/{id}` | Remove a container |
| `WS` | `/ws/logs/{deploy_id}` | Live build logs |

Interactive docs are served by FastAPI at `/docs`.

## Getting Started

**Prerequisites:** Docker with Docker Compose, and Node.js 18+ for the dashboard.

```bash
git clone https://github.com/enesilbay/CloudForge.git
cd CloudForge
cp .env.example .env

# Start PostgreSQL, Redis, the API and the Celery worker
docker compose up --build

# Start the dashboard
cd frontend
npm install
npm run dev
```

- API: http://localhost:8000
- Dashboard: http://localhost:5173

> **Note:** The backend and worker mount `/var/run/docker.sock` to build and run containers. Only run CloudForge in a trusted environment.

## Project Structure

```
├── main.py              # FastAPI app and WebSocket endpoint
├── tasks/worker.py      # Celery build-and-deploy task
├── services/            # git, Docker and project type detection helpers
├── db/                  # SQLAlchemy models, schemas and CRUD
├── frontend/            # React + Vite + Tailwind dashboard
├── Dockerfile
└── docker-compose.yml
```

## License

This project was developed for learning and portfolio purposes.
