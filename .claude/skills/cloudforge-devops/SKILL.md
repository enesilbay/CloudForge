---
name: cloudforge-devops
description: CloudForge'un genel mimarisi, deploy akışı (FastAPI → Redis → Celery → Docker), docker-compose geliştirme ortamı, CI pipeline ve roadmap'e göre iş planlama. Birden fazla katmanı etkileyen görevlerde veya "nereden başlamalıyım" sorularında kullan.
---

# CloudForge DevOps

## Mimari (mevcut durum)
Frontend (React/Vite) → FastAPI (`main.py`) → Redis (broker + log pub/sub) → Celery Worker (`tasks/worker.py`) → Docker daemon (`/var/run/docker.sock`) → PostgreSQL (`db/`)

Deploy akışı:
1. `POST /deploy` → Deployment kaydı oluşturulur, `build_and_deploy_task.delay(...)` çağrılır
2. Worker: `git_service.clone_repo` → `detector_service.process_dockerfile` → `docker_service.build_image` → `run_container`
3. Loglar Redis üzerinden yayınlanır, `/ws/logs/{deploy_id}` WebSocket'i ile frontend'e akar
4. Durum `crud` ile DB'ye yazılır (DB = source of truth)

## Kurallar
- Değişiklikten önce `roadmap.md` (docker-compose/PaaS) ve `roadmap_eks.md` (EKS geçişi) dosyalarındaki ilgili maddeyi bul. Kapsamı o maddeyle sınırla.
- Birden fazla katmanı etkileyen değişikliklerde çalışma sırasını AGENTS.md formatında göster.
- Yeni servis eklenirken `docker-compose.yml` içindeki healthcheck + `depends_on: condition: service_healthy` desenine uy.
- Backend ve worker aynı image'ı kullanır. Bağımlılık değişikliği ikisini de etkiler.

## Kontrol (CI ile aynı)
- `python -m compileall -q .`
- `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics`
- `docker compose config`
- Gerekirse `docker build -t cloudforge-app:local .`

Not: Projede henüz otomatik test paketi yok. Bunu raporda açıkça belirt.
