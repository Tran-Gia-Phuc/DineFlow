# DineFlow - Makefile
# Dùng: make <command>

.PHONY: up down restart logs shell db-shell rebuild clean

## Khởi động
up:
	docker compose up -d

## Tắt
down:
	docker compose down

## Khởi động lại
restart:
	docker compose restart odoo

## Xem log realtime
logs:
	docker compose logs -f odoo

## Xem log cả 2 service
logs-all:
	docker compose logs -f

## Vào shell của Odoo container
shell:
	docker compose exec odoo bash

## Vào psql của DB
db-shell:
	docker compose exec db psql -U odoo -d odoo

## Build lại từ đầu (xóa image cache)
rebuild:
	docker compose down
	docker compose build --no-cache
	docker compose up -d

## Xóa toàn bộ data (NGUY HIỂM - reset DB)
clean:
	docker compose down -v
	@echo "Đã xóa toàn bộ volumes. Lần sau chạy 'make up' sẽ setup lại từ đầu."

## Cài module mới (sau khi thêm vào addons/)
install-module:
	@read -p "Tên module: " module; \
	docker compose exec odoo odoo -d odoo --stop-after-init -i $$module

## Update module
update-module:
	@read -p "Tên module: " module; \
	docker compose exec odoo odoo -d odoo --stop-after-init -u $$module

## Trạng thái containers
status:
	docker compose ps
