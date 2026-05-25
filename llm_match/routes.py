from fastapi import APIRouter, Security
from llm_match import LLMMatcher
from auth import verify_token
from models import MatchRequest

router = APIRouter()
matcher = LLMMatcher()


@router.post("/match")
async def match(req: MatchRequest, _token: str = Security(verify_token)):
    return await matcher.match_raw(
        shops=[s.model_dump() for s in req.shops],
        mode=req.mode,
    )

@router.get("/auth")
async def auth(_token: str = Security(verify_token)):
    return {"status": "ok"}

@router.get("/health")
async def health():
    return {"status": "ok"}
