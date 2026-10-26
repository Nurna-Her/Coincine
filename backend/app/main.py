import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .api.endpoints import router, close_shared_driver, _driver_lock
from .core.logging import logger
from .core.database import create_db_and_tables

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend")
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

app = FastAPI(title="Coincine API", version="1.0.0")

# Reject requests whose Host is not local (protects against DNS rebinding)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])

@app.middleware("http")
async def reject_cross_origin_writes(request: Request, call_next):
    # The frontend is served from this same origin, so any other origin is a cross-site request
    origin = request.headers.get("origin")
    own_origin = f"{request.url.scheme}://{request.headers.get('host')}"
    if request.method not in SAFE_METHODS and origin and origin != own_origin:
        return JSONResponse(status_code=403, content={"detail": "Cross-origin request rejected"})
    return await call_next(request)

app.include_router(router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    logger.info("Coincine Backend Starting Up...")
    create_db_and_tables()


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Closing shared driver...")
    with _driver_lock:
        close_shared_driver()
    logger.info("Coincine Backend Shutting Down...")

# Serve the frontend last so it doesn't shadow /api routes
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
