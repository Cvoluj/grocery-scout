import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from curl_cffi import AsyncSession
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.broker import broker
from src.models.shops import ATBShop, VarusShop
from src.settings import LLM_SERVICE_API_KEY, LLM_SERVICE_URL
from src.tasks import search_atb_task, search_varus_task

BASE = Path(__file__).parent.parent
SHARED_DATA = BASE / "shared_data"

_atb_shops: list[dict] = json.loads((SHARED_DATA / "atb_shops.json").read_text(encoding="utf-8"))
_varus_shops: list[dict] = json.loads((SHARED_DATA / "varus_shops.json").read_text(encoding="utf-8"))
_atb_by_id: dict[int, dict] = {s["id"]: s for s in _atb_shops}
_varus_by_id: dict[int, dict] = {s["id"]: s for s in _varus_shops}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await broker.startup()
    yield
    await broker.shutdown()


app = FastAPI(title="Shop Search", lifespan=lifespan)


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "store_map.html")


@app.get("/checkout")
def checkout():
    return FileResponse(Path(__file__).parent / "checkout.html")


@app.get("/api/shops")
def get_shops():
    atb = [{**s, "brand": "atb"} for s in _atb_shops]
    varus = [{**s, "brand": "varus"} for s in _varus_shops]
    return atb + varus


# ── Search ────────────────────────────────────────────────────────────────────

class ShopRef(BaseModel):
    id: int
    brand: str


class SearchRequest(BaseModel):
    query: str
    shops: list[ShopRef]


@app.post("/api/search")
async def search(req: SearchRequest):
    atb_shops = [_atb_by_id[s.id] for s in req.shops if s.brand == "atb" and s.id in _atb_by_id]
    varus_shops = [_varus_by_id[s.id] for s in req.shops if s.brand == "varus" and s.id in _varus_by_id]

    jobs = await asyncio.gather(
        *[search_atb_task.kiq(shop, req.query) for shop in atb_shops],
        *[search_varus_task.kiq(shop, req.query) for shop in varus_shops],
    )

    results = await asyncio.gather(*[job.wait_result(timeout=30) for job in jobs])
    return [r.return_value for r in results]


# ── Match ─────────────────────────────────────────────────────────────────────

class ProductResult(BaseModel):
    id: str
    name: str
    price: float
    special_price: float | None = None
    in_stock: bool
    url: str
    image_url: str | None = None


class ShopResult(BaseModel):
    shop_id: int
    shop_name: str
    brand: str
    products: list[ProductResult]


class MatchRequest(BaseModel):
    results: list[ShopResult]
    mode: str = "strict"


@app.post("/api/match")
async def match(req: MatchRequest):
    shops = [
        {
            "shop_id": shop.shop_id,
            "shop_name": shop.shop_name,
            "brand": shop.brand,
            "products": [p.model_dump() for p in shop.products],
        }
        for shop in req.results
    ]

    async with AsyncSession() as session:
        resp = await session.post(
            f"{LLM_SERVICE_URL}/match",
            json={"shops": shops, "mode": req.mode},
            headers={"Authorization": f"Bearer {LLM_SERVICE_API_KEY}"},
        )
        resp.raise_for_status()

    return resp.json()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.server:app", host="0.0.0.0", port=8000, reload=True)
