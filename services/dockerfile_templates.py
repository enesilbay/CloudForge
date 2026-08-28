from typing import List, Optional


def _node_install_command(production_only: bool = False) -> str:
    omit_dev = " --omit=dev" if production_only else ""
    return (
        "RUN if [ -f package-lock.json ]; then "
        f"npm ci{omit_dev} --ignore-scripts; "
        "else "
        f"npm install{omit_dev} --ignore-scripts; "
        "fi"
    )


def vite_dockerfile() -> str:
    return """FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN if [ -f package-lock.json ]; then npm ci --ignore-scripts; else npm install --ignore-scripts; fi
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine AS runner
COPY --from=builder /app/dist /usr/share/nginx/html
USER nginx
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
"""


def create_react_app_dockerfile() -> str:
    return """FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN if [ -f package-lock.json ]; then npm ci --ignore-scripts; else npm install --ignore-scripts; fi
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine AS runner
COPY --from=builder /app/build /usr/share/nginx/html
USER nginx
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
"""


def next_dockerfile() -> str:
    return """FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN if [ -f package-lock.json ]; then npm ci --ignore-scripts; else npm install --ignore-scripts; fi

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
USER node
EXPOSE 3000
CMD ["npm", "start"]
"""


def node_server_dockerfile(start_cmd: str, port: int = 3000, production_only: bool = True) -> str:
    install_cmd = _node_install_command(production_only=production_only)
    return f"""FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
{install_cmd}

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=deps /app/node_modules ./node_modules
COPY . .
USER node
EXPOSE {port}
{start_cmd}
"""


def python_dockerfile(
    start_cmd: str,
    port: int = 8000,
    install_target: Optional[str] = None,
    extra_packages: Optional[List[str]] = None,
) -> str:
    dependency_install = (
        "RUN pip install --no-cache-dir -r requirements.txt"
        if install_target == "requirements"
        else "RUN pip install --no-cache-dir ."
    )
    extra_install = ""
    if extra_packages:
        extra_install = f"RUN pip install --no-cache-dir {' '.join(extra_packages)}\n"

    return f"""FROM python:3.12-slim AS builder
WORKDIR /app
COPY . .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip
{extra_install}{dependency_install}

FROM python:3.12-slim AS runner
WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH"
COPY --from=builder /opt/venv /opt/venv
COPY . .
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE {port}
{start_cmd}
"""
