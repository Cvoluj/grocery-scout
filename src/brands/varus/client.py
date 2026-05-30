

from dataclasses import asdict
import json

from curl_cffi import AsyncSession, Response

from src.config import VARUS_SHOPS_CACHE
from src.models.products import VarusProduct
from src.models.shops import VarusShop
from src.brands.varus.headers import MULTISEARCH_HEADERS, REGULAR_HEADERS


class VarusClient:
    VARUS_MULTISEARCH_ID = "12138"
    VARUS_API_KEY = "468671b168b5ec56b8c34d458bf03f1b"

    def __init__(self):
        self.session = AsyncSession()
        self.stores: list[VarusShop] = []

    async def _fetch_stores(self):
        params = {
            '_source_exclude': 'phone,is_darkhub,fax,emails,work_time,format_id,format_group_id,region,name',
            '_source_include': '',
            'from': '0',
            'request': '{"_availableFilters":[],"_appliedFilters":[{"attribute":"delivery_methods","value":{"in":null},"scope":"default"},{"attribute":"city_id","value":8,"scope":"default"}],"_appliedSort":[],"_searchText":""}',
            'request_format': 'search-query',
            'response_format': 'compact',
            'size': '250',
            'sort': '',
        }
        response: Response = await self.session.get(
            'https://varus.ua/api/catalog/vue_storefront_catalog_2/tms_shop/_search',
            params=params,
            headers=REGULAR_HEADERS,
        )
        return [
            VarusShop(
                id=store["id"],
                tms_id=store["tms_id"],
                short_name=f"Варус — {store['short_name']}",
                address=store["address"],
                lat=float(store["lat"]),
                lon=float(store["long"]),
            )
            for store in response.json()["hits"]
            if store.get("is_enabled") == "1" and store.get("is_darkstore") == "0"
        ]

    async def get_stores(self):
        if not self.stores:
            self.stores = await self._fetch_stores()
        return self.stores
    
    async def search_product_ids(self, shop: VarusShop, query: str) -> list[str]:
        params = {
            "id": self.VARUS_MULTISEARCH_ID,
            "key": self.VARUS_API_KEY,
            "query": query,
            "location": shop.tms_id,
            "lang": "uk",
            "limit": "40",
            "categories": "0",
            "fields": "id",
            "sort": "relevance",
            "filters": "{}",
        }
        response: Response = await self.session.get(
            "https://api.multisearch.io/",
            params=params,
            headers=MULTISEARCH_HEADERS,
        )
        data = response.json()
        return [str(item["id"]) for item in data["results"]["items"]]
    
    async def fetch_products(self, shop: VarusShop, product_ids: list[str]) -> list[VarusProduct]:
        sqpp_field = f"sqpp_data_{shop.id}"

        params = {
            "_source_include": ",".join([
                "id", "name", "sku", "fv_image_timestamp", "url_key",
                "regular_price", "special_price_discount",
                sqpp_field,
            ]),
            "from": "0",
            "request": json.dumps({
                "_availableFilters": [],
                "_appliedFilters": [
                    {"attribute": "id", "value": {"in": product_ids}, "scope": "default"},
                    {"attribute": f"{sqpp_field}.in_stock", "value": {"eq": True}, "scope": "default"},
                ],
                "_appliedSort": [],
                "_searchText": "",
            }),
            "request_format": "search-query",
            "response_format": "compact",
            "shop_id": str(shop.id),
            "size": str(len(product_ids)),
            "sort": "",
        }

        response: Response = await self.session.get(
            "https://varus.ua/api/catalog/vue_storefront_catalog_2/product_v2/_search",
            params=params,
            headers=REGULAR_HEADERS,
        )
        data = response.json()

        products = []
        for item in data["hits"]:
            sqpp = item.get(sqpp_field, {})
            fv_image_timestamp = item.get("fv_image_timestamp")
            products.append(VarusProduct(
                id=str(item["id"]),
                name=item["name"],
                sku=item["sku"],
                price=sqpp.get("price", 0.0),
                special_price=sqpp.get("special_price") or None,
                special_price_discount=sqpp.get("special_price_discount") or None,
                special_price_to_date=sqpp.get("special_price_to_date"),
                in_stock=sqpp.get("in_stock", False),
                url=f"https://varus.ua/{item['url_key']}",
                image_url=f"https://varus.ua/img/product/420/420/{item['sku']}?t={fv_image_timestamp}" if fv_image_timestamp else None,
            ))
        return products
    
    
    async def search_in_shop(self, shop: VarusShop, query: str) -> list[VarusProduct]:
        product_ids = await self.search_product_ids(shop, query)
        if not product_ids:
            return []
        return await self.fetch_products(shop, product_ids)
    
if __name__ == '__main__':
    import asyncio

    async def main():
        client = VarusClient()
        shops = await client.get_stores()
        print(f"Знайдено магазинів: {len(shops)}")

        shop = shops[0]
        print(shop)
        print(f"Шукаємо в: {shop.short_name} ({shop.address})")

        query = "Молоко Яготинське"
        products = await client.search_in_shop(shop, query)
        print(f"\nРезультати для '{query}' ({len(products)} товарів):")
        for product in products:
            print(product)

    asyncio.run(main())
