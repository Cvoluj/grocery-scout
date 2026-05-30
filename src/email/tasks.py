from src.broker import broker
from src.brands import registry
from src.email.schemas import ReceiptData
from src.email.service import EnrichedReceipt, send_receipt_email


def _enrich(receipts: list[ReceiptData], shop_ids: list[dict]) -> list[EnrichedReceipt]:
    coords: dict[str, tuple[float | None, float | None]] = {}
    for s in shop_ids:
        brand, sid = s["brand"], s["id"]
        shop = registry.by_id(brand, sid)
        key = f"{brand}_{sid}"
        coords[key] = (shop["lat"], shop["lon"]) if shop else (None, None)

    sorted_receipts = sorted(
        receipts,
        key=lambda r: (-(r.available_count == r.total_count), r.total),
    )
    best_total = next(
        (r.total for r in sorted_receipts if r.available_count == r.total_count),
        None,
    )

    result = []
    for r in sorted_receipts:
        lat, lon = coords.get(r.shop_key, (None, None))
        is_best = best_total is not None and r.total == best_total and r.available_count == r.total_count
        result.append(EnrichedReceipt(data=r, lat=lat, lon=lon, is_best=is_best))
    return result


@broker.task
async def send_receipt_task(to: str, receipts: list[dict], shop_ids: list[dict]) -> None:
    parsed = [ReceiptData(**r) for r in receipts]
    enriched = _enrich(parsed, shop_ids)
    await send_receipt_email(to, enriched)
