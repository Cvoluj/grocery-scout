from dataclasses import asdict
import json
import re
import time
import uuid
import random

from curl_cffi import AsyncSession, Response

from src.brands.atb.headers import GETSTORE_HEADERS, MULTISEARCH_HEADERS
from src.models.products import ATBProduct
from src.models.shops import ATBShop
from src.settings import BROWSER_TYPES_CYCLE

_OPTION_RE = re.compile(
    r"<option value='(\d+)' worktime='([^']+)' city='\d+'>([^<]+)</option>"
)

def _strip_prefix(address: str) -> str:
    first, _, rest = address.partition(' ')
    return rest.strip() if first.endswith('.') else address

def _parse_shops(data: dict) -> list[ATBShop]:
    coord_map = {
        item["id"]: (float(item["lat"]), float(item["lng"]))
        for item in data["coordinates"]
    }
    shops = []
    for m in _OPTION_RE.finditer(data["optselect"]):
        shop_id = int(m.group(1))
        worktime = m.group(2)
        address = m.group(3)
        lat, lon = coord_map[shop_id]
        shops.append(ATBShop(
            id=shop_id,
            short_name=f"АТБ — {_strip_prefix(address)}",
            lat=lat,
            lon=lon,
            address=address,
            worktime=worktime,
        ))
    return shops


def _parse_product(item: dict) -> ATBProduct:
    old_price = item.get("oldprice")
    return ATBProduct(
        id=item["id"],
        name=item["name"],
        price=old_price if old_price else item["price"],
        in_stock=item["is_presence"],
        url=item["url"],
        image_url=item.get("picture"),
        special_price=item["price"] if old_price else None,
    )


def _parse_products(data: dict) -> list[ATBProduct]:
    products = []
    for group in data["results"]["item_groups"]:
        for item in group["items"]:
            items = item if isinstance(item, list) else [item]
            for subitem in items:
                products.append(_parse_product(subitem))
    return products


def _gen_q() -> str:
    return random.randint(0, 36**6).to_bytes(4, "big").hex()[:6]

class AtbClient:
    ATB_MULTISEARCH_ID = "11280"
    ATB_API_KEY = "63a6d0a760fd2d0562c4061b78e64754"
    ATB_CITY_ID = "395"


    def __init__(self):
        self.session = AsyncSession(impersonate=next(BROWSER_TYPES_CYCLE))
        self.search_session = AsyncSession()
        self.stores: list[ATBShop] = []
        self.uid = str(uuid.uuid4())

    async def _fetch_stores(self) -> list[ATBShop]:
        response: Response = await self.session.post(
            "https://www.atbmarket.com/site/getstore",
            headers=GETSTORE_HEADERS,
            cookies={"lang": "uk"},
            data={"city": self.ATB_CITY_ID},
        )
        return _parse_shops(response.json())

    async def get_stores(self):
        if not self.stores:
            self.stores = await self._fetch_stores()
        return self.stores

    async def search_in_shop(self, shop: ATBShop, query: str) -> list[ATBProduct]:
        params = {
            "id": self.ATB_MULTISEARCH_ID,
            "key": self.ATB_API_KEY,
            "lang": "uk",
            "location": str(shop.id),
            "m": str(int(time.time() * 1000)),
            "q": _gen_q(),
            "query": query,
            "s": "small",
            "uid": self.uid,
        }
        response: Response = await self.search_session.get(
            "https://api.multisearch.io/",
            params=params,
            headers=MULTISEARCH_HEADERS,
        )
        data = response.json()
        if not data.get("results", {}).get("item_groups"):
            return []
        return _parse_products(data)


if __name__ == "__main__":
    import asyncio

    async def main():
        client = AtbClient()
        shops = await client.get_stores()
        print(f"Знайдено магазинів: {len(shops)}")

        shop = shops[0]
        print(f"Шукаємо в: {shop}")

        query = "Молоко Яготинське"
        products = await client.search_in_shop(shop, query)
        print(f"\nРезультати для '{query}' ({len(products)} товарів):")
        for product in products:
            print(product)

    asyncio.run(main())