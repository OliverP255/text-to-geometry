# Rendering Setup

## Quick Start (single server)

```bash
./run.sh
```

Then open **http://localhost:5001** in your browser. Run the chatbot on the GPU to update the scene.

## Alternative: Vite dev server

1. **Start Flask** (scene server): `python server.py`
2. **Start Vite**: `cd web && npm run dev`
3. Open **http://localhost:5173** (or the port Vite shows)
4. Run the chatbot on the GPU

## SSH tunnel (GPU → local)

When running the chatbot on a remote GPU, use reverse port forwarding so the chatbot can reach your local Flask:

```bash
ssh -p PORT root@HOST -L 8080:localhost:8080 -R 5001:localhost:5001
```

- `-R 5001` lets the GPU POST to your local Flask at port 5001
- Ensure Flask is running locally before running the chatbot

## Troubleshooting

- **Connection error**: Ensure Flask is running on port 5001
- **Wrong port**: Stop any process on 5001 (`lsof -i :5001`) and restart
