import asyncpg
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from src.auth.deps import get_current_user, require_page_auth
from src.brands import registry
from src.settings import BASE_DIR

router = APIRouter()


@router.get("/login")
def login_page():
    return FileResponse(BASE_DIR / "src" / "static" / "login.html")


@router.get("/")
def index(_: None = Depends(require_page_auth)):
    return FileResponse(BASE_DIR / "src" / "static" / "store_map.html")


@router.get("/checkout")
def checkout(_: None = Depends(require_page_auth)):
    return FileResponse(BASE_DIR / "src" / "static" / "checkout.html")


@router.get("/api/shops")
def get_shops(_: asyncpg.Record = Depends(get_current_user)):
    return [
        {**shop, "brand": brand}
        for brand in registry.enabled_brands
        for shop in registry.shops_for(brand)
    ]
