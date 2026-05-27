import asyncpg

from libs.pb_client import runtime

_pool: asyncpg.Pool | None = None

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    email           TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
"""


async def setup_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(runtime.get("DATABASE_URL"))
    print(f"DATABASE_URL: {runtime.get("DATABASE_URL")}", flush=True)
    async with _pool.acquire() as conn:
        await conn.execute(_CREATE_TABLES)


async def teardown_pool() -> None:
    if _pool:
        await _pool.close()


async def get_conn():
    async with _pool.acquire() as conn:
        yield conn
