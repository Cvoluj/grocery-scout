from dataclasses import dataclass



@dataclass
class Product:
    id: str
    store: str          # "atb" | "varus"
    name: str
    price: float
    in_stock: bool
    url: str
    image_url: str | None = None
    special_price: float | None = None

    @property
    def actual_price(self) -> float:
        return self.special_price or self.price

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


@dataclass
class ATBProduct:
    id: str
    name: str
    price: float
    in_stock: bool
    url: str
    image_url: str | None = None
    special_price: float | None = None