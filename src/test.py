import asyncio
import os

from src.brands.atb.client import AtbClient
from src.brands.varus.client import VarusClient
from src.models.adapter_product import Product, from_atb, from_varus
from src.llm_match import LLMMatcher, MatchedProduct

# --- заморожені магазини ---
ATB_SHOP_ID = 812
VARUS_SHOP_ID = 44


async def search_all(
    query: str,
    atb_client: AtbClient,
    varus_client: VarusClient,
    atb_shop,
    varus_shop,
) -> dict[tuple[str, int], list[Product]]:
    atb_raw, varus_raw = await asyncio.gather(
        atb_client.search_in_shop(atb_shop, query),
        varus_client.search_in_shop(varus_shop, query),
    )
    return {
        ("atb", atb_shop.id): [from_atb(p) for p in atb_raw],
        ("varus", varus_shop.id): [from_varus(p) for p in varus_raw],
    }


def display_matches(matches: list[MatchedProduct]):
    for i, m in enumerate(matches):
        print(f"\n[{i}] {m.canonical_name}")
        for (store, shop_id), p in m.offers.items():
            actual = p.special_price or p.price
            discount = f" (зі знижки {p.price} грн)" if p.special_price else ""
            image = f"\n      🖼  {p.image_url}" if p.image_url else ""
            print(f"     {store.upper():6} {actual:.2f} грн{discount}")
            print(f"      🔗 {p.url}{image}")


def display_cart(cart: list[tuple[MatchedProduct, int]]):
    print("\n" + "="*50)
    print("🛒 КОШИК:")
    totals: dict[tuple[str, int], float] = {}

    for m, qty in cart:
        print(f"\n  {m.canonical_name} x{qty}")
        for (store, shop_id), p in m.offers.items():
            actual = p.special_price or p.price
            line = actual * qty
            totals[(store, shop_id)] = totals.get((store, shop_id), 0) + line
            print(f"    {store.upper():6} {actual:.2f} x {qty} = {line:.2f} грн")

    print("\n📊 Підсумок по магазинах:")
    for (store, shop_id), total in sorted(totals.items(), key=lambda x: x[1]):
        print(f"  {store.upper():6} shop={shop_id}: {total:.2f} грн")

    if totals:
        best = min(totals, key=totals.get)
        print(f"\n✅ Найвигідніше: {best[0].upper()} shop={best[1]} — {totals[best]:.2f} грн")
    print("="*50)


async def main():
    atb_client = AtbClient()
    varus_client = VarusClient()
    matcher = LLMMatcher()

    print("Завантаження магазинів...")
    atb_shops = await atb_client.get_stores()
    varus_shops = await varus_client.get_stores()

    atb_shop = next(s for s in atb_shops if s.id == ATB_SHOP_ID)
    varus_shop = next(s for s in varus_shops if s.id == VARUS_SHOP_ID)

    print(f"ATB:   {atb_shop.short_name}")
    print(f"Varus: {varus_shop.short_name}")

    cart: list[tuple[MatchedProduct, int]] = []

    while True:
        print("\n" + "-"*50)
        cmd = input("🔍 Запит (або 'кошик' / 'вихід'): ").strip()

        if cmd == "вихід":
            break
        if cmd == "кошик":
            display_cart(cart)
            continue
        if not cmd:
            continue

        query = cmd
        while True:
            print(f"\nШукаємо '{query}'...")
            products = await search_all(query, atb_client, varus_client, atb_shop, varus_shop)

            total = sum(len(v) for v in products.values())
            if not total:
                print("Нічого не знайдено.")
                break

            print("Матчинг через LLM...")
            matches = await matcher.match(products)
            display_matches(matches)

            print("\n[q] нова кверя  [число] вибрати продукт  [Enter] пропустити")
            choice = input("→ ").strip()

            if choice == "q":
                query = input("Новий запит: ").strip()
                continue
            if choice == "":
                break
            if choice.isdigit() and int(choice) < len(matches):
                selected = matches[int(choice)]
                qty_raw = input(f"Кількість [{selected.canonical_name}]: ").strip()
                qty = int(qty_raw) if qty_raw.isdigit() else 1
                cart.append((selected, qty))
                print(f"✅ Додано: {selected.canonical_name} x{qty}")

                more = input("Додати ще продукт? [y/n]: ").strip()
                if more != "y":
                    break
            else:
                print("Невірний вибір.")

    display_cart(cart)


if __name__ == "__main__":
    asyncio.run(main())