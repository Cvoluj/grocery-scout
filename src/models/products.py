from dataclasses import dataclass


@dataclass
class ATBProduct:
    id: str
    name: str
    price: float
    in_stock: bool
    url: str
    image_url: str | None = None
    special_price: float | None = None


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


def from_atb(p: ATBProduct) -> Product:
    return Product(
        id=p.id,
        store="atb",
        name=p.name,
        price=p.price,
        in_stock=p.in_stock,
        url=p.url,
        image_url=p.image_url,
        special_price=p.special_price,
    )


def from_varus(p: VarusProduct) -> Product:
    return Product(
        id=p.id,
        store="varus",
        name=p.name,
        price=p.price,
        in_stock=p.in_stock,
        url=p.url,
        image_url=p.image_url,
        special_price=p.special_price,
    )
