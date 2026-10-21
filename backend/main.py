import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from app.api.router import api_router
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.core.redis import listen_redis_events
from app.db.session import close_mongo_connection, connect_to_mongo, init_db

# Initialize logging configuration
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager handling startup and shutdown events."""
    logger.info("Starting %s in %s mode...", settings.PROJECT_NAME, settings.ENVIRONMENT)
    try:
        await connect_to_mongo()
        await init_db()
    except Exception as exc:
        logger.warning("MongoDB initial connection notice: %s. Application continuing startup.", str(exc))

    # Start background task scheduler ONLY after DB is ready
    try:
        from app.worker import start_scheduler
        start_scheduler()
    except Exception as exc:
        logger.warning("Scheduler startup notice: %s. Continuing startup without background scheduler.", str(exc))

    # Start Redis Pub/Sub listener background task
    redis_task = asyncio.create_task(listen_redis_events())

    yield

    logger.info("Shutting down %s...", settings.PROJECT_NAME)

    # Stop the scheduler cleanly
    try:
        from app.worker import stop_scheduler
        stop_scheduler()
    except Exception as e:
        logger.warning("Error stopping scheduler: %s", str(e))

    redis_task.cancel()
    try:
        await redis_task
    except asyncio.CancelledError:
        pass
    await close_mongo_connection()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Trust reverse proxy headers (Render, Cloudflare, ALB) for SSL/TLS and WebSocket (wss://) termination
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# Clean and normalize allowed origins to strip whitespace and trailing slashes
raw_origins = settings.ALLOWED_ORIGINS
allowed_origins: list[str] = []

if isinstance(raw_origins, str):
    allowed_origins = [orig.strip().rstrip("/") for orig in raw_origins.split(",") if orig.strip()]
elif isinstance(raw_origins, (list, tuple, set)):
    allowed_origins = [str(orig).strip().rstrip("/") for orig in raw_origins if str(orig).strip()]

# Mount dynamic CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


# Direct /health endpoint for convenience
@app.get("/health", status_code=200, tags=["Health"])
def root_health_check():
    """Root level health check endpoint."""
    return {
        "status": "ok",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
