from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.endpoints import router, _shared_driver
from .core.logging import logger

app = FastAPI(title="Coincine API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    logger.info("Coincine Backend Starting Up...")

@app.on_event("shutdown")
async def shutdown_event():
    global _shared_driver
    if _shared_driver:
        logger.info("Closing shared driver...")
        _shared_driver.quit()
    logger.info("Coincine Backend Shutting Down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
