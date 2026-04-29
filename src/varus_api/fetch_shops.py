from curl_cffi import AsyncSession, Response

from src.models.shops import VarusShop


headers = {
    'accept': 'application/json',
    'accept-language': 'ru-RU,ru;q=0.9',
    'cache-control': 'no-cache',
    'content-type': 'application/json',
    'pragma': 'no-cache',
    'priority': 'u=1, i',
    'referer': 'https://varus.ua/search?q=%D1%8F%D0%B9%D1%86%D1%8F%D1%96',
    'sec-ch-ua': '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'traceparent': '00-1f3bcb087a37fb079db1a1b6630680d0-9290d0922f65068c-01',
    'tracestate': 'es=s:1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
}






if __name__ == '__main__':
    import asyncio

    loop = asyncio.get_event_loop()
    varus_shops = loop.run_until_complete(fetch_kyiv_stores())
    print(varus_shops)