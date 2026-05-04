from dataclasses import dataclass

from src.models.products import ATBProduct, VarusProduct


@dataclass
class Product:
    id: str
    store: str          # "atb" | "varus"
    name: str
    price: float        # оригінальна ціна
    in_stock: bool
    url: str
    image_url: str | None = None
    special_price: float | None = None  # ціна зі знижкою

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