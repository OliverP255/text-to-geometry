# Print backend

On-demand print job API, database models, auth helpers, Discord notifications, and mesh validation live **here**, not under `agent/`.

- `print_backend.printing` — validation and cost/time heuristics for meshes (trimesh).
- `print_backend.routes_api` — Flask blueprint under `/api` (registered from root `server.py`).
- `print_backend.job_service` — STL generation (uses `agent/` mesh and B-Rep exporters on `PYTHONPATH`).

The `agent/` package remains focused on LLM / WGSL / CadQuery generation.

Environment variables are documented in `.env.example` at the repository root.