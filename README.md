# NLSmusic-V4

NLSmusic V4 monorepo:

- `frontend/`: React + Vite + Tailwind + Framer Motion + Lucide UI
- `backend/`: FastAPI + Telethon + SQLite API layer

## Run frontend

```bash
cd frontend
npm install
npm run dev
```

## Run backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The backend uses `BOT_TOKEN`, `API_ID`, and `API_HASH` environment variables.
