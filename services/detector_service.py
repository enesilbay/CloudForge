import os
import json
import re
from typing import Any, Dict, Optional, Set, Tuple

from services.dockerfile_templates import (
    node_server_dockerfile,
    python_dockerfile,
    static_node_dockerfile,
)


BuildSettingsDict = Dict[str, Any]


def _normalize_dependency_name(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def _extract_requirement_name(line: str) -> str:
    cleaned = line.split("#", 1)[0].strip()
    if not cleaned or cleaned.startswith("-"):
        return ""
    return re.split(r"[\[<>=!~; ]", cleaned, maxsplit=1)[0].strip()


def _read_package_json(repo_path: str) -> Tuple[Dict[str, Any], Set[str], Dict[str, str]]:
    pkg_path = os.path.join(repo_path, "package.json")
    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)

    scripts = pkg_data.get("scripts", {})
    dependencies = {
        **pkg_data.get("dependencies", {}),
        **pkg_data.get("devDependencies", {}),
    }
    dependency_names = {_normalize_dependency_name(name) for name in dependencies}
    return pkg_data, dependency_names, scripts


def _clean_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _safe_join_repo_path(repo_path: str, root_directory: Optional[str]) -> str:
    if not root_directory:
        return repo_path

    repo_abs = os.path.abspath(repo_path)
    candidate = os.path.abspath(os.path.join(repo_abs, root_directory))

    if candidate != repo_abs and not candidate.startswith(repo_abs + os.sep):
        raise Exception("Root directory repo klasörünün dışına çıkamaz.")
    if not os.path.isdir(candidate):
        raise Exception(f"Root directory bulunamadı: {root_directory}")

    return candidate


def _settings_value(build_settings: Optional[BuildSettingsDict], key: str) -> Optional[Any]:
    if not build_settings:
        return None
    value = build_settings.get(key)
    if isinstance(value, str):
        return _clean_optional_text(value)
    return value


def _read_requirements_txt(repo_path: str) -> Set[str]:
    requirements_path = os.path.join(repo_path, "requirements.txt")
    dependencies = set()

    if not os.path.exists(requirements_path):
        return dependencies

    with open(requirements_path, "r", encoding="utf-8") as f:
        for line in f:
            name = _extract_requirement_name(line)
            if name:
                dependencies.add(_normalize_dependency_name(name))

    return dependencies


def _read_pyproject_toml(repo_path: str) -> Set[str]:
    pyproject_path = os.path.join(repo_path, "pyproject.toml")
    dependencies = set()

    if not os.path.exists(pyproject_path):
        return dependencies

    with open(pyproject_path, "rb") as f:
        content_bytes = f.read()

    try:
        import tomllib

        pyproject_data = tomllib.loads(content_bytes.decode("utf-8"))
        project_dependencies = pyproject_data.get("project", {}).get("dependencies", [])
        for dependency in project_dependencies:
            name = _extract_requirement_name(str(dependency))
            if name:
                dependencies.add(_normalize_dependency_name(name))

        poetry_dependencies = (
            pyproject_data.get("tool", {})
            .get("poetry", {})
            .get("dependencies", {})
        )
        for name in poetry_dependencies:
            if name.lower() != "python":
                dependencies.add(_normalize_dependency_name(name))
    except Exception:
        text = content_bytes.decode("utf-8", errors="ignore")
        for known_dependency in ["fastapi", "flask", "django", "streamlit", "uvicorn", "gunicorn"]:
            if re.search(rf'["\']?{known_dependency}["\']?', text, re.IGNORECASE):
                dependencies.add(known_dependency)

    return dependencies


def _detect_node_project(repo_path: str, build_settings: Optional[BuildSettingsDict] = None) -> Tuple[str, int, str]:
    _, dependencies, scripts = _read_package_json(repo_path)
    install_command = _settings_value(build_settings, "install_command")
    build_command = _settings_value(build_settings, "build_command")
    start_command_override = _settings_value(build_settings, "start_command")
    output_directory = _settings_value(build_settings, "output_directory")
    port_override = _settings_value(build_settings, "port")

    if "vite" in dependencies:
        if start_command_override:
            port = int(port_override or 4173)
            return (
                "Vite projesi tespit edildi; custom start command uygulandı.",
                port,
                node_server_dockerfile(
                    start_command=start_command_override,
                    port=port,
                    install_command=install_command,
                    build_command=build_command,
                    production_only=False,
                ),
            )
        return (
            "Vite projesi tespit edildi (package.json bağımlılık analizi).",
            8080,
            static_node_dockerfile(
                build_command=build_command or "npm run build",
                output_directory=output_directory or "dist",
                install_command=install_command,
            ),
        )

    if "next" in dependencies:
        port = int(port_override or 3000)
        return (
            "Next.js projesi tespit edildi (package.json bağımlılık analizi).",
            port,
            node_server_dockerfile(
                start_command=start_command_override or "npm start",
                port=port,
                install_command=install_command,
                build_command=build_command or "npm run build",
            ),
        )

    if "express" in dependencies:
        port = int(port_override or 3000)
        if start_command_override:
            start_cmd = start_command_override
        elif "start" in scripts:
            start_cmd = "npm start"
        elif "server.js" in os.listdir(repo_path):
            start_cmd = "node server.js"
        else:
            start_cmd = "npm run dev" if "dev" in scripts else "npm start"
        return (
            "Express projesi tespit edildi (package.json bağımlılık analizi).",
            port,
            node_server_dockerfile(
                start_command=start_cmd,
                port=port,
                install_command=install_command,
                build_command=build_command,
            ),
        )

    if "react-scripts" in dependencies:
        if start_command_override:
            port = int(port_override or 3000)
            return (
                "Create React App projesi tespit edildi; custom start command uygulandı.",
                port,
                node_server_dockerfile(
                    start_command=start_command_override,
                    port=port,
                    install_command=install_command,
                    build_command=build_command,
                    production_only=False,
                ),
            )
        return (
            "Create React App projesi tespit edildi (package.json bağımlılık analizi).",
            8080,
            static_node_dockerfile(
                build_command=build_command or "npm run build",
                output_directory=output_directory or "build",
                install_command=install_command,
            ),
        )

    if "start" in scripts:
        port = int(port_override or 3000)
        return (
            "Node.js projesi tespit edildi (package.json scripts.start analizi).",
            port,
            node_server_dockerfile(
                start_command=start_command_override or "npm start",
                port=port,
                install_command=install_command,
                build_command=build_command,
            ),
        )

    if "dev" in scripts:
        port = int(port_override or 3000)
        return (
            "Node.js projesi tespit edildi (package.json scripts.dev analizi).",
            port,
            node_server_dockerfile(
                start_command=start_command_override or "npm run dev -- --host 0.0.0.0",
                port=port,
                install_command=install_command,
                build_command=build_command,
                production_only=False,
            ),
        )

    port = int(port_override or 3000)
    return (
        "Node.js projesi tespit edildi (package.json bulundu).",
        port,
        node_server_dockerfile(
            start_command=start_command_override or "npm start",
            port=port,
            install_command=install_command,
            build_command=build_command,
        ),
    )


def _find_asgi_module(repo_path: str) -> str:
    if "main.py" in os.listdir(repo_path):
        return "main:app"
    if "app.py" in os.listdir(repo_path):
        return "app:app"
    if os.path.exists(os.path.join(repo_path, "app", "main.py")):
        return "app.main:app"
    return "main:app"


def _detect_python_project(repo_path: str, build_settings: Optional[BuildSettingsDict] = None) -> Tuple[str, int, str]:
    dependencies = _read_requirements_txt(repo_path) | _read_pyproject_toml(repo_path)
    files = os.listdir(repo_path)
    install_command = _settings_value(build_settings, "install_command")
    start_command_override = _settings_value(build_settings, "start_command")
    port_override = _settings_value(build_settings, "port")
    has_requirements = "requirements.txt" in files

    if "fastapi" in dependencies:
        asgi_module = _find_asgi_module(repo_path)
        port = int(port_override or 8000)
        return (
            "FastAPI projesi tespit edildi (requirements/pyproject bağımlılık analizi).",
            port,
            python_dockerfile(
                start_command=start_command_override or f"uvicorn {asgi_module} --host 0.0.0.0 --port {port}",
                port=port,
                install_command=install_command,
                has_requirements=has_requirements,
                extra_install_command=None if "uvicorn" in dependencies or install_command else "pip install --no-cache-dir uvicorn",
            ),
        )

    if "django" in dependencies and "manage.py" in files:
        port = int(port_override or 8000)
        return (
            "Django projesi tespit edildi (requirements/pyproject bağımlılık analizi).",
            port,
            python_dockerfile(
                start_command=start_command_override or f"python manage.py runserver 0.0.0.0:{port}",
                port=port,
                install_command=install_command,
                has_requirements=has_requirements,
            ),
        )

    if "flask" in dependencies:
        app_module = "app" if "app.py" in files else "main"
        port = int(port_override or 8000)
        return (
            "Flask projesi tespit edildi (requirements/pyproject bağımlılık analizi).",
            port,
            python_dockerfile(
                start_command=start_command_override or f"flask --app {app_module} run --host 0.0.0.0 --port {port}",
                port=port,
                install_command=install_command,
                has_requirements=has_requirements,
            ),
        )

    if "streamlit" in dependencies:
        entrypoint = "app.py" if "app.py" in files else "main.py"
        port = int(port_override or 8501)
        return (
            "Streamlit projesi tespit edildi (requirements/pyproject bağımlılık analizi).",
            port,
            python_dockerfile(
                start_command=start_command_override or f"streamlit run {entrypoint} --server.address=0.0.0.0 --server.port={port}",
                port=port,
                install_command=install_command,
                has_requirements=has_requirements,
            ),
        )

    port = int(port_override or 8000)
    return (
        "Python projesi tespit edildi (requirements.txt veya pyproject.toml bulundu).",
        port,
        python_dockerfile(
            start_command=start_command_override or f"uvicorn main:app --host 0.0.0.0 --port {port}",
            port=port,
            install_command=install_command,
            has_requirements=has_requirements,
            extra_install_command=None if "uvicorn" in dependencies or install_command else "pip install --no-cache-dir uvicorn",
        ),
    )


def _read_exposed_port_from_dockerfile(repo_path: str) -> int:
    dockerfile_path = os.path.join(repo_path, "Dockerfile")

    with open(dockerfile_path, "r", encoding="utf-8") as f:
        for line in f:
            cleaned = line.split("#", 1)[0].strip()
            if not cleaned:
                continue

            match = re.match(r"^EXPOSE\s+(.+)$", cleaned, re.IGNORECASE)
            if not match:
                continue

            exposed_values = match.group(1).split()
            for exposed_value in exposed_values:
                port_text = exposed_value.split("/", 1)[0]
                if port_text.isdigit():
                    return int(port_text)

    return 8000


def process_dockerfile(repo_path: str, build_settings: Optional[BuildSettingsDict] = None):
    root_directory = _settings_value(build_settings, "root_directory")
    build_path = _safe_join_repo_path(repo_path, root_directory)
    dosyalar = os.listdir(build_path)
    
    if "Dockerfile" in dosyalar:
        exposed_port = int(_settings_value(build_settings, "port") or _read_exposed_port_from_dockerfile(build_path))
        return f"Projede mevcut Dockerfile bulundu, container portu {exposed_port} olarak ayarlandı.", exposed_port, build_path
        
    elif "package.json" in dosyalar:
        detected_msg, target_port, dockerfile_icerigi = _detect_node_project(build_path, build_settings)
        with open(os.path.join(build_path, "Dockerfile"), "w", encoding="utf-8") as f:
            f.write(dockerfile_icerigi)
        return f"{detected_msg} Custom build specs uygulanarak Dockerfile oluşturuldu.", target_port, build_path
        
    elif "requirements.txt" in dosyalar or "pyproject.toml" in dosyalar:
        detected_msg, target_port, dockerfile_icerigi = _detect_python_project(build_path, build_settings)
        with open(os.path.join(build_path, "Dockerfile"), "w", encoding="utf-8") as f:
            f.write(dockerfile_icerigi)
        return f"{detected_msg} Custom build specs uygulanarak Dockerfile oluşturuldu.", target_port, build_path
        
    else:
        raise Exception("Desteklenmeyen proje! İçinde Dockerfile, requirements.txt veya package.json bulunmalı.")
