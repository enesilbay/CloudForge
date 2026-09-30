---
name: fastapi
description: CloudForge backend'inde FastAPI endpoint, Pydantic schema, SQLAlchemy model/CRUD, Celery task ve WebSocket değişiklikleri. main.py, db/, tasks/ dosyalarına dokunan işler için kullan.
---

# FastAPI Backend

## Katmanlar
main.py (endpoint'ler) → db/schemas.py (Pydantic) → db/crud.py (DB işlemleri) → db/models.py (SQLAlchemy 2.0 `Mapped`) → PostgreSQL

main.py → tasks/worker.py (Celery `build_and_deploy_task`) → services/*

## Kurallar
- Endpoint'ler şu an `main.py` içinde. Kullanıcı istemedikçe router'lara bölme.
- DB erişimi endpoint içinde değil `crud.py` fonksiyonlarında olmalı. `Session` `Depends(get_db)` ile alınır.
- Worker kendi session'ını `SessionLocal()` ile açar. Her kullanımdan sonra `close()` edildiğinden emin ol.
- Response'lar `response_model` ile tanımlanır. ORM nesnesini schema dışında döndürme (secret sızmasın).
- Sürümler: FastAPI 0.110, Pydantic v2 (`model_config`, `model_dump`), SQLAlchemy 2.x.
- Şema şu an `Base.metadata.create_all` ile oluşuyor. Mevcut tabloya kolon eklemek bunu güncellemez. Alembic (requirements'ta var, henüz kurulmamış) gerekiyorsa kullanıcıya belirt.
- Sync endpoint'lerde (`def`) blocking DB çağrısı normaldir. `async def` içinde blocking çağrı yapma.
- Uzun süren işler endpoint'te değil Celery task'ında yapılır.

## Açıklama (AGENTS.md)
DB değişikliklerinde işlemin türünü (SELECT/INSERT/UPDATE/DELETE) ve commit/refresh kullanımını açıkla.

## Kontrol
- `python -m compileall -q .` + flake8 (CI komutları)
- Mümkünse `uvicorn main:app` ile ayağa kaldırıp `/docs` üzerinden ilgili endpoint'i dene.
