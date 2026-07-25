# CloudForge: Uzun Vadeli PaaS (Platform as a Service) Yol Haritası

## 🏁 Tamamlananlar (v0.1 - Yerel Çekirdek)

- [x] Kullanıcıdan GitHub repo linki alma.
- [x] FastAPI ve Docker-py ile repoyu klonlayıp imaj oluşturma.
- [x] Celery ve Redis ile asenkron (kuyruk tabanlı) görev yönetimi.
- [x] React ve Tailwind CSS ile modern arayüz ve Polling (durum sorgulama) mekanizması.

---

## 🏗️ Faz 1: Sağlam Temeller ve Gelişmiş Yönetim (Yerel)

_Sistemi spagetti koddan kurtarıp, gerçek bir platform özellikleriyle donattığımız aşama._

- **Modüler Mimari (Refactoring):** İş mantığını API, Services ve Tasks olarak profesyonel klasör yapısına bölme.
- **Çoklu Dil Desteği:** Python (`requirements.txt`) ve Node.js (`package.json`) projelerini otomatik tanıyıp uygun Dockerfile üretme.
- **Konteyner Yönetim Paneli:**
  - Çalışan uygulamaları arayüzde listeleme.
  - Uygulamaları tek tuşla Durdurma (Stop), Yeniden Başlatma (Restart) ve Silme (Remove).
- **Veritabanı ve Deploy Geçmişi:** SQLite/PostgreSQL entegrasyonu ile geçmiş deploy'ların, sürelerin ve durumların (Başarılı/Hatalı) kalıcı olarak saklanıp listelenmesi.

---

## ⚡ Faz 2: Gerçek Zamanlı Deneyim ve Otomasyon

_Kullanıcı deneyimini "bekleyen" bir yapıdan, "akıcı ve anlık" bir yapıya taşıma._

- **Canlı Build Logları (WebSocket):** Deploy işlemi sırasındaki Docker loglarını (Step 1/6...) Redis Pub/Sub ve WebSockets üzerinden anlık olarak React arayüzüne akıtma.
- **Otomatik Redeploy (CI/CD):** GitHub Webhook entegrasyonu. Kullanıcı reposuna `git push` yaptığında CloudForge'un bunu algılayıp yeni versiyonu otomatik derlemesi ve canlıya alması.

---

## ☁️ Faz 3: Buluta Çıkış (AWS & IaC)

_CloudForge'u yerel makineden kurtarıp 7/24 açık bir bulut platformuna dönüştürme._

- **Altyapı Otomasyonu (Terraform):** AWS EC2 sunucularını ve gerekli güvenlik gruplarını kod yazarak (Infrastructure as Code) otomatik oluşturma.
- **Uzaktan Çalıştırma:** Celery worker'ların işlemleri kullanıcının bilgisayarında değil, oluşturulan AWS sunucusunda gerçekleştirmesi.

---

## ☸️ Faz 4: Orkestrasyon ve Enterprise Mimari (Kubernetes)

_Platformun ölçeklenebilir bir deve dönüştüğü, gerçek DevOps pratiklerinin uygulandığı zirve noktası._

- **AWS ECR (Elastic Container Registry):** Oluşturulan Docker imajlarının sunucuda değil, güvenli bir bulut deposunda (Registry) saklanması.
- **Kubernetes (AWS EKS) Geçişi:** Raw Docker komutlarını bırakıp; uygulamaları K8s Pod'ları ve Deployment'ları olarak ayağa kaldırma.
- **Alan Adı (Domain) ve Ingress Yönetimi:** Kullanıcılara `app1.cloudforge.com` gibi alt alan adları atama ve ağ trafiğini Kubernetes Ingress üzerinden ilgili uygulamaya yönlendirme.

---

## 📊 Faz 5: Gözlemlenebilirlik (Observability)

- **Sistem Metrikleri:** Çalışan konteyner/pod'ların anlık CPU ve RAM tüketim verilerini toplayıp React arayüzünde grafiksel (basit metrikler) olarak sunma.
