---
name: terraform
description: CloudForge'un AWS altyapısını (VPC, IAM, RDS, ElastiCache, ECR, EKS) Terraform ile `infrastructure/` altında yazma ve inceleme. roadmap_eks.md Aşama 2 işleri için kullan.
---

# Terraform (AWS)

## Bağlam
- `infrastructure/` klasörü şu an boş. Terraform kodu buraya yazılacak.
- Hedef kaynaklar (`roadmap_eks.md` Aşama 2): VPC + public/private subnet + IGW/NAT, IAM rolleri, RDS PostgreSQL 16, ElastiCache Redis 7, ECR, EKS cluster + node group.

## Önerilen yapı (ihtiyaç doğdukça oluştur, önceden boş modül açma)
```
infrastructure/
├── versions.tf      # terraform + provider sürüm kısıtları
├── providers.tf
├── variables.tf / outputs.tf
├── main.tf
└── modules/<network|eks|rds|...>   # sadece tekrar kullanım gerçekten varsa
```

## Kurallar
- Provider ve modül sürümlerini sabitle (`~>`).
- Secret'ları (DB şifresi vb.) `.tf` içine veya `terraform.tfvars` içine yazma. `sensitive = true` değişken, AWS Secrets Manager ya da `random_password` kullan.
- `*.tfstate`, `*.tfvars`, `.terraform/` Git'e girmemeli. Remote state (S3 + DynamoDB lock) öner.
- RDS ve ElastiCache private subnet'te olmalı, security group'lar sadece EKS node/pod SG'sinden erişime izin vermeli.
- IAM'de en az yetki prensibi. EKS pod'ları için IRSA kullan.
- Kaynaklara ortak `tags` (Project = "cloudforge", Environment) ekle.

## Kontrol
- `terraform fmt -check -recursive`
- `terraform init -backend=false && terraform validate`
- `terraform plan` gerçek AWS hesabına dokunur. Çalıştırmadan önce kullanıcıdan onay al. `apply`/`destroy` asla onaysız çalıştırılmaz.
