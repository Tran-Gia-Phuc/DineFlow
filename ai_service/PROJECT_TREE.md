# Project Tree Structure

Generated on 5/25/2026

```
└── 📁 ai_service
    ├── 📁 agent
    │   ├── 📁 prompts
    │   │   └── 📄 system.txt
    │   ├── 📄 __init__.py
    │   ├── 📄 executor.py
    │   └── 📄 memory.py
    ├── 📁 job_queue
    │   ├── 📄 __init__.py
    │   └── 📄 worker.py
    ├── 📁 llm
    │   ├── 📄 __init__.py
    │   ├── 📄 fallback.py
    │   └── 📄 groq_client.py
    ├── 📁 middleware
    │   ├── 📄 __init__.py
    │   └── 📄 auth.py
    ├── 📁 pipeline
    │   ├── 📄 __init__.py
    │   └── 📄 selector.py
    ├── 📁 storage
    │   ├── 📄 __init__.py
    │   ├── 📄 chat_history.py
    │   └── 📄 job_tracker.py
    ├── 📁 tools
    │   ├── 📄 __init__.py
    │   ├── 📄 bookings.py
    │   ├── 📄 employees.py
    │   ├── 📄 leave.py
    │   ├── 📄 revenue.py
    │   └── 📄 tables.py
    ├── 📁 validator
    │   ├── 📄 __init__.py
    │   ├── 📄 sanitizer.py
    │   └── 📄 schema.py
    ├── 📄 __init__.py
    ├── 📄 .env
    ├── 📄 config.py
    ├── 📄 Dockerfile
    ├── 📄 main.py
    ├── 📝 PROJECT_TREE.md
    └── 📄 requirements.txt
```
