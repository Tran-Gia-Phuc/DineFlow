# 🍜 DineFlow — Restaurant Management System

Hệ thống quản lý nhà hàng xây dựng trên **Odoo 17** + **PostgreSQL 15** + **Docker**.

---

## 🚀 Quick Start

### 1. Clone & setup config

```bash
git clone <your-repo-url>
cd DineFlow

# Copy file config mẫu
cp config/odoo.conf.example config/odoo.conf

# Sửa password trong odoo.conf nếu muốn (mặc định đã có sẵn cho local)
```

### 2. Chạy

```bash
# Khởi động
make up

# Hoặc không có make:
docker compose up -d
```

### 3. Truy cập

| Service | URL |
|---|---|
| Odoo | http://localhost:8069 |
| Database manager | http://localhost:8069/web/database/manager |

Lần đầu chạy → vào `/web/database/manager` → tạo database mới với tên `odoo`.

---

## 📁 Cấu trúc thư mục

```
DineFlow/
├── addons/                  # Custom modules (sẽ build ở đây)
│   └── dineflow_restaurant/ # Module chính (coming soon)
├── config/
│   ├── odoo.conf            # Config thật (gitignored)
│   └── odoo.conf.example    # Config mẫu (commit lên git)
├── docker-compose.yml
├── Makefile                 # Shortcuts
└── README.md
```

---

## 🛠 Các lệnh thường dùng

```bash
make up              # Bật containers
make down            # Tắt containers
make logs            # Xem log Odoo
make shell           # Vào bash trong Odoo container
make db-shell        # Vào psql
make restart         # Restart Odoo (sau khi sửa config)
make rebuild         # Build lại từ đầu
make clean           # Xóa hết data (RESET)
```

---

## 📦 Roadmap modules

- [ ] `dineflow_restaurant` — Core: bàn, món ăn, nhân viên, phân quyền
- [ ] Đặt bàn online (Odoo Website)
- [ ] Quản lý nghỉ phép
- [ ] CI/CD Jenkins
- [ ] Chat polling / Notification
- [ ] VNPay integration
- [ ] AI Agent chatbot

---

## ⚙️ Yêu cầu hệ thống

- Docker Desktop hoặc Docker Engine
- Docker Compose v2+
- RAM: 16GB (recommended) 

# Setup n8n Workflow

1. Vào http://localhost:31208
2. Tạo account admin
3. Click "Add workflow" → "Import from file"
4. Chọn file `dineflow_workflow.json`
5. Cấu hình credentials:
   - Groq API Key: [tạo tại console.groq.com]
6. Click Publish/Activate