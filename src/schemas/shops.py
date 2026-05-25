from pydantic import BaseModel


class ShopRef(BaseModel):
    id: int
    brand: str
