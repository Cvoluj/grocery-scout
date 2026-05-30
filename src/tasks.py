from src.broker import broker

from src.brands.atb.client import AtbClient
from src.brands.fora.client import ForaClient
from src.brands.varus.client import VarusClient

from src.models.shops import ATBShop, VarusShop, ForaShop



def _product_dict(p) -> dict:
    return {
        "id":            p.id,
        "name":          p.name,
        "price":         p.price,
        "special_price": p.special_price,
        "in_stock":      p.in_stock,
        "url":           p.url,
        "image_url":     p.image_url,
    }


@broker.task
async def search_atb_task(shop: dict, query: str) -> dict:
    client = AtbClient()
    products = await client.search_in_shop(ATBShop(**shop), query)
    return {
        "shop_id":   shop["id"],
        "shop_name": shop["short_name"],
        "brand":     "atb",
        "products":  [_product_dict(p) for p in products],
    }


@broker.task
async def search_varus_task(shop: dict, query: str) -> dict:
    client = VarusClient()
    products = await client.search_in_shop(VarusShop(**shop), query)
    return {
        "shop_id":   shop["id"],
        "shop_name": shop["short_name"],
        "brand":     "varus",
        "products":  [_product_dict(p) for p in products],
    }

@broker.task
async def search_fora_task(shop: dict, query: str) -> dict:
    client = ForaClient()
    products = await client.search_in_shop(ForaShop(**shop), query)
    return {
        "shop_id":   shop["id"],
        "shop_name": shop["short_name"],
        "brand":     "fora",
        "products":  [_product_dict(p) for p in products],
    }