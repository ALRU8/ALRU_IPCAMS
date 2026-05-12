
set -e

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

. .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
python -m pip install -U pyinstaller

MODE=""
if [ "$1" = "--onefile" ]; then
  MODE="--onefile"
fi

pyinstaller $MODE --noconfirm --clean --windowed --name IPCameraViewer --collect-data onvif --collect-submodules onvif main.py
