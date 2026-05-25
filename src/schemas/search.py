from pydantic import BaseModel

from src.schemas.shops import ShopRef


class SearchRequest(BaseModel):
    query: str
    shops: list[ShopRef]


class ProductResult(BaseModel):
    id: str
    name: str
    price: float
    special_price: float | None = None
    in_stock: bool
    url: str
    image_url: str | None = None


class ShopResult(BaseModel):
    shop_id: int
    shop_name: str
    brand: str
    products: list[ProductResult]


class MatchRequest(BaseModel):
    results: list[ShopResult]
    mode: str = "strict"
