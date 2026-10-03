# BeforeYouBuy

BeforeYouBuy checks a product page against your deal-breakers before you spend.

## Architecture

```text
Browser (React + Vite)
        |
        | POST /analyze
        v
FastAPI backend
  |-- URL safety + redirects + size limits
  |-- HTML/JSON-LD text extraction
  |-- mock parser or Anthropic JSON extraction
  '-- comparison + warnings + evidence filtering
        |
        v
      JSON result -> responsive comparison UI
```

## Prerequisites

- Python 3.11+ with `venv`
- Node.js 18+ and npm
- An Anthropic API key only if you want to use real AI mode

## Setup

### Windows PowerShell

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env

cd ..\frontend
npm install
```

### macOS/Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env

cd ../frontend
npm install
```

## Environment variables

Set these in `backend/.env`:

| Variable | Default | Purpose |
| --- | --- | --- |
| `USE_MOCK_AI` | `true` | Use deterministic local extraction when `true`. |
| `ANTHROPIC_API_KEY` | empty | Enables real Anthropic extraction when present and mock mode is `false`. |
| `ANTHROPIC_MODEL` | `claude-3-5-sonnet-latest` | Anthropic model name. |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated frontend origins. |
| `ALLOW_LOCAL_DEMO` | `true` | Allows the three local demo pages. |

Never commit a real API key.

## Run the app

After setup, the shortest path is:

```powershell
.\run-dev.ps1
```

or on macOS/Linux:

```bash
./run-dev.sh
```

The scripts open one backend and one frontend terminal. If you prefer separate terminals:

Backend:

```text
cd backend
.\.venv\Scripts\Activate.ps1       # Windows
source .venv/bin/activate          # macOS/Linux
uvicorn main:app --reload --port 8000
```

Frontend:

```text
cd frontend
npm run dev
```

Open the Vite URL, usually `http://localhost:5173`.

## Tests and build

Run backend tests from `backend` with the virtual environment active:

```text
pytest -q
```

Build the frontend from `frontend`:

```text
npm run build
```

## Demo links

Click one of the three demo buttons in the UI:

- `http://localhost:8000/demo/demo_match.html`
- `http://localhost:8000/demo/demo_noanc.html`
- `http://localhost:8000/demo/demo_missing.html`

The demo pages are served by the backend, so the backend must be running first.

## Mock and real AI

Mock mode is the default and needs no key:

```dotenv
USE_MOCK_AI=true
```

For real extraction, put a key in `backend/.env` and switch the flag:

```dotenv
ANTHROPIC_API_KEY=your_key_here
USE_MOCK_AI=false
```

The backend validates the model response against the product schema and retries once if the first response is not valid JSON. Evidence is retained only when the snippet occurs in the supplied page text.

## Paste-text fallback and limitations

JavaScript-heavy or bot-protected sites may fail because the backend reads server-delivered HTML and does not run a browser. Use **Page blocked? Paste page text instead** when that happens. Extracted specs can still be incomplete or ambiguous; always verify before buying. Requests to loopback, private, and link-local addresses are rejected.

## 30-second demo script

Use the default checklist (max ₹2,000, minimum 40 hours, ANC required, budget and ANC as deal-breakers), then click each link:

1. `http://localhost:8000/demo/demo_match.html` — say: “Everything passes: this is a great match.”
2. `http://localhost:8000/demo/demo_noanc.html` — say: “The price and battery pass, but missing ANC fails the deal-breaker.”
3. `http://localhost:8000/demo/demo_missing.html` — say: “The core checks pass, but the missing warranty and ‘up to’ battery claim need verification.”

The result page keeps the extracted evidence snippets visible under **What we found on the page**.
