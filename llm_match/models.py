from pydantic import BaseModel
from llm_match import MatchMode


class ProductIn(BaseModel):
    id: str
    name: str
    price: float
    special_price: float | None = None
    in_stock: bool = True
    url: str | None = None
    image_url: str | None = None


class ShopIn(BaseModel):
    shop_id: int
    shop_name: str
    brand: str
    products: list[ProductIn]


class MatchRequest(BaseModel):
    shops: list[ShopIn]
    mode: MatchMode = MatchMode.STRICT
