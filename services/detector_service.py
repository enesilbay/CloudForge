import os
import json
import re
from typing import Any, Dict, Set, Tuple

from services.dockerfile_templates import (
    create_react_app_dockerfile,
    next_dockerfile,
    node_server_dockerfile,
    python_dockerfile,
    vite_dockerfile,
)


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


def _detect_node_project(repo_path: str) -> Tuple[str, int, str]:
    _, dependencies, scripts = _read_package_json(repo_path)

    if "vite" in dependencies:
        return (
            "Vite projesi tespit edildi (package.json bağımlılık analizi).",
            8080,
            vite_dockerfile(),
        )

    if "next" in dependencies:
        return (
            "Next.js projesi tespit edildi (package.json bağımlılık analizi).",
            3000,
            next_dockerfile(),
        )

    if "express" in dependencies:
        if "start" in scripts:
            start_cmd = 'CMD ["npm", "start"]'
        elif "server.js" in os.listdir(repo_path):
            start_cmd = 'CMD ["node", "server.js"]'
        else:
            start_cmd = 'CMD ["npm", "run", "dev"]' if "dev" in scripts else 'CMD ["npm", "start"]'
        return (
            "Express projesi tespit edildi (package.json bağımlılık analizi).",
            3000,
            node_server_dockerfile(start_cmd=start_cmd, port=3000),
        )

    if "react-scripts" in dependencies:
        return (
            "Create React App projesi tespit edildi (package.json bağımlılık analizi).",
            8080,
            create_react_app_dockerfile(),
        )

    if "start" in scripts:
        return (
            "Node.js projesi tespit edildi (package.json scripts.start analizi).",
            3000,
            node_server_dockerfile(start_cmd='CMD ["npm", "start"]', port=3000),
        )

    if "dev" in scripts:
        return (
            "Node.js projesi tespit edildi (package.json scripts.dev analizi).",
            3000,
            node_server_dockerfile(
                start_cmd='CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]',
                port=3000,
                production_only=False,
            ),
        )

    return (
        "Node.js projesi tespit edildi (package.json bulundu).",
        3000,
        node_server_dockerfile(start_cmd='CMD ["npm", "start"]', port=3000),
    )


def _find_asgi_module(repo_path: str) -> str:
    if "main.py" in os.listdir(repo_path):
        return "main:app"
    if "app.py" in os.listdir(repo_path):
        return "app:app"
    if os.path.exists(os.path.join(repo_path, "app", "main.py")):
        return "app.main:app"
    return "main:app"


def _detect_python_project(repo_path: str) -> Tuple[str, int, str]:
    dependencies = _read_requirements_txt(repo_path) | _read_pyproject_toml(repo_path)
    files = os.listdir(repo_path)
    install_target = "requirements" if "requirements.txt" in files else "pyproject"

    if "fastapi" in dependencies:
        asgi_module = _find_asgi_module(repo_path)
        return (
            "FastAPI projesi tespit edildi (requirements/pyproject bağımlılık analizi).",
            8000,
            python_dockerfile(
                start_cmd=f'CMD ["uvicorn", "{asgi_module}", "--host", "0.0.0.0", "--port", "8000"]',
                port=8000,
                install_target=install_target,
                extra_packages=[] if "uvicorn" in dependencies else ["uvicorn"],
            ),
        )

    if "django" in dependencies and "manage.py" in files:
        return (
            "Django projesi tespit edildi (requirements/pyproject bağımlılık analizi).",
            8000,
            python_dockerfile(
                start_cmd='CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]',
                port=8000,
                install_target=install_target,
            ),
        )

    if "flask" in dependencies:
        app_module = "app" if "app.py" in files else "main"
        return (
            "Flask projesi tespit edildi (requirements/pyproject bağımlılık analizi).",
            8000,
            python_dockerfile(
                start_cmd=f'CMD ["flask", "--app", "{app_module}", "run", "--host", "0.0.0.0", "--port", "8000"]',
                port=8000,
                install_target=install_target,
            ),
        )

    if "streamlit" in dependencies:
        entrypoint = "app.py" if "app.py" in files else "main.py"
        return (
            "Streamlit projesi tespit edildi (requirements/pyproject bağımlılık analizi).",
            8501,
            python_dockerfile(
                start_cmd=f'CMD ["streamlit", "run", "{entrypoint}", "--server.address=0.0.0.0", "--server.port=8501"]',
                port=8501,
                install_target=install_target,
            ),
        )

    return (
        "Python projesi tespit edildi (requirements.txt veya pyproject.toml bulundu).",
        8000,
        python_dockerfile(
            start_cmd='CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]',
            port=8000,
            install_target=install_target,
            extra_packages=[] if "uvicorn" in dependencies else ["uvicorn"],
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


def process_dockerfile(repo_path: str):
    dosyalar = os.listdir(repo_path)
    
    if "Dockerfile" in dosyalar:
        exposed_port = _read_exposed_port_from_dockerfile(repo_path)
        return f"Projede mevcut Dockerfile bulundu, EXPOSE portu {exposed_port} olarak algılandı.", exposed_port
        
    elif "package.json" in dosyalar:
        detected_msg, target_port, dockerfile_icerigi = _detect_node_project(repo_path)
        with open(os.path.join(repo_path, "Dockerfile"), "w", encoding="utf-8") as f:
            f.write(dockerfile_icerigi)
        return f"{detected_msg} Optimize edilmiş Node.js Dockerfile şablonu oluşturuldu.", target_port
        
    elif "requirements.txt" in dosyalar or "pyproject.toml" in dosyalar:
        detected_msg, target_port, dockerfile_icerigi = _detect_python_project(repo_path)
        with open(os.path.join(repo_path, "Dockerfile"), "w", encoding="utf-8") as f:
            f.write(dockerfile_icerigi)
        return f"{detected_msg} Optimize edilmiş Python Dockerfile şablonu oluşturuldu.", target_port
        
    else:
        raise Exception("Desteklenmeyen proje! İçinde Dockerfile, requirements.txt veya package.json bulunmalı.")
