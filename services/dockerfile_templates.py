import json
from typing import List, Optional


def shell_cmd(command: str) -> str:
    return json.dumps(["sh", "-c", command])


def node_install_command(custom_command: Optional[str] = None, production_only: bool = False) -> str:
    if custom_command:
        return f"RUN {custom_command}"

    omit_dev = " --omit=dev" if production_only else ""
    return (
        "RUN if [ -f package-lock.json ]; then "
        f"npm ci{omit_dev} --ignore-scripts; "
        "else "
        f"npm install{omit_dev} --ignore-scripts; "
        "fi"
    )


def static_node_dockerfile(
    build_command: str,
    output_directory: str,
    install_command: Optional[str] = None,
) -> str:
    return f"""FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
{node_install_command(install_command)}
COPY . .
RUN {build_command}

FROM nginxinc/nginx-unprivileged:1.27-alpine AS runner
COPY --from=builder /app/{output_directory} /usr/share/nginx/html
USER nginx
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
"""


def vite_dockerfile() -> str:
    return static_node_dockerfile(build_command="npm run build", output_directory="dist")


def create_react_app_dockerfile() -> str:
    return static_node_dockerfile(build_command="npm run build", output_directory="build")


def next_dockerfile() -> str:
    return node_server_dockerfile(
        start_command="npm start",
        port=3000,
        build_command="npm run build",
    )


def node_server_dockerfile(
    start_command: str,
    port: int = 3000,
    install_command: Optional[str] = None,
    build_command: Optional[str] = None,
    production_only: bool = True,
) -> str:
    build_step = f"RUN {build_command}\n" if build_command else ""
    install_production_only = production_only and not build_command
    return f"""FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
{node_install_command(install_command, production_only=install_production_only)}

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=deps /app/node_modules ./node_modules
COPY . .
{build_step}USER node
EXPOSE {port}
CMD {shell_cmd(start_command)}
"""


def python_dockerfile(
    start_command: str,
    port: int = 8000,
    install_command: Optional[str] = None,
    has_requirements: bool = True,
    extra_install_command: Optional[str] = None,
) -> str:
    if install_command:
        dependency_install = f"RUN {install_command}"
    elif has_requirements:
        dependency_install = "RUN pip install --no-cache-dir -r requirements.txt"
    else:
        dependency_install = "RUN pip install --no-cache-dir ."

    extra_install = f"RUN {extra_install_command}\n" if extra_install_command else ""

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
CMD {shell_cmd(start_command)}
"""

