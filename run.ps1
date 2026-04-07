# Run project helper for Windows PowerShell
# Usage: Open PowerShell in project root and run: .\run.ps1

param(
  [switch]$RecreateVenv,
  [switch]$InstallExtras
)

$venvPath = ".venv"

function Ensure-Venv {
    if ($RecreateVenv -or -not (Test-Path $venvPath)) {
        Write-Host "Creating virtual environment at $venvPath..."
        python -m venv $venvPath
    } else {
        Write-Host "Virtual environment exists at $venvPath"
    }
}

function Activate-Venv {
    Write-Host "Activating virtual environment..."
    & "$venvPath\Scripts\Activate.ps1"
}

function Install-Dependencies {
    Write-Host "Upgrading pip and installing requirements..."
    python -m pip install --upgrade pip
    if (Test-Path requirements.txt) {
        python -m pip install -r requirements.txt
    } else {
        Write-Host "requirements.txt not found; skipping."
    }
    # Dev/test deps
    python -m pip install pytest requests pillow -q
    if ($InstallExtras) {
        Write-Host "Installing optional heavy extras: pyannote.audio resemblyzer"
        python -m pip install pyannote.audio resemblyzer
    }
}

function Start-Server {
    Write-Host "Starting FastAPI server on http://127.0.0.1:8000"
    python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
}

# Main
Ensure-Venv
Activate-Venv
Install-Dependencies
Start-Server
