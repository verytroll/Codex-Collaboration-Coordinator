$ErrorActionPreference = "Stop"

python -m app.services.docs_registry_check
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
