# Project Tree Structure

Generated on 5/25/2026

```
└── 📁 DineFlow
    ├── 📁 addons
    │   ├── 📁 auto_database_backup
    │   │   ├── 📁 controllers
    │   │   │   ├── 📄 __init__.py
    │   │   │   └── 📄 auto_database_backup.py
    │   │   ├── 📁 data
    │   │   │   ├── 📄 ir_cron_data.xml
    │   │   │   └── 📄 mail_template_data.xml
    │   │   ├── 📁 doc
    │   │   │   └── 📝 RELEASE_NOTES.md
    │   │   ├── 📁 models
    │   │   │   ├── 📄 __init__.py
    │   │   │   └── 📄 db_backup_configure.py
    │   │   ├── 📁 security
    │   │   │   └── 📄 ir.model.access.csv
    │   │   ├── 📁 static
    │   │   │   └── 📁 description
    │   │   │       ├── 📁 assets
    │   │   │       │   ├── 📁 icons
    │   │   │       │   │   ......
    │   │   │       ├── 🖼️ banner.gif
    │   │   │       ├── 🖼️ icon.png
    │   │   │       └── 🌐 index.html
    │   │   ├── 📁 views
    │   │   │   └── 📄 db_backup_configure_views.xml
    │   │   ├── 📁 wizard
    │   │   │   ├── 📄 __init__.py
    │   │   │   ├── 📄 dropbox_auth_code_views.xml
    │   │   │   └── 📄 dropbox_auth_code.py
    │   │   ├── 📄 __init__.py
    │   │   ├── 📄 __manifest__.py
    │   │   └── 📄 README.rst
    │   ├── 📁 dineflow
    │   │   ├── 📁 controllers
    │   │   │   ├── 📄 __init__.py
    │   │   │   ├── 📄 chat.py
    │   │   │   └── 📄 main.py
    │   │   ├── 📁 data
    │   │   │   └── 📄 restaurant_data.xml
    │   │   ├── 📁 models
    │   │   │   ├── 📄 __init__.py
    │   │   │   ├── 📄 hr_employee.py
    │   │   │   ├── 📄 restaurant_ai_chat.py
    │   │   │   ├── 📄 restaurant_booking.py
    │   │   │   ├── 📄 restaurant_category.py
    │   │   │   ├── 📄 restaurant_leave.py
    │   │   │   ├── 📄 restaurant_menu_item.py
    │   │   │   ├── 📄 restaurant_order.py
    │   │   │   └── 📄 restaurant_table.py
    │   │   ├── 📁 report
    │   │   │   ├── 📄 __init__.py
    │   │   │   ├── 📄 leave_report_views.xml
    │   │   │   ├── 📄 restaurant_leave_report.py
    │   │   │   ├── 📄 restaurant_order_report.xml
    │   │   │   ├── 📄 restaurant_revenue_report.py
    │   │   │   └── 📄 revenue_report_views.xml
    │   │   ├── 📁 security
    │   │   │   ├── 📄 groups.xml
    │   │   │   └── 📄 ir.model.access.csv
    │   │   ├── 📁 static
    │   │   │   ├── 📁 description
    │   │   │   │   └── 🖼️ icon.png
    │   │   │   ├── 📁 src
    │   │   │   │   ├── 📁 components
    │   │   │   │   │   ├── 📁 ai_chat
    │   │   │   │   │   │   ├── 🎨 ai_chat.css
    │   │   │   │   │   │   ├── 📜 ai_chat.js
    │   │   │   │   │   │   └── 📄 ai_chat.xml
    │   │   │   │   │   └── 📄 a
    │   │   │   │   ├── 📁 css
    │   │   │   │   │   └── 🎨 dineflow.css
    │   │   │   │   └── 📄 z
    │   │   │   ├── 📄 a
    │   │   │   └── 📝 PROJECT_TREE.md
    │   │   ├── 📁 tests
    │   │   │   ├── 📄 __init__.py
    │   │   │   └── 📄 test_dineflow.py
    │   │   ├── 📁 views
    │   │   │   ├── 📄 booking_views.xml
    │   │   │   ├── 📄 employee_views.xml
    │   │   │   ├── 📄 leave_views.xml
    │   │   │   ├── 📄 menu_items.xml
    │   │   │   ├── 📄 menu_views.xml
    │   │   │   ├── 📄 order_views.xml
    │   │   │   └── 📄 table_views.xml
    │   │   ├── 📁 wizard
    │   │   │   ├── 📄 __init__.py
    │   │   │   ├── 📄 approve_leave_wizard.py
    │   │   │   ├── 📄 approve_leave_wizard.xml
    │   │   │   ├── 📄 cancel_booking_wizard.py
    │   │   │   ├── 📄 cancel_booking_wizard.xml
    │   │   │   ├── 📄 cancel_order_wizard.py
    │   │   │   ├── 📄 cancel_order_wizard.xml
    │   │   │   ├── 📄 payment_wizard.py
    │   │   │   └── 📄 payment_wizard.xml
    │   │   ├── 📄 __init__.py
    │   │   ├── 📄 __manifest__.py
    │   │   ├── 📜 a.js
    │   │   └── 📝 PROJECT_TREE.md
    │   ├── 📝 PROJECT_TREE.md
    │   └── 📝 readme.md
    ├── 📁 backup
    │   ├── 📄 backup_20260522_102923.sql
    │   ├── 📄 backup_20260522_155513.sql
    │   ├── 📄 backup_20260522_164104.sql
    │   ├── 📄 backup_20260522_164240.sql
    │   └── 📄 backup_20260525_020541.sql
    ├── 📁 etc
    │   ├── 📄 logrotate
    │   ├── 📄 odoo.conf
    │   └── 📄 requirements.txt
    ├── 📁 n8n
    │   └── 📊 dineflow_workflow.json
    ├── 📁 postgresql
    │   ├── 📁 base
    │   │   ├── 📁 1
    │   │   │   ├── ....
    │   ├── 📁 pg_commit_ts
    │   ├── 📁 pg_dynshmem
    │   ├── 📁 pg_logical
    │   │   ├── 📁 mappings
    │   │   ├── 📁 snapshots
    │   │   └── 📄 replorigin_checkpoint
    │   ├── 📁 pg_multixact
    │   │   ├── 📁 members
    │   │   │   └── 📄 0000
    │   │   └── 📁 offsets
    │   │       └── 📄 0000
    │   ├── 📁 pg_notify
    │   ├── 📁 pg_replslot
    │   ├── 📁 pg_serial
    │   ├── 📁 pg_snapshots
    │   ├── 📁 pg_stat
    │   ├── 📁 pg_stat_tmp
    │   ├── 📁 pg_subtrans
    │   │   └── 📄 0000
    │   ├── 📁 pg_tblspc
    │   ├── 📁 pg_twophase
    │   ├── 📁 pg_wal
    │   │   ├── 📁 archive_status
    │   │   ├── 📄 00000001000000000000001B
    │   │   ├── 📄 00000001000000000000001C
    │   │   ├── 📄 00000001000000000000001D
    │   │   ├── 📄 00000001000000000000001E
    │   │   └── 📄 00000001000000000000001F
    │   ├── 📁 pg_xact
    │   │   └── 📄 0000
    │   ├── 📄 pg_hba.conf
    │   ├── 📄 pg_ident.conf
    │   ├── 📄 PG_VERSION
    │   ├── 📄 postgresql.auto.conf
    │   ├── 📄 postgresql.conf
    │   ├── 📄 postmaster.opts
    │   └── 📄 postmaster.pid
    ├── 📁 screenshots
    │   ├── 🖼️ odoo-17-apps-screenshot.png
    │   ├── 🖼️ odoo-17-product-form.png
    │   ├── 🖼️ odoo-17-sales-screen.png
    │   └── 🖼️ odoo-17-welcome-screenshot.png
    ├── 📄 .gitattributes
    ├── 📄 .gitignore
    ├── 📄 build_and_run.sh
    ├── 📄 docker-compose.yml
    ├── 📄 Dockerfile.jenkins
    ├── 📄 entrypoint.sh
    ├── 📄 Jenkinsfile
    ├── 📝 PROJECT_TREE.md
    ├── 📝 README.md
    ├── 📝 READMEOLD.md
    └── 📄 run.sh
```
