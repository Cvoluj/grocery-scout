"""
HTTP Client Benchmark: requests vs httpx vs curl_cffi
Залежності: pip install requests httpx curl_cffi fastapi uvicorn matplotlib numpy
"""

import asyncio
import time
import threading
import json
import string
import random
import statistics
from concurrent.futures import ThreadPoolExecutor

import uvicorn
import requests as req_lib
import httpx
from curl_cffi.requests import AsyncSession
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import matplotlib.pyplot as plt
import numpy as np

HOST = "127.0.0.1"
PORT = 8765
URL = f"http://{HOST}:{PORT}/data"

CONCURRENCY_LEVELS = [50, 75, 100, 200, 400]
WARMUP_REQUESTS = 5
RUNS_PER_LEVEL = 3

# ---------------------------------------------------------------------------
# Тестовий сервер — повертає ~200KB JSON
# ---------------------------------------------------------------------------

def generate_payload(size_kb: int = 200) -> dict:
    chars = string.ascii_letters + string.digits + " "
    items = []
    while True:
        item = {
            "id": random.randint(1, 999999),
            "name": "".join(random.choices(chars, k=40)),
            "price": round(random.uniform(10, 500), 2),
            "available": random.choice([True, False]),
            "store_id": random.randint(1, 100),
            "category": random.choice(["dairy", "meat", "bakery", "beverages", "snacks"]),
            "description": "".join(random.choices(chars, k=120)),
        }
        items.append(item)
        if len(json.dumps(items).encode()) >= size_kb * 1024:
            break
    return {"count": len(items), "items": items}

print("Генеруємо payload ~200KB...")
PAYLOAD = generate_payload(200)
actual_size = len(json.dumps(PAYLOAD).encode())
print(f"Розмір payload: {actual_size / 1024:.1f} KB ({len(PAYLOAD['items'])} товарів)")

app = FastAPI()

@app.get("/data")
async def get_data():
    return JSONResponse(content=PAYLOAD)

def run_server():
    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="error", access_log=False)
    server = uvicorn.Server(config)
    server.run()

# ---------------------------------------------------------------------------
# Бенчмарк функції
# ---------------------------------------------------------------------------

def benchmark_requests_sync(n: int) -> float:
    session = req_lib.Session()
    def fetch(_):
        r = session.get(URL)
        r.raise_for_status()
        return len(r.content)
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=n) as ex:
        list(ex.map(fetch, range(n)))
    return time.perf_counter() - start

async def benchmark_httpx_async(n: int) -> float:
    async with httpx.AsyncClient() as client:
        start = time.perf_counter()
        await asyncio.gather(*[client.get(URL) for _ in range(n)])
        return time.perf_counter() - start

async def benchmark_curl_cffi_async(n: int) -> float:
    async with AsyncSession(impersonate="chrome") as session:
        start = time.perf_counter()
        await asyncio.gather(*[session.get(URL) for _ in range(n)])
        return time.perf_counter() - start

# ---------------------------------------------------------------------------
# Прогрів
# ---------------------------------------------------------------------------

async def warmup():
    print(f"\nПрогрів ({WARMUP_REQUESTS} запитів)...")
    async with httpx.AsyncClient() as client:
        for _ in range(WARMUP_REQUESTS):
            await client.get(URL)
    print("Прогрів завершено.")

# ---------------------------------------------------------------------------
# Основний цикл бенчмарку
# ---------------------------------------------------------------------------

async def run_benchmarks():
    results = {"requests": [], "httpx": [], "curl_cffi": []}

    for n in CONCURRENCY_LEVELS:
        print(f"\n--- Паралельність: {n} запитів ---")

        times = []
        for i in range(RUNS_PER_LEVEL):
            t = benchmark_requests_sync(n)
            times.append(t)
            print(f"  requests  run {i+1}: {t:.3f}s")
        results["requests"].append(statistics.mean(times))

        times = []
        for i in range(RUNS_PER_LEVEL):
            t = await benchmark_httpx_async(n)
            times.append(t)
            print(f"  httpx     run {i+1}: {t:.3f}s")
        results["httpx"].append(statistics.mean(times))

        times = []
        for i in range(RUNS_PER_LEVEL):
            t = await benchmark_curl_cffi_async(n)
            times.append(t)
            print(f"  curl_cffi run {i+1}: {t:.3f}s")
        results["curl_cffi"].append(statistics.mean(times))

    return results

# ---------------------------------------------------------------------------
# Графік — лише час виконання
# ---------------------------------------------------------------------------

COLORS = {
    "requests":  "#73726c",
    "httpx":     "#378add",
    "curl_cffi": "#1d9e75",
}

LABELS = {
    "requests":  "requests (threads)",
    "httpx":     "httpx (async)",
    "curl_cffi": "curl_cffi (async)",
}

def plot_results(results):
    x = np.arange(len(CONCURRENCY_LEVELS))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.suptitle(
        "Порівняння HTTP-клієнтів Python: requests vs httpx vs curl_cffi\n"
        f"Тестовий payload ~{actual_size/1024:.0f} KB, середнє з {RUNS_PER_LEVEL} запусків",
        fontsize=12, y=1.02
    )

    for i, (lib, color) in enumerate(COLORS.items()):
        bars = ax.bar(x + i * width, results[lib], width,
                      label=LABELS[lib], color=color, alpha=0.85)
        for bar, val in zip(bars, results[lib]):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.01,
                    f"{val:.2f}s", ha="center", va="bottom", fontsize=8)

    ax.set_xlabel("Кількість паралельних запитів")
    ax.set_ylabel("Час (с)")
    ax.set_title("Час виконання N запитів")
    ax.set_xticks(x + width)
    ax.set_xticklabels(CONCURRENCY_LEVELS)
    ax.legend(fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    plt.savefig("benchmark_results.png", dpi=150, bbox_inches="tight")
    print("\nГрафік збережено: benchmark_results.png")

# ---------------------------------------------------------------------------
# Таблиця результатів
# ---------------------------------------------------------------------------

def print_table(results):
    print("\n" + "=" * 65)
    print("РЕЗУЛЬТАТИ (середній час, с):")
    print(f"{'Паралельність':<16} {'requests':>12} {'httpx':>12} {'curl_cffi':>12}")
    print("-" * 55)
    for i, n in enumerate(CONCURRENCY_LEVELS):
        req_t = results["requests"][i]
        hpx_t = results["httpx"][i]
        curl_t = results["curl_cffi"][i]
        print(f"{n:<16} {req_t:>12.3f} {hpx_t:>12.3f} {curl_t:>12.3f}")

    print("\nПРИСКОРЕННЯ curl_cffi відносно інших (×):")
    print(f"{'Паралельність':<16} {'vs requests':>14} {'vs httpx':>14}")
    print("-" * 45)
    for i, n in enumerate(CONCURRENCY_LEVELS):
        vs_req = results["requests"][i] / results["curl_cffi"][i]
        vs_hpx = results["httpx"][i] / results["curl_cffi"][i]
        print(f"{n:<16} {vs_req:>14.2f}× {vs_hpx:>14.2f}×")

# ---------------------------------------------------------------------------
# Запуск
# ---------------------------------------------------------------------------

async def main():
    print("Запускаємо тестовий сервер...")
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    await asyncio.sleep(1.5)

    try:
        r = req_lib.get(URL, timeout=5)
        print(f"Сервер доступний. Розмір відповіді: {len(r.content) / 1024:.1f} KB")
    except Exception as e:
        print(f"Сервер недоступний: {e}")
        return

    await warmup()
    results = await run_benchmarks()
    print_table(results)
    plot_results(results)

if __name__ == "__main__":
    asyncio.run(main())