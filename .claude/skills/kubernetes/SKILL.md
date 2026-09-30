---
name: kubernetes
description: CloudForge'u EKS'e taşıma, K8s manifestleri (Deployment, Service, Ingress, Job) ve worker'ın Docker yerine Kubernetes API kullanması. roadmap_eks.md Aşama 1 ve 3 işleri için kullan.
---

# Kubernetes / EKS

## Bağlam
- Şu an kullanıcı uygulamaları `services/docker_service.py` ile yerel Docker daemon'da çalışıyor (`docker.sock` mount).
- Hedef (`roadmap_eks.md`): Build için Kaniko Job + ECR push. Run için kullanıcı başına Deployment + Service (+ Ingress / AWS ALB). Durum takibi Kubernetes API üzerinden.
- Python tarafında `kubernetes` client kütüphanesi kullanılacak. Eklemeden önce kullanıcıya sor (AGENTS.md: yeni kütüphane kuralı).

## Kurallar
- Docker → K8s geçişinde `docker_service.py` fonksiyon imzalarını (build_image, run_container, list_containers, stop_container, remove_container) mümkün olduğunca koru. Böylece `worker.py` ve `main.py` minimum değişir.
- Her container için `resources.requests/limits`, `readinessProbe`/`livenessProbe` tanımla.
- `securityContext`: `runAsNonRoot: true`, `allowPrivilegeEscalation: false`, mümkünse `readOnlyRootFilesystem`.
- Kullanıcı env var'ları Kubernetes `Secret` olarak verilmeli, manifest içinde düz metin olarak olmamalı.
- Kullanıcı uygulamalarını CloudForge'un kendi bileşenlerinden ayrı namespace'te çalıştır. NetworkPolicy ile izole et.
- Worker'ın ServiceAccount'u için RBAC'ı sadece gereken namespace ve kaynaklarla sınırla.
- Build Job'larına `activeDeadlineSeconds` ekle (roadmap 1.4.5 timeout hedefiyle uyumlu).

## Kontrol
- `kubectl apply --dry-run=client -f <dosya>` veya `kubeconform`
- Canlı cluster'a `apply`/`delete` işlemlerini kullanıcı onayı olmadan yapma.
