from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from src.store_data import atb_shops, varus_shops

router = APIRouter()

_STATIC = Path(__file__).parent.parent / "static"


@router.get("/")
def index():
    return FileResponse(_STATIC / "store_map.html")


@router.get("/checkout")
def checkout():
    return FileResponse(_STATIC / "checkout.html")


@router.get("/api/shops")
def get_shops():
    atb = [{**s, "brand": "atb"} for s in atb_shops]
    varus = [{**s, "brand": "varus"} for s in varus_shops]
    return atb + varus
