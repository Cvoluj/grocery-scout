import os
from dotenv import load_dotenv
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from jinja2 import Environment, FileSystemLoader

from src.settings import TEMPLATES_DIR
from src.email.schemas import ReceiptData
load_dotenv()


SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM")

BRANDS: dict[str, dict] = {
    "atb":   {"label": "АТБ",   "bg": "#FEF3C7", "color": "#92400E"},
    "varus": {"label": "Варус", "bg": "#DBEAFE", "color": "#1E40AF"},
}


def _make_jinja_env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)

    def plural_uk(n: int, one: str, few: str, many: str) -> str:
        if 11 <= n % 100 <= 14:
            return many
        if n % 10 == 1:
            return one
        if 2 <= n % 10 <= 4:
            return few
        return many

    def maps_url(r: "EnrichedReceipt") -> str:
        if r.lat and r.lon:
            return f"https://www.google.com/maps/search/?api=1&query={r.lat},{r.lon}"
        return f"https://www.google.com/maps/search/?api=1&query={r.data.shop_name.replace(' ', '+')}"

    env.filters["plural_uk"] = plural_uk
    env.filters["maps_url"] = maps_url
    return env


_jinja_env = _make_jinja_env()


@dataclass
class EnrichedReceipt:
    data: ReceiptData
    lat: float | None
    lon: float | None
    is_best: bool


def build_html(receipts: list[EnrichedReceipt], user_email: str) -> str:
    total_items = receipts[0].data.total_count if receipts else 0
    template = _jinja_env.get_template("receipt.html.jinja2")
    return template.render(
        receipts=receipts,
        user_email=user_email,
        total_items=total_items,
        BRANDS=BRANDS,
    )


async def send_receipt_email(to: str, receipts: list[EnrichedReceipt]) -> None:
    html = build_html(receipts, to)
    total_items = receipts[0].data.total_count if receipts else 0

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"GroceryScout - список покупок ({total_items} товарів)"
    msg["From"] = SMTP_FROM
    msg["To"] = to
    msg.attach(MIMEText(html, "html", "utf-8"))

    await aiosmtplib.send(
        msg,
        hostname=SMTP_HOST,
        port=SMTP_PORT,
        username=SMTP_USER,
        password=SMTP_PASSWORD,
        start_tls=True,
    )
