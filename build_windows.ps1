param(
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"

if (!(Test-Path ".venv")) {
    python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -U pyinstaller

$pyinstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name", "IPCameraViewer",
    "--collect-data", "onvif",
    "--collect-submodules", "onvif",
    "main.py"
)

if ($OneFile) {
    $pyinstallerArgs = @("--onefile") + $pyinstallerArgs
}

.\.venv\Scripts\pyinstaller.exe @pyinstallerArgs
