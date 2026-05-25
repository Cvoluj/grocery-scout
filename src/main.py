from contextlib import asynccontextmanager

from fastapi import FastAPI

from libs.pb_client import start_pb
from src.broker import broker
from src.routers import shops, search


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_pb()
    await broker.startup()
    yield
    await broker.shutdown()


app = FastAPI(title="Shop Search", lifespan=lifespan)

app.include_router(shops.router)
app.include_router(search.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
