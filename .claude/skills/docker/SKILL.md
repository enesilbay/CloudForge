---
name: docker
description: CloudForge'un kendi Dockerfile/docker-compose'u ile kullanıcı projeleri için üretilen Dockerfile şablonları (services/dockerfile_templates.py, detector_service.py) ve docker_service.py build/run mantığı. Build cache, timeout, resource limit işleri için kullan.
---

# Docker

## İki ayrı Docker dünyası var, karıştırma
1. **CloudForge'un kendisi:** kökteki `Dockerfile` (python:3.11-slim) + `docker-compose.yml` (postgres, redis, backend, worker)
2. **Kullanıcı projeleri:** `detector_service.process_dockerfile` framework tespit eder, `dockerfile_templates.py` ile multi-stage Dockerfile üretir. `docker_service.build_image`/`run_container` docker SDK (`docker` paketi) ile çalışır.

## Şablon kuralları (dockerfile_templates.py)
- Multi-stage build, non-root user, npm için `--ignore-scripts` desenini koru.
- Kullanıcı girdisi (build/start/install command) `shell_cmd` ile güvenli şekilde JSON-array CMD'ye çevrilir. Doğrudan string birleştirme yapma.
- `root_directory` için `_safe_join_repo_path` kullan (path traversal koruması).
- Build cache (roadmap 1.4.4): bağımlılık manifestini (`package*.json`, `requirements.txt`) kaynak koddan önce COPY et. Gerekirse BuildKit `--mount=type=cache` kullan. BuildKit gerekiyorsa docker SDK'nın bunu destekleyip desteklemediğini önce doğrula.

## Runtime kuralları (docker_service.py)
- Kullanıcı container'larına bellek/CPU limiti ve build timeout (roadmap 1.4.5) ekle.
- Env var'lar sadece `environment=` ile verilir, loglanmaz.
- `docker.sock` mount'u host üzerinde root eşdeğeri yetki verir. Bunu değiştiren işlerde güvenlik etkisini açıkla.

## Kontrol
- `docker compose config`
- `docker build -t cloudforge-app:local .`
- Şablon değişikliğinde örnek bir Node ve Python repo ile üretilen Dockerfile'ı build et (mümkünse).
