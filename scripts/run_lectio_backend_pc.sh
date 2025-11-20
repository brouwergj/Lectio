#!/usr/bin/env bash
set -e

# Run the Lectio backend on your Windows PC from a Bash shell (e.g. VS Code).

# Move to repo root (script is in scripts/)
cd "$(dirname "$0")/.." || exit 1

# Activate the local virtual environment if available
if [ -f ".venv/Scripts/activate" ]; then
  # shellcheck disable=SC1091
  source ".venv/Scripts/activate"
fi

# Default to the WSL2-hosted stack on this PC
export OLLAMA_URL="${OLLAMA_URL:-http://192.168.178.237:11434}"
export QDRANT_URL="${QDRANT_URL:-http://192.168.178.237:6333}"
export QDRANT_COLLECTION="${QDRANT_COLLECTION:-lectio_corpus}"

powershell.exe -NoProfile -Command "Copy-Item 'D:\Work\Lectio\word-addin\manifest.xml' 'C:\OfficeAddins\lectio-manifest.xml' -Force"
python ./python/lectio_backend.py

