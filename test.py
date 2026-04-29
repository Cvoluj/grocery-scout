import json
from dataclasses import dataclass
from curl_cffi import requests

from src.models.products import VarusProduct
from src.models.shops import VarusShop
from src.varus_api.headers import REGULAR_HEADERS, MULTISEARCH_HEADERS




VARUS_MULTISEARCH_ID = "12138"
VARUS_API_KEY = "468671b168b5ec56b8c34d458bf03f1b"

def fetch_kyiv_shops() -> list[VarusShop]:
    params = {
        "_source_exclude": "phone,is_darkhub,fax,emails,work_time,format_id,format_group_id,region,name",
        "_source_include": "",
        "from": "0",
        "request": json.dumps({
            "_availableFilters": [],
            "_appliedFilters": [
                {"attribute": "delivery_methods", "value": {"in": None}, "scope": "default"},
                {"attribute": "city_id", "value": 8, "scope": "default"},
            ],
            "_appliedSort": [],
            "_searchText": "",
        }),
        "request_format": "search-query",
        "response_format": "compact",
        "size": "250",
        "sort": "",
    }

    response = requests.get(
        "https://varus.ua/api/catalog/vue_storefront_catalog_2/tms_shop/_search",
        params=params,
        headers=REGULAR_HEADERS,
    )
    data = response.json()

    return [
        VarusShop(
            id=store["id"],
            tms_id=store["tms_id"],
            short_name=store["short_name"],
            address=store["address"],
            lat=float(store["lat"]),
            lon=float(store["long"]),
        )
        for store in data["hits"]
        if store.get("is_enabled") == "1" and store.get("is_darkstore") == "0"
    ]


def search_product_ids(shop: VarusShop, query: str) -> list[str]:
    params = {
        "id": VARUS_MULTISEARCH_ID,
        "key": VARUS_API_KEY,
        "query": query,
        "location": shop.tms_id,
        "lang": "uk",
        "limit": "40",
        "categories": "0",
        "fields": "id",
        "sort": "relevance",
        "filters": "{}",
    }

    response = requests.get(
        "https://api.multisearch.io/",
        params=params,
        headers=MULTISEARCH_HEADERS,
    )
    data = response.json()
    return [str(item["id"]) for item in data["results"]["items"]]


def fetch_products(shop: VarusShop, product_ids: list[str]) -> list[VarusProduct]:
    sqpp_field = f"sqpp_data_{shop.id}"

    params = {
        "_source_include": ",".join([
            "id", "name", "sku", "image", "url_key",
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

    response = requests.get(
        "https://varus.ua/api/catalog/vue_storefront_catalog_2/product_v2/_search",
        params=params,
        headers=REGULAR_HEADERS,
    )
    data = response.json()
    print(data)

    products = []
    for item in data["hits"]:
        sqpp = item.get(sqpp_field, {})
        products.append(VarusProduct(
            id=str(item["id"]),
            name=item["name"],
            sku=item["sku"],
            price=item.get("regular_price", 0.0),
            special_price_discount=item.get("special_price_discount"),
            in_stock=sqpp.get("in_stock", False),
            image=item.get("image", ""),
            url_key=item.get("url_key", ""),
        ))
    return products


def search_in_shop(shop: VarusShop, query: str) -> list[VarusProduct]:
    product_ids = search_product_ids(shop, query)
    if not product_ids:
        return []
    return fetch_products(shop, product_ids)


if __name__ == "__main__":
    shops = fetch_kyiv_shops()
    print(f"Знайдено магазинів: {len(shops)}")

    shop = shops[1]
    print(f"Шукаємо в: {shop.short_name} ({shop.address})")

    products = search_in_shop(shop, "молоко яготинське 2.6% 900г ультрапастеризоване")
    for p in products:
        print(f"{p.name} — {p.price} грн (в наявності: {p.in_stock})")