from dataclasses import dataclass


@dataclass
class VarusProduct:
    id: str
    name: str
    sku: str
    price: float
    in_stock: bool
    url: str
    image_url: str | None = None
    special_price: float | None = None
    special_price_discount: int | None = None
    special_price_to_date: str | None = None
