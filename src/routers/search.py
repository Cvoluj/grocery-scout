import asyncio

import asyncpg
from curl_cffi import AsyncSession
from fastapi import APIRouter, Depends, HTTPException

from libs.pb_client import runtime
from src.brands import registry
from src.auth.deps import get_current_user
from src.schemas.search import MatchRequest, SearchRequest

router = APIRouter(prefix="/api")


@router.post("/search")
async def search(req: SearchRequest, _: asyncpg.Record = Depends(get_current_user)):
    grouped = registry.resolve_shops(req.shops)

    if not grouped:
        raise HTTPException(status_code=422, detail="No enabled shops matched the request")

    jobs = await asyncio.gather(*[
        registry.get_task(brand).kiq(shop, req.query)
        for brand, shops in grouped.items()
        for shop in shops
    ])
    results = await asyncio.gather(*[job.wait_result(timeout=30) for job in jobs])
    return [r.return_value for r in results]


@router.post("/match")
async def match(req: MatchRequest, _: asyncpg.Record = Depends(get_current_user)):
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
