import json

from src.config import SHARED_DATA

_raw_atb: list[dict] = json.loads((SHARED_DATA / "atb_shops.json").read_text(encoding="utf-8"))
_raw_varus: list[dict] = json.loads((SHARED_DATA / "varus_shops.json").read_text(encoding="utf-8"))

atb_shops: list[dict] = _raw_atb
varus_shops: list[dict] = _raw_varus
atb_by_id: dict[int, dict] = {s["id"]: s for s in _raw_atb}
varus_by_id: dict[int, dict] = {s["id"]: s for s in _raw_varus}
