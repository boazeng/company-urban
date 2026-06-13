"""AWS Lambda entry point for Guy's WhatsApp webhook.

Wraps the FastAPI app (backend.app.main:app) with Mangum. lifespan="off" skips
the startup demo-script seed.

API Gateway (HTTP API) with a named stage prefixes the request path with the
stage (e.g. /prod/api/whatsapp/webhook). FastAPI's routes are /api/... , so we
strip the stage from the event before Mangum maps it — mirroring how urbangroup
handles the same thing. CodeUri is the repo root (guy/), so /var/task is on
sys.path and the package imports resolve unchanged.
"""

from mangum import Mangum

from backend.app.main import app

_mangum = Mangum(app, lifespan="off")


def handler(event, context):
    rc = event.get("requestContext", {})
    stage = rc.get("stage")
    if stage and stage != "$default":
        prefix = f"/{stage}"
        raw = event.get("rawPath", "")
        if raw.startswith(prefix):
            event["rawPath"] = raw[len(prefix):] or "/"
        http = rc.get("http", {})
        path = http.get("path", "")
        if path.startswith(prefix):
            http["path"] = path[len(prefix):] or "/"
    return _mangum(event, context)
