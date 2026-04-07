Quick run instructions (Windows PowerShell)

1) Create + activate venv (only once)

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
```

2) Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest requests pillow
```

3) Start the app

```powershell
# Preferred: try port 8000 first
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload

# If you see a WinError 10013 (socket permission / reserved port), use the fallback port 8001:
python -m uvicorn app:app --host 127.0.0.1 --port 8001 --reload
```

4) Quick test (fast-path)

```powershell
# Fast-path (try 8000, or 8001 if you started the server on the fallback port)
curl -F "image=@C:\path\to\test.jpg" -F "claim=test" -F "fast=true" http://127.0.0.1:8000/analyze/image
# If using fallback port:
curl -F "image=@C:\path\to\test.jpg" -F "claim=test" -F "fast=true" http://127.0.0.1:8001/analyze/image
```

Alternative: use the provided `run.ps1` script:

```powershell
.\run.ps1
# or
.\run.ps1 -RecreateVenv
.\run.ps1 -InstallExtras
```

Smoke tests (quick checks):

```powershell
# Health check
curl http://127.0.0.1:8001/status

# Quick image upload (fast-mode)
curl -F "image=@C:\path\to\test.jpg" -F "claim=test" -F "fast=true" http://127.0.0.1:8001/analyze/image
```
