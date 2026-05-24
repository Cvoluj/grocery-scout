import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from llm_match import LLMMatcher, MatchMode
from dotenv import load_dotenv
load_dotenv()

LLM_SERVICE_API_KEY = os.environ["LLM_SERVICE_API_KEY"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
MODEL = os.getenv("LLM_MODEL", "groq/llama-3.3-70b-versatile")
PROMPTS_DIR = Path(__file__).parent / "prompts"

app = FastAPI(title="LLM Matcher Service")
bearer = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Security(bearer)):
    if credentials.credentials != LLM_SERVICE_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.credentials


class ProductIn(BaseModel):
    id: str
    name: str
    price: float
    special_price: float | None = None
    in_stock: bool = True
    url: str | None = None
    image_url: str | None = None


class ShopIn(BaseModel):
    shop_id: int
    shop_name: str
    brand: str
    products: list[ProductIn]


class MatchRequest(BaseModel):
    shops: list[ShopIn]
    mode: MatchMode = MatchMode.STRICT


matcher = LLMMatcher(model=MODEL, api_key=GROQ_API_KEY, prompts_dir=PROMPTS_DIR)


@app.post("/match")
async def match(req: MatchRequest, _token: str = Security(verify_token)):
    return await matcher.match_raw(
        shops=[s.model_dump() for s in req.shops],
        mode=req.mode,
    )


@app.get("/auth")
async def auth(_token: str = Security(verify_token)):
    return {"status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
