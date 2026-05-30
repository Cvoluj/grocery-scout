from dataclasses import dataclass
from curl_cffi import AsyncSession, Response

from src.models.products import ForaProduct
from src.brands.fora.headers import REGULAR_HEADERS, SEARCH_HEADERS
from src.models.shops import ForaShop


class ForaClient:
    API_URL = "https://api.catalog.ecom.fora.ua/api/2.0/exec/EcomCatalogGlobal"


    def __init__(self):
        self.session = AsyncSession()
        self.stores: list[ForaShop] = []

    async def _fetch_stores(self) -> list[ForaShop]:
        response: Response = await self.session.post(
            self.API_URL,
            headers=REGULAR_HEADERS,
            json={
                "method": "GetPickupFilials",
                "data": {
                    "merchantId": 2,
                    "businessId": 4,
                    "city": "м. Київ",
                    "lat": "",
                    "lon": "",
                    "distance": "",
                },
            },
        )
        return [
            ForaShop(
                id=item["id"],
                short_name=f"Фора — {item['address']}",
                address=item["title"],
                lat=item["lat"],
                lon=item["lon"],
            )
            for item in response.json()["items"]
        ]

    async def get_stores(self) -> list[ForaShop]:
        if not self.stores:
            self.stores = await self._fetch_stores()
        return self.stores
    
    async def search_in_shop(self, shop: ForaShop, query: str) -> list[ForaProduct]:
        response: Response = await self.session.post(
            self.API_URL,
            headers=SEARCH_HEADERS,
            json={
                "method": "GetSimpleCatalogItems",
                "data": {
                    "merchantId": 2,
                    "customFilter": query,
                    "deliveryType": 1,
                    "filialId": shop.id,
                    "From": 1,
                    "To": 40,
                },
            },
        )
        data = response.json()
        products = []
        for item in data.get("items", []):
            old_price = item.get("oldPrice")
            products.append(ForaProduct(
                id=str(item["id"]),
                name=f"{item['name']} {item['unit']}" if item.get("unit") else item["name"],
                price=old_price if old_price else item["price"],
                special_price=item["price"] if old_price else None,
                in_stock=item.get("quantity", 0) > 0,
                url=f"https://fora.ua/product/{item['slug']}",
                image_url=item.get("mainImage"),
            ))
        return products
    

if __name__ == '__main__':
    import asyncio

    async def main():
        client = ForaClient()
        shops = await client.get_stores()
        print(f"Знайдено магазинів: {len(shops)}")

        shop = shops[0]
        print(shop)
        print(f"Шукаємо в: {shop.short_name} ({shop.address})")

        query = "десерт сирковий"
        products = await client.search_in_shop(shop, query)
        print(f"\nРезультати для '{query}' ({len(products)} товарів):")
        for product in products:
            print(product)

    asyncio.run(main())
