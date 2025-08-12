from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from acontext_server import __version__
from acontext_server.api import V1_ROUTER
from acontext_server.env import LOG
from acontext_server.client.db import init_database, close_database
from acontext_server.client.redis import init_redis, close_redis


def configure_logging():
    # Configure uvicorn's loggers to use your format
    uvicorn_access = logging.getLogger("uvicorn.access")

    # Clear existing handlers
    uvicorn_access.handlers.clear()

    uvicorn_access.name = "acontext"

    # Add your custom handler to uvicorn loggers
    custom_handler = LOG.handlers[0] if LOG.handlers else None
    if custom_handler:
        uvicorn_access.addHandler(custom_handler)

    # Set log levels
    uvicorn_access.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure logging on startup
    configure_logging()
    await init_database()
    await init_redis()
    yield
    await close_database()
    await close_redis()


app = FastAPI(lifespan=lifespan, version=__version__)
app.include_router(V1_ROUTER)
