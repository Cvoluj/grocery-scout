from pydantic import BaseModel


class OfferData(BaseModel):
    name: str
    actual_price: float
    price: float
    special_price: float | None = None
    image_url: str | None = None
    url: str | None = None


class ReceiptLine(BaseModel):
    canonical: str
    offer: OfferData | None = None


class ReceiptData(BaseModel):
    shop_key: str
    shop_name: str
    brand: str
    total: float
    available_count: int
    total_count: int
    lines: list[ReceiptLine]


class SendReceiptRequest(BaseModel):
    receipts: list[ReceiptData]
    shop_ids: list[dict]  # [{"brand": "atb", "id": 964}, ...]
