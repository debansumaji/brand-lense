# Run both servers

Use two terminals from the repository root.

Terminal 1 — backend:

```powershell
cd backend
..\.python\python.exe -m uvicorn main:app --reload --port 8000
```

Terminal 2 — frontend:

```powershell
cd frontend
npm run dev
```

On macOS/Linux, replace the Python path with the available Python executable.
If you created a virtual environment, use its Python executable instead.
The root `run-dev.ps1` and `run-dev.sh` scripts automatically prefer the
virtual environment and fall back to the bundled Python runtime when present.
