# Project Tree Structure

Generated on 5/27/2026

```
└── 📁 ai_service
    ├── 📁 __pycache__
    │   ├── 📄 config.cpython-310.pyc
    │   ├── 📄 config.cpython-311.pyc
    │   ├── 📄 main.cpython-310.pyc
    │   └── 📄 main.cpython-311.pyc
    ├── 📁 agent
    │   ├── 📁 __pycache__
    │   │   ├── 📄 __init__.cpython-311.pyc
    │   │   ├── 📄 callbacks.cpython-311.pyc
    │   │   ├── 📄 executor.cpython-311.pyc
    │   │   ├── 📄 memory.cpython-311.pyc
    │   │   └── 📄 token_counter.cpython-311.pyc
    │   ├── 📁 prompts
    │   │   └── 📄 system.txt
    │   ├── 📄 __init__.py
    │   ├── 📄 callbacks.py
    │   ├── 📄 executor.py
    │   ├── 📄 memory.py
    │   └── 📄 token_counter.py
    ├── 📁 job_queue
    │   ├── 📁 __pycache__
    │   │   ├── 📄 __init__.cpython-310.pyc
    │   │   ├── 📄 __init__.cpython-311.pyc
    │   │   └── 📄 worker.cpython-311.pyc
    │   ├── 📄 __init__.py
    │   └── 📄 worker.py
    ├── 📁 llm
    │   ├── 📁 __pycache__
    │   │   ├── 📄 __init__.cpython-311.pyc
    │   │   ├── 📄 fallback.cpython-311.pyc
    │   │   └── 📄 groq_client.cpython-311.pyc
    │   ├── 📄 __init__.py
    │   ├── 📄 fallback.py
    │   └── 📄 groq_client.py
    ├── 📁 middleware
    │   ├── 📁 __pycache__
    │   │   ├── 📄 __init__.cpython-310.pyc
    │   │   ├── 📄 __init__.cpython-311.pyc
    │   │   ├── 📄 auth.cpython-310.pyc
    │   │   └── 📄 auth.cpython-311.pyc
    │   ├── 📄 __init__.py
    │   └── 📄 auth.py
    ├── 📁 pipeline
    │   ├── 📁 __pycache__
    │   │   ├── 📄 __init__.cpython-311.pyc
    │   │   └── 📄 selector.cpython-311.pyc
    │   ├── 📄 __init__.py
    │   └── 📄 selector.py
    ├── 📁 storage
    │   ├── 📁 __pycache__
    │   │   ├── 📄 __init__.cpython-311.pyc
    │   │   ├── 📄 chat_history.cpython-311.pyc
    │   │   └── 📄 job_tracker.cpython-311.pyc
    │   ├── 📄 __init__.py
    │   ├── 📄 chat_history.py
    │   └── 📄 job_tracker.py
    ├── 📁 streaming
    │   ├── 📁 __pycache__
    │   │   ├── 📄 __init__.cpython-311.pyc
    │   │   └── 📄 sse_manager.cpython-311.pyc
    │   ├── 📄 __init__.py
    │   └── 📄 sse_manager.py
    ├── 📁 tools
    │   ├── 📁 __pycache__
    │   │   ├── 📄 __init__.cpython-311.pyc
    │   │   ├── 📄 bookings.cpython-311.pyc
    │   │   ├── 📄 employees.cpython-311.pyc
    │   │   ├── 📄 leave.cpython-311.pyc
    │   │   ├── 📄 revenue.cpython-311.pyc
    │   │   └── 📄 tables.cpython-311.pyc
    │   ├── 📄 __init__.py
    │   ├── 📄 bookings.py
    │   ├── 📄 employees.py
    │   ├── 📄 leave.py
    │   ├── 📄 revenue.py
    │   └── 📄 tables.py
    ├── 📁 validator
    │   ├── 📁 __pycache__
    │   │   ├── 📄 __init__.cpython-311.pyc
    │   │   ├── 📄 sanitizer.cpython-311.pyc
    │   │   └── 📄 schema.cpython-311.pyc
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
