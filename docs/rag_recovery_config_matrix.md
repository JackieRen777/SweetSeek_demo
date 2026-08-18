# RAG Recovery Configuration Matrix

This document intentionally excludes API keys and other secrets.

| Setting | Local development | Production constraint |
| --- | --- | --- |
| Hardware | Apple M1, 8 cores, 8 GB RAM | 2 vCPU, 3.5 GB RAM, 4 GB swap |
| Python | Project `venv`, Python 3.10 | Python 3.11 |
| HTTP runtime | Waitress, 4 threads, launchd | Gunicorn, 1 gevent worker |
| Automatic index build | Disabled | Disabled |
| Eager RAG initialization | Disabled | Disabled |
| Domain loading | One domain at a time | One domain at a time |
| Source-document batch | 5 | 2 for emergency-only server builds |
| Embedding batch | 8 | 8 or lower after memory measurement |
| Embedding/OpenMP threads | 1 (macOS libomp stability) | 1 |
| Build RSS guard | 5.5 GB | Build artifacts locally instead |
| Build disk guard | Start >= 12 GB; pause < 8 GB | Not applicable to normal deployment |
| Target index | FAISS vectors + SQLite chunks | Same verified artifact |

The four domains are `sweetness`, `dual_protein`, `encapsulation`, and
`proteoglycan`. Their indexes are isolated and switched atomically through each
domain's `current/` directory.
