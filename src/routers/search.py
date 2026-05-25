import asyncio

from curl_cffi import AsyncSession
from fastapi import APIRouter

from libs.pb_client import runtime
from src.schemas.search import MatchRequest, SearchRequest
from src.store_data import atb_by_id, varus_by_id
from src.tasks import search_atb_task, search_varus_task

router = APIRouter(prefix="/api")


@router.post("/search")
async def search(req: SearchRequest):
    atb = [atb_by_id[s.id] for s in req.shops if s.brand == "atb" and s.id in atb_by_id]
    varus = [varus_by_id[s.id] for s in req.shops if s.brand == "varus" and s.id in varus_by_id]

    jobs = await asyncio.gather(
        *[search_atb_task.kiq(shop, req.query) for shop in atb],
        *[search_varus_task.kiq(shop, req.query) for shop in varus],
    )
    results = await asyncio.gather(*[job.wait_result(timeout=30) for job in jobs])
    return [r.return_value for r in results]


@router.post("/match")
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
            f"{runtime.get('LLM_SERVICE_URL')}/match",
            json={"shops": shops, "mode": req.mode},
            headers={"Authorization": f"Bearer {runtime.get('LLM_SERVICE_API_KEY')}"},
        )
        resp.raise_for_status()
    return resp.json()
