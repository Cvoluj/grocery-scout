import json
from dataclasses import dataclass

from litellm import acompletion

from src.models.products import Product
from src.settings import ANTHROPIC_API_KEY, GEMINI_API_KEY, GROQ_API_KEY


@dataclass
class MatchedProduct:
    canonical_name: str
    offers: dict[tuple[str, int], Product]


class LLMMatcher:
    def __init__(self, model="groq/llama-3.3-70b-versatile"):
        self.model = model

    def _build_prompt(
        self,
        products: dict[tuple[str, int], list[Product]],
    ) -> tuple[str, dict[str, Product]]:
        index_map: dict[str, Product] = {}
        lines = []

        for (store, shop_id), store_products in products.items():
            lines.append(f"\n[{store} | shop_id={shop_id}]")
            for i, p in enumerate(store_products):
                key = f"{store}:{shop_id}:{i}"
                index_map[key] = p
                lines.append(f"  {key}: {p.name}")

        prompt = f"""Згрупуй однакові продукти з різних магазинів.

        Продукти вважаються однаковими якщо збігаються: бренд, об'єм/вага, жирність, смак, тип упаковки.
        Допускається різне форматування (0,9 кг = 900 г, 2,6% = 2.6%, п/бут = пляшка).
        Кожен продукт має потрапити рівно в одну групу, навіть якщо пари немає.

        Продукти:
        {chr(10).join(lines)}

        Поверни ТІЛЬКИ валідний JSON без markdown та коментарів:
        {{
        "groups": [
            {{
            "canonical": "Молоко Яготинське ультрапастеризоване 2.6% 900г",
            "matches": ["atb:1262:0", "varus:42:2"]
            }}
        ]
        }}"""

        return prompt, index_map

    async def match(
        self,
        products: dict[tuple[str, int], list[Product]],
    ) -> list[MatchedProduct]:
        prompt, index_map = self._build_prompt(products)

        response = await acompletion(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            api_key=GROQ_API_KEY,
        )

        raw = response.choices[0].message.content.strip()
        print("LLM raw response:", raw)
        parsed = json.loads(raw)

        results = []
        for group in parsed["groups"]:
            offers: dict[tuple[str, int], Product] = {}
            for key in group["matches"]:
                store, shop_id, _ = key.split(":")
                p = index_map[key]
                offers[(store, int(shop_id))] = p
            results.append(MatchedProduct(
                canonical_name=group["canonical"],
                offers=offers,
            ))

        return results