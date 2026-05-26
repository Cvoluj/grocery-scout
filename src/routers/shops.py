from fastapi import APIRouter
from fastapi.responses import FileResponse

from src.settings import BASE_DIR
from src.store_data import atb_shops, varus_shops

router = APIRouter()


@router.get("/")
def index():
    return FileResponse(BASE_DIR / "src" / "static" / "store_map.html")

@router.get("/checkout")
def checkout():
    return FileResponse(BASE_DIR / "src" / "static" / "checkout.html")


@router.get("/api/shops")
def get_shops():
    atb = [{**s, "brand": "atb"} for s in atb_shops]
    varus = [{**s, "brand": "varus"} for s in varus_shops]
    return atb + varus
