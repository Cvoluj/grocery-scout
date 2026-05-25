import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from libs.pb_client import PocketBaseClient
from src.settings import runtime
from src.broker import broker
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pb = PocketBaseClient()
    await pb.auth()

    # початкове завантаження
    settings = await pb.get_settings()
    runtime.load(settings)
    logger.info("Runtime settings loaded from PocketBase")

    # realtime у фоні
    async def realtime_loop():
        while True:
            try:
                await pb.subscribe()
            except Exception:
                logger.exception("Realtime disconnected, reconnecting in 5s")
                await asyncio.sleep(5)

    task = asyncio.create_task(realtime_loop())

    await broker.startup()
    yield
    await broker.shutdown()

    task.cancel()