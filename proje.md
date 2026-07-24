# 🗺️ CloudForge: Proje Yol Haritası ve Mimari Tasarım

## 📖 Proje Vizyonu
CloudForge, yazılımcıların altyapı (sunucu, ağ, orkestrasyon) detaylarıyla uğraşmadan, yalnızca GitHub repo linklerini vererek uygulamalarını saniyeler içinde canlıya almalarını sağlayan minimal bir "Internal Developer Platform" (IDP) projesidir.

Amacımız ticari bir ürün geliştirmek değil; sistem tasarımı, konteynerizasyon (Docker), orkestrasyon (Kubernetes) ve bulut mimarisi (AWS, Terraform) konularında derinlemesine pratik mühendislik tecrübesi kazanmaktır. Geliştirme süreci **"Sadece İhtiyacın Olduğunda Öğren" (Just-in-Time Learning)** felsefesine dayanmaktadır.

---

## 🎯 v0.1: Minimum Viable Product (MVP) - "Yerel Çekirdek"
*İlk aşamada AWS, Kubernetes, kullanıcı girişleri, veri tabanları ve karmaşık ağ ayarları tamamen kapsam dışıdır. Her şey yerel bilgisayarda (localhost) çalışacaktır.*

### Kapsam ve Teknolojiler
| Bileşen | Teknoloji | Görev Tanımı |
| :--- | :--- | :--- |
| **Frontend (Vitrin)** | React + Tailwind CSS | Kullanıcıdan GitHub linkini alacak temiz, tek sayfalık bir form arayüzü. |
| **Backend (API)** | Python (FastAPI) | Arayüzden gelen istekleri karşılayan ve iş mantığını yürüten ana trafik polisi. |
| **Engine (Motor)** | Python (`GitPython`, `docker-py`) | Kodu klonlayan, dilini analiz eden, dinamik `Dockerfile` üreten ve yerel Docker Daemon üzerinde ayağa kaldıran işçi modülü. |

### 🏆 v0.1 Başarı Kriteri (Success Criteria)
Sisteme sadece `main.py` ve `requirements.txt` içeren basit bir test reposunun linki verilecek. Sistem arkada kodları çekecek, Docker imajını oluşturacak, çalıştıracak ve kullanıcıya uygulamasının çalıştığı portu (örn: `localhost:8055`) geri dönecektir. Kullanıcı bu porta gittiğinde uygulamanın başarıyla çalıştığını görecektir.

### 📝 v0.1 Adımları
- [ ] **Adım 1:** FastAPI ile proje iskeletinin kurulması ve `/deploy` uç noktasının (endpoint) oluşturulması.
- [ ] **Adım 2:** React ve Tailwind CSS ile GitHub linkini alıp API'ye post edecek basit UI'ın hazırlanması.
- [ ] **Adım 3:** API'ye gelen GitHub linkinin geçici bir klasöre (`tempfile`) klonlanması.
- [ ] **Adım 4:** Klonlanan proje içinde `requirements.txt` (Python) veya `package.json` (Node.js) aranarak dilin tespit edilmesi.
- [ ] **Adım 5:** Tespit edilen dile uygun standart bir `Dockerfile` dosyasının otomatik olarak proje klasörüne yazılması.
- [ ] **Adım 6:** `docker-py` kullanılarak bu klasördeki kodların Docker imajına dönüştürülmesi (`build`).
- [ ] **Adım 7:** İmajın `docker run` ile bir konteyner olarak ayağa kaldırılması ve açık olan bir portun arayüze döndürülmesi.

---

## 🚀 Faz 1: Asenkron İşlem ve Kuyruk Yönetimi (Scaling)
*API'nin kilitlenmesini önlemek için arka plan işçilerinin sisteme dahil edilmesi.*

- [ ] **Redis ve Celery Entegrasyonu:** Uzun süren derleme (build) işlemlerinin kuyruğa alınması.
- [ ] **WebSocket ile Canlı Loglar:** Docker build sürecindeki logların anlık olarak React arayüzüne akıtılması.

---

## 🌍 Faz 2: Bulut ve Orkestrasyon (AWS & Kubernetes)
*Yerelde çalışan kusursuz sistemin, "Kara Kutu" (Black Box) mantığıyla Terraform kullanılarak buluta taşınması.*

- [ ] **Terraform ile Altyapı:** AWS VPC ve ağ bileşenlerinin kodla oluşturulması.
- [ ] **AWS ECR Entegrasyonu:** Yerelde oluşan Docker imajlarının AWS Container Registry'e push edilmesi.
- [ ] **Lokal Kubernetes (Minikube):** Python `kubernetes` kütüphanesi ile konteynerin Minikube üzerinde Pod olarak kaldırılması.
- [ ] **AWS EKS'e Geçiş:** Minikube üzerinde test edilen yapının Terraform ile kurulan AWS Kubernetes cluster'ına taşınması.

---

## 🛡️ Faz 3: Ağ Yönetimi ve Güvenlik (Production Ready)
*Gerçek bir ürün hissi vermek için yönlendirmelerin yapılması.*

- [ ] **Ingress Controller (NGINX):** Uygulamaların dış dünyaya açılması.
- [ ] **Dinamik Alt Alan Adı (Subdomain):** Her uygulamaya özel link oluşturulması (örn: `test-app.cloudforge.local`).
- [ ] **(Opsiyonel) Cert-Manager:** Gerçek alan adları için Let's Encrypt ile otomatik SSL sertifikası üretimi.