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
            lines.append(f"\n[{store}]")
            for i, p in enumerate(store_products):
                key = f"{store}:{shop_id}:{i}"
                index_map[key] = p
                lines.append(f"  {key}: {p.name}")

        prompt = f"""You are a product matching engine. Group IDENTICAL products from different stores.

Two products are identical ONLY when ALL of the following match exactly:
1. Brand / manufacturer
2. Flavor, filling, or variety (soy sauce ≠ gouda cheese ≠ bacon — these are DIFFERENT products)
3. Volume or weight (1 L ≠ 1.25 L ≠ 1.5 L; 30 g ≠ 50 g — even "close" sizes are different products)
4. Fat content, if stated (2.5% ≠ 3.2%)
5. Product type (snack ≠ drink, even same brand)

Allowed formatting variants (same product): 0.9 kg = 900 g | 2,6% = 2.6% | "пл" = "пляшка" | minor name reordering.

NEVER group these — they are distinct products, each gets its own group:
  ✗ Same brand, different flavor: "РябChick сушені соєвий соус 30г" vs "РябChick сушені сир гауда 30г"
  ✗ Same brand, different volume: "Кока-кола 1 л" vs "Кока-кола 1.25 л"
  ✗ Same brand, different fat%: "молоко 2.5%" vs "молоко 3.2%"

When in doubt → separate groups. More groups is always safer than wrong merges.
Every product must appear in exactly one group. If a product has no match — it gets its own single-item group.

Products:
{chr(10).join(lines)}

Return ONLY valid JSON, no markdown, no comments:
{{
  "groups": [
    {{
      "canonical": "Молоко Яготинське 2.6% 900г",
      "matches": ["atb:0:2", "varus:0:5"]
    }},
    {{
      "canonical": "РябChick слайси соєвий соус 30г",
      "matches": ["atb:0:7"]
    }},
    {{
      "canonical": "РябChick слайси сир гауда 30г",
      "matches": ["varus:0:3"]
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
            temperature=0.0,
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