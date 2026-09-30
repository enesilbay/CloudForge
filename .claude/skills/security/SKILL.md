---
name: security
description: CloudForge'da authentication (JWT, bcrypt), secret şifreleme (Fernet), kullanıcı env var'ları, yetkilendirme, docker.sock ve kullanıcı kodu çalıştırma riskleri. Auth, secret, izin veya güvenlik incelemesi içeren işlerde kullan.
---

# Security

## İlgili dosyalar
- `services/auth_service.py`: bcrypt (passlib) hash, PyJWT token. Anahtar `JWT_SECRET_KEY` env.
- `services/crypto_service.py`: Fernet ile env var şifreleme. Anahtar `CLOUDFORGE_ENCRYPTION_KEY` env.
- `db/crud.py`: `get_decrypted_env_dict_for_project` (decrypt sadece deploy anında yapılmalı)
- `main.py`: `get_current_user`, `/auth/*`, `/projects/{id}/env`

## Bilinen durum (değiştirmeden önce kullanıcıya danış)
- JWT ve encryption key'lerin kod içinde varsayılan fallback değerleri var. Production'da env zorunlu olmalı.
- `docker-compose.yml` içinde DB şifresi düz metin (lokal geliştirme için).
- Bazı proje/env/deployment endpoint'leri `get_current_user` ile sahiplik kontrolü yapmıyor olabilir. İlgili endpoint'i incelemeden varsayımda bulunma.

## Kurallar
- Secret, token, şifre ve decrypt edilmiş env değerlerini loglama, Redis log kanalına basma, response'ta döndürme (maskele).
- Yeni secret'ı `.env.example`'a sadece placeholder olarak ekle. Gerçek `.env` Git'e girmez.
- Encryption key değişirse mevcut şifreli veriler çözülemez. Rotasyon planı olmadan key değiştirme.
- Kullanıcıdan gelen repo URL, path ve komutları güvenilmez kabul et (path traversal, command injection).
- Kullanıcı kodu çalıştıran container'larda non-root, resource limit ve ağ izolasyonu uygula.
- GitHub webhook eklenirse HMAC imzasını `hmac.compare_digest` ile doğrula.

## Açıklama (AGENTS.md)
Auth/authorization/encryption/secret değişikliklerinde güvenlik gerekçesini kısaca açıkla.
