from contextlib import asynccontextmanager
from fastapi import FastAPI
from libs.pb_client import start_pb
from routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_pb()
    yield

app = FastAPI(title="LLM Matcher Service", lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)