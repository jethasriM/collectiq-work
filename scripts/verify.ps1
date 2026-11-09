$ErrorActionPreference = "Stop"
python -m py_compile backend/app/*.py
Push-Location backend
python -m pytest -q
Pop-Location
Push-Location frontend
npm run test
npm run build
Pop-Location
