from src.broker import broker
from src.atb_api.client import ATBClient
from src.varus_api.client import VarusClient
from src.models.shops import ATBShop, VarusShop


@broker.task
async def search_atb_task(shop: dict, query: str) -> dict:
    client = ATBClient()
    products = await client.search_in_shop(ATBShop(**shop), query)
    return {
        "shop_id": shop["id"],
        "shop_name": f"АТБ — {shop['short_name']}",
        "brand": "atb",
        "products": [
            {
                "id": p.id, "name": p.name,
                "price": p.price, "special_price": p.special_price,
                "in_stock": p.in_stock, "url": p.url, "image_url": p.image_url,
            }
            for p in products
        ],
    }


@broker.task
async def search_varus_task(shop: dict, query: str) -> dict:
    client = VarusClient()
    products = await client.search_in_shop(VarusShop(**shop), query)
    return {
        "shop_id": shop["id"],
        "shop_name": shop["short_name"],
        "brand": "varus",
        "products": [
            {
                "id": p.id, "name": p.name,
                "price": p.price, "special_price": p.special_price,
                "in_stock": p.in_stock, "url": p.url, "image_url": p.image_url,
            }
            for p in products
        ],
    }
