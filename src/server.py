import asyncio
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.atb_api.client import ATBClient
from src.llm_match import LLMMatcher
from src.models.products import Product
from src.models.shops import ATBShop, VarusShop
from src.varus_api.client import VarusClient

BASE = Path(__file__).parent.parent
SHARED_DATA = BASE / "shared_data"

_atb_shops: list[dict] = json.loads((SHARED_DATA / "atb_shops.json").read_text(encoding="utf-8"))
_varus_shops: list[dict] = json.loads((SHARED_DATA / "varus_shops.json").read_text(encoding="utf-8"))
_atb_by_id: dict[int, dict] = {s["id"]: s for s in _atb_shops}
_varus_by_id: dict[int, dict] = {s["id"]: s for s in _varus_shops}

app = FastAPI(title="Shop Search")


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


class ShopRef(BaseModel):
    id: int
    brand: str


class SearchRequest(BaseModel):
    query: str
    shops: list[ShopRef]


async def _search_atb(refs: list[ShopRef], query: str) -> list[dict]:
    client = ATBClient()
    shop_objs, tasks = [], []
    for ref in refs:
        raw = _atb_by_id.get(ref.id)
        if not raw:
            continue
        shop = ATBShop(
            id=raw["id"], short_name=raw["short_name"],
            lat=raw["lat"], lon=raw["lon"],
            address=raw["address"], worktime=raw.get("worktime", ""),
        )
        shop_objs.append(shop)
        tasks.append(client.search_in_shop(shop, query))
    found = await asyncio.gather(*tasks, return_exceptions=True)
    results = []
    for shop, products in zip(shop_objs, found):
        if isinstance(products, Exception):
            products = []
        results.append({
            "shop_id": shop.id,
            "shop_name": f"АТБ — {shop.short_name}",
            "brand": "atb",
            "products": [_atb_product(p) for p in products],
        })
    return results


async def _search_varus(refs: list[ShopRef], query: str) -> list[dict]:
    client = VarusClient()
    shop_objs, tasks = [], []
    for ref in refs:
        raw = _varus_by_id.get(ref.id)
        if not raw:
            continue
        shop = VarusShop(
            id=raw["id"], tms_id=raw["tms_id"],
            short_name=raw["short_name"],
            lat=raw["lat"], lon=raw["lon"],
            address=raw["address"],
        )
        shop_objs.append(shop)
        tasks.append(client.search_in_shop(shop, query))
    found = await asyncio.gather(*tasks, return_exceptions=True)
    results = []
    for shop, products in zip(shop_objs, found):
        if isinstance(products, Exception):
            products = []
        results.append({
            "shop_id": shop.id,
            "shop_name": shop.short_name,
            "brand": "varus",
            "products": [_varus_product(p) for p in products],
        })
    return results


def _atb_product(p) -> dict:
    return {
        "id": p.id, "name": p.name,
        "price": p.price, "special_price": p.special_price,
        "in_stock": p.in_stock, "url": p.url, "image_url": p.image_url,
    }


def _varus_product(p) -> dict:
    return {
        "id": p.id, "name": p.name,
        "price": p.price, "special_price": p.special_price,
        "in_stock": p.in_stock, "url": p.url, "image_url": p.image_url,
    }


@app.post("/api/search")
async def search(req: SearchRequest):
    atb_refs = [s for s in req.shops if s.brand == "atb"]
    varus_refs = [s for s in req.shops if s.brand == "varus"]

    atb_results, varus_results = await asyncio.gather(
        _search_atb(atb_refs, req.query),
        _search_varus(varus_refs, req.query),
    )
    return atb_results + varus_results


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


def _prepare_for_matching(results: list[ShopResult]):
    """
    Returns:
      matcher_input  — {(brand, 0): [Product]}  one entry per brand,
                       products deduplicated by id (any representative).
      shop_lookup    — {(brand, product_id): [shop_offer]}  every shop
                       that carries the product with its own price.
    """
    brand_products: dict[str, dict[str, Product]] = {}
    shop_lookup: dict[tuple[str, str], list[dict]] = {}

    for shop in results:
        brand = shop.brand
        brand_products.setdefault(brand, {})

        for p in shop.products:
            actual = p.special_price if p.special_price is not None else p.price
            key = (brand, p.id)

            shop_lookup.setdefault(key, []).append({
                "shop_id": shop.shop_id,
                "shop_name": shop.shop_name,
                "price": p.price,
                "special_price": p.special_price,
                "actual_price": actual,
            })

            if p.id not in brand_products[brand]:
                brand_products[brand][p.id] = Product(
                    id=p.id, store=brand, name=p.name,
                    price=p.price, special_price=p.special_price,
                    in_stock=p.in_stock, url=p.url, image_url=p.image_url,
                )

    matcher_input = {
        (brand, 0): list(products.values())
        for brand, products in brand_products.items()
    }
    return matcher_input, shop_lookup


@app.post("/api/match")
async def match(req: MatchRequest):
    matcher_input, shop_lookup = _prepare_for_matching(req.results)
    matched = await LLMMatcher().match(matcher_input)

    output = []
    for m in matched:
        offers = {}
        for (store, _), product in m.offers.items():
            shops = shop_lookup.get((store, product.id), [])
            for shop in sorted(shops, key=lambda s: s["actual_price"]):
                key = f"{store}_{shop['shop_id']}"
                offers[key] = {
                    "brand": store,
                    "shop_id": shop["shop_id"],
                    "shop_name": shop["shop_name"],
                    "product_id": product.id,
                    "name": product.name,
                    "url": product.url,
                    "image_url": product.image_url,
                    "price": shop["price"],
                    "special_price": shop["special_price"],
                    "actual_price": shop["actual_price"],
                }
        output.append({"canonical": m.canonical_name, "offers": offers})

    return output


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.server:app", host="0.0.0.0", port=8000, reload=True)
