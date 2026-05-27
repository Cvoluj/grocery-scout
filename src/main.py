from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from libs.pb_client import start_pb
from src import db
from src.auth.router import router as auth_router
from src.email.router import router as email_router
from src.broker import broker
from src.routers import shops, search
from src.settings import BASE_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_pb()
    await db.setup_pool()
    await broker.startup()
    yield
    await broker.shutdown()
    await db.teardown_pool()


app = FastAPI(title="Shop Search", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "src" / "static")), name="static")


app.include_router(shops.router)
app.include_router(search.router)
app.include_router(auth_router)
app.include_router(email_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
