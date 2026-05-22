#!/bin/bash
set -e

# ==========================================
# CẤU HÌNH
# ==========================================
DB_NAME="intern"
ODOO_CONTAINER="dineflow-odoo-1"
DB_CONTAINER="dineflow-db-1"
ADDONS_DIR="/DineFlow/addons"        # ← path trong container jenkins
BACKUP_DIR="/DineFlow/backup"        # ← path trong container jenkins

# Telegram
TELEGRAM_TOKEN="8891955831:AAFlT0DQtN4pednHINba87bKRya3PH_Pi9o"
TELEGRAM_CHAT_ID="5594081068"

# ==========================================
# HÀM THÔNG BÁO TELEGRAM
# ==========================================
send_telegram() {
    local message=$1
    if [ "$TELEGRAM_TOKEN" != "YOUR_BOT_TOKEN" ]; then
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_TOKEN/sendMessage" \
            -d chat_id="$TELEGRAM_CHAT_ID" \
            -d text="$message" > /dev/null
    fi
}

echo "================================================"
echo "=== BẮT ĐẦU DEPLOY DINEFLOW ==="
echo "================================================"
send_telegram "🚀 Bắt đầu deploy DineFlow...
Commit: $GIT_COMMIT
Branch: $GIT_BRANCH"

# ==========================================
# BƯỚC 1 — Kiểm tra thay đổi
# ==========================================
echo "=== [1/4] Kiểm tra thay đổi ==="

CHANGED=$(git -C $WORKSPACE diff --name-only HEAD~1 HEAD 2>/dev/null | grep "^addons/" || true)

if [ -z "$CHANGED" ]; then
    echo "Không có thay đổi trong addons, bỏ qua deploy."
    send_telegram "ℹ️ Không có thay đổi addons
Bỏ qua deploy."
    exit 0
fi

send_telegram "📂 Phát hiện thay đổi:
$CHANGED"

# ==========================================
# BƯỚC 2 — Backup database
# ==========================================
echo "=== [2/4] Backup database '$DB_NAME' ==="
mkdir -p $BACKUP_DIR
BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql"
docker exec $DB_CONTAINER pg_dump -U odoo $DB_NAME > $BACKUP_FILE
ls -t $BACKUP_DIR/*.sql | tail -n +6 | xargs -r rm

send_telegram "💾 Backup database xong
📁 File: $BACKUP_FILE"

# ==========================================
# BƯỚC 3 — Sync addons
# ==========================================
echo "=== [3/4] Sync addons ==="
mkdir -p $ADDONS_DIR
cp -r $WORKSPACE/addons/. $ADDONS_DIR/

send_telegram "📦 Sync addons xong
✅ Code mới đã được copy vào server"

# ==========================================
# BƯỚC 4 — Restart + Update modules
# ==========================================
echo "=== [4/4] Restart và update modules ==="
docker restart $ODOO_CONTAINER
send_telegram "🔄 Docker restart $ODOO_CONTAINER...
⏳ Đợi Odoo khởi động (20s)"

sleep 20
docker exec $ODOO_CONTAINER odoo -u dineflow -d $DB_NAME --stop-after-init \
    --db_host=db --db_user=odoo --db_password=Phuc0312

send_telegram "✅ Update modules xong
🟢 Odoo đã sẵn sàng!"

echo "=== Check containers ==="
docker ps

echo "================================================"
echo "=== DEPLOY HOÀN THÀNH ==="
echo "================================================"
send_telegram "🎉 DEPLOY HOÀN THÀNH!
──────────────────
🗄️ Database: $DB_NAME
📌 Commit: $GIT_COMMIT
⏱️ Thời gian: $(date '+%H:%M:%S %d/%m/%Y')"