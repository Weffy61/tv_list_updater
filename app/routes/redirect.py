from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from core.db import get_db
from models.tv_settings import TVSettings

router = APIRouter()


@router.get("/tv")
async def redirect_to_tv(db: Session = Depends(get_db)):
    settings = db.query(TVSettings).first()
    if not settings or not settings.tv_link:
        return {"error": "TV link not set"}
    return RedirectResponse(settings.tv_link)
