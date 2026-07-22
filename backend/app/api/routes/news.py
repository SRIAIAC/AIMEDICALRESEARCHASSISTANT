from fastapi import APIRouter

from app.services.news import get_medical_news

router = APIRouter(prefix="/news", tags=["news"])


@router.get("")
async def get_news() -> dict:
    return await get_medical_news()
