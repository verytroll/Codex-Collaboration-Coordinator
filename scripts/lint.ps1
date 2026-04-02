$ErrorActionPreference = "Stop"

python -m ruff check .
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python -m ruff format --check .
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python -m app.services.docs_registry_check
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
