"""AWS Lambda entry point for Guy's WhatsApp webhook.

Wraps the FastAPI app (backend.app.main:app) with Mangum so API Gateway (HTTP
API) events drive it. lifespan="off" skips the startup demo-script seed — the
production scripts are seeded into DynamoDB by a separate one-time step.

CodeUri is the repo root (guy/), so /var/task is on sys.path and the package
imports (backend / agents / database / tools / shared_env) resolve unchanged.
Storage is selected by STORAGE_BACKEND=dynamodb via the function's env vars.
"""

from mangum import Mangum

from backend.app.main import app

handler = Mangum(app, lifespan="off")
