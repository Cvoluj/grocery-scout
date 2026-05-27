import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.deps import get_current_user
from src.email.schemas import SendReceiptRequest
from src.email.tasks import send_receipt_task

router = APIRouter(prefix="/api")


@router.post("/send-receipt", status_code=status.HTTP_202_ACCEPTED)
async def send_receipt(
    req: SendReceiptRequest,
    current_user: asyncpg.Record = Depends(get_current_user),
):
    if not req.receipts:
        raise HTTPException(status_code=400, detail="Empty cart")

    await send_receipt_task.kiq(
        to=current_user["email"],
        receipts=[r.model_dump() for r in req.receipts],
        shop_ids=req.shop_ids,
    )
    return {"ok": True}