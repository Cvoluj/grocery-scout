"""
Shop registry - single source of truth for all shop configurations.

Adding a new shop chain:
  2. Add {BRANDNAME}_META = {"label": "...", "bg": "...", "color": "..."} in PocketBase settings collection
  3. Add src/<brand>_api/client.py  implementing search_in_shop()
  4. Add search_{brand}_task  in src/tasks.py

File naming: {brand}_shops.json  →  brand is derived from filename automatically.
"""
import json
import importlib
from dataclasses import asdict
import logging
from pathlib import Path
from typing import Callable

from libs.pb_client import RuntimeSettings, runtime
from src.settings import SHARED_DATA

logger = logging.getLogger(__name__)

class BrandConfig:
    def __init__(self, brand: str, shops: list[dict], runtime: RuntimeSettings):
        self.brand: str = brand
        self._runtime = runtime
        self.shops: list[dict] = shops
        self.by_id: dict[int, dict] = {s["id"]: s for s in shops}

    def _meta(self) -> dict:
        meta_raw = self._runtime.get(f"{self.brand.upper()}_META", "{}")
        return json.loads(meta_raw) if meta_raw else {}

    @property
    def label(self) -> str:
        return self._meta().get("label", self.brand)

    @property
    def bg(self) -> str:
        return self._meta().get("bg", "#F3F4F6")

    @property
    def color(self) -> str:
        return self._meta().get("color", "#111827")

    @property
    def email_meta(self) -> dict:
        meta = self._meta()
        return {
            "label": meta.get("label", self.brand),
            "bg":    meta.get("bg", "#F3F4F6"),
            "color": meta.get("color", "#111827"),
        }

    def refresh_shops(self, shops: list[dict], path: Path) -> None:
        """Update in-memory lookups and overwrite the JSON file."""
        self.shops = shops
        self.by_id = {s["id"]: s for s in shops}
        path.write_text(
            json.dumps(shops, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("ShopRegistry: refreshed %s (%d shops)", self.brand, len(shops))


class ShopRegistry:
    """
    Auto-discovers all *_shops.json files in `shops_dir`.
    Merges with meta from PocketBase runtime ({BRAND}_META key).
    Consults runtime `enabled_brands` to decide which brands are active.

    Startup order (important):
        await start_pb()     # runtime must be populated first
        registry.load()

    Usage:
        registry.is_enabled("atb")
        registry.shops_for("varus")
        registry.resolve_shops(req.shops)   # filters to enabled only
        registry.get_task("atb")            # returns Taskiq task
        registry.refresh_shops("varus", new_shops)
    """

    def __init__(self, shops_dir: Path, runtime: "RuntimeSettings"):
        self._dir = shops_dir
        self._runtime = runtime
        self._configs: dict[str, BrandConfig] = {}
        # Track file paths for refresh writes
        self._paths: dict[str, Path] = {}

    def load(self) -> None:
        if not self._dir.exists():
            raise FileNotFoundError(f"shops_dir not found: {self._dir}")

        # Create missing shop files for known enabled brands
        enabled_raw = self._runtime.get("enabled_brands", "")
        if enabled_raw:
            for brand in {b.strip() for b in enabled_raw.split(",")}:
                path = self._dir / f"{brand}_shops.json"
                if not path.exists():
                    path.write_text("[]", encoding="utf-8")
                    logger.info("ShopRegistry: created empty %s", path.name)

        loaded: list[str] = []
        for path in sorted(self._dir.glob("*_shops.json")):
            brand = path.stem.replace("_shops", "")
            try:
                shops: list[dict] = json.loads(path.read_text(encoding="utf-8"))
                cfg = BrandConfig(brand, shops, self._runtime)
                self._configs[brand] = cfg
                self._paths[brand] = path
                loaded.append(brand)
            except Exception:
                logger.exception("ShopRegistry: failed to load %s", path)

        logger.info("ShopRegistry: loaded brands=%s", loaded)

    def is_enabled(self, brand: str) -> bool:
        """
        Enabled when brand is loaded AND either:
          - `enabled_brands` key is absent/empty in PocketBase (all on), or
          - brand appears in the comma-separated `enabled_brands` value.
        """
        if brand not in self._configs:
            return False
        enabled = self._runtime.get("enabled_brands", "")
        if not enabled:
            return True
        return brand in {b.strip() for b in enabled.split(",")}

    @property
    def enabled_brands(self) -> list[str]:
        return [b for b in self._configs if self.is_enabled(b)]

    def shops_for(self, brand: str) -> list[dict]:
        return self._get(brand).shops

    def by_id(self, brand: str, shop_id: int) -> dict | None:
        return self._get(brand).by_id.get(shop_id)

    def config(self, brand: str) -> BrandConfig:
        return self._get(brand)

    def all_configs(self) -> dict[str, BrandConfig]:
        return dict(self._configs)

    def refresh_shops(self, brand: str, shops: list[dict]) -> None:
        """
        Update in-memory lookups and persist to JSON.
        Clients call this instead of writing the file themselves:

            registry.refresh_shops("varus", [asdict(s) for s in stores])
        """
        cfg = self._get(brand)
        cfg.refresh_shops(shops, self._paths[brand])
    
    async def sync_all_shops(self) -> None:
        for brand in self.enabled_brands:
            try:
                module = importlib.import_module(f"src.brands.{brand}.client")
                client_class = getattr(module, f"{brand.capitalize()}Client")
                client = client_class()
                shops = await client.get_stores()
                self.refresh_shops(brand, [asdict(s) for s in shops])
            except Exception:
                logger.exception("Failed to sync shops for brand '%s'", brand)

    def email_brands(self) -> dict[str, dict]:
        """Drop-in for the old hardcoded BRANDS dict in email/sender.py."""
        return {brand: cfg.email_meta for brand, cfg in self._configs.items()}

    def resolve_shops(self, requested: list) -> dict[str, list[dict]]:
        """
        Given a list of ShopRef(brand, id) from a search request,
        returns { brand: [shop_dict, ...] } filtered to enabled brands only.
        Items can be dicts or objects with .brand / .id attributes.
        """
        grouped: dict[str, list[dict]] = {}
        for ref in requested:
            brand   = ref["brand"] if isinstance(ref, dict) else ref.brand
            shop_id = ref["id"]    if isinstance(ref, dict) else ref.id

            if not self.is_enabled(brand):
                continue
            shop = self.by_id(brand, shop_id)
            if shop:
                grouped.setdefault(brand, []).append(shop)
        return grouped

    def get_task(self, brand: str) -> Callable:
        """
        Returns the Taskiq task for `brand` by convention:
            search_{brand}_task  must exist in src/tasks.py
        """
        from src import tasks  # late import - avoids circular deps
        task_name = f"search_{brand}_task"
        task = getattr(tasks, task_name, None)
        if task is None:
            raise KeyError(
                f"No task '{task_name}' in src.tasks. "
                f"Add it to support brand '{brand}'."
            )
        return task

    def _get(self, brand: str) -> BrandConfig:
        if brand not in self._configs:
            raise KeyError(
                f"Unknown brand '{brand}'. "
                f"Known: {list(self._configs)}. "
                f"Add shared_data/shops/{brand}_shops.json to register it."
            )
        return self._configs[brand]
registry = ShopRegistry(SHARED_DATA, runtime)
    

if __name__ == '__main__':
    import asyncio
    from libs.pb_client import start_pb

    async def main():
        await start_pb()
        registry.load()

        for brand in registry.enabled_brands:
            cfg = registry.config(brand)
            print(f"{brand}: {cfg.label} - {len(cfg.shops)} shops")
            print(f"  meta: bg={cfg.bg} color={cfg.color}")
            print(f"  first shop: {cfg.shops[0] if cfg.shops else 'none'}")

    asyncio.run(main()) 
