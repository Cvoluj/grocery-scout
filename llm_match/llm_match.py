import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from litellm import acompletion


class MatchMode(str, Enum):
    STRICT = "strict"
    ANALOGS = "analogs"


@dataclass
class Product:
    id: str
    name: str
    price: float
    store: str
    shop_id: int
    in_stock: bool = True
    url: str | None = None
    image_url: str | None = None
    special_price: float | None = None


@dataclass
class MatchedProduct:
    canonical_name: str
    offers: list[dict]


class LLMMatcher:
    def __init__(
        self,
        model: str = "groq/llama-3.3-70b-versatile",
        api_key: str | None = None,
        prompts_dir: Path | None = None,
    ):
        self.model = model
        self.api_key = api_key
        base = prompts_dir or Path(__file__).parent / "prompts"
        self._prompts = {
            mode: (base / f"{mode.value}.txt").read_text(encoding="utf-8").strip()
            for mode in MatchMode
        }

    def prepare(
        self,
        shops: list[dict],
    ) -> tuple[dict[tuple[str, int], list[Product]], dict[tuple[str, str], list[dict]]]:
        brand_products: dict[str, dict[str, Product]] = {}
        shop_lookup: dict[tuple[str, str], list[dict]] = {}

        for shop in shops:
            brand = shop["brand"]
            brand_products.setdefault(brand, {})

            for p in shop["products"]:
                actual = p.get("special_price") or p["price"]
                key = (brand, p["id"])

                shop_lookup.setdefault(key, []).append({
                    "shop_id": shop["shop_id"],
                    "shop_name": shop["shop_name"],
                    "price": p["price"],
                    "special_price": p.get("special_price"),
                    "actual_price": actual,
                })

                if p["id"] not in brand_products[brand]:
                    brand_products[brand][p["id"]] = Product(
                        id=p["id"],
                        name=p["name"],
                        price=p["price"],
                        special_price=p.get("special_price"),
                        in_stock=p.get("in_stock", True),
                        url=p.get("url"),
                        image_url=p.get("image_url"),
                        store=brand,
                        shop_id=shop["shop_id"],
                    )

        matcher_input = {
            (brand, 0): list(products.values())
            for brand, products in brand_products.items()
        }
        return matcher_input, shop_lookup

    def _build_product_list(
        self,
        products: dict[tuple[str, int], list[Product]],
    ) -> tuple[str, dict[str, Product]]:
        index_map: dict[str, Product] = {}
        lines = []

        for (store, shop_id), store_products in products.items():
            lines.append(f"[{store} shop={shop_id}]")
            for i, p in enumerate(store_products):
                key = f"{store}:{shop_id}:{i}"
                index_map[key] = p
                lines.append(f"  {key}: {p.name}")

        return "\n".join(lines), index_map

    async def match(
        self,
        products: dict[tuple[str, int], list[Product]],
        mode: MatchMode = MatchMode.STRICT,
    ) -> list[MatchedProduct]:
        product_list, index_map = self._build_product_list(products)

        response = await acompletion(
            model=self.model,
            max_tokens=4096,
            temperature=0.0,
            api_key=self.api_key,
            messages=[
                {"role": "system", "content": self._prompts[mode]},
                {"role": "user", "content": f"Products to group:\n\n{product_list}"},
            ],
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)

        results = []
        for group in parsed["groups"]:
            offers_map: dict[tuple[str, int], Product] = {}
            for key in group["matches"]:
                store, shop_id, _ = key.split(":")
                p = index_map[key]
                offers_map[(store, int(shop_id))] = p
            results.append(MatchedProduct(
                canonical_name=group["canonical"],
                offers=offers_map,
            ))

        return results

    async def match_raw(
        self,
        shops: list[dict],
        mode: MatchMode = MatchMode.STRICT,
    ) -> list[dict]:
        matcher_input, shop_lookup = self.prepare(shops)
        matched = await self.match(matcher_input, mode=mode)

        output = []
        for matched_product in matched:
            offers = {}
            for (store, _), product in matched_product.offers.items():
                for shop in sorted(
                    shop_lookup.get((store, product.id), []),
                    key=lambda s: s["actual_price"],
                ):
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
            output.append({"canonical": matched_product.canonical_name, "offers": offers})

        return output
