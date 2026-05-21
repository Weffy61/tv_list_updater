import asyncio
from typing import Optional

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from jinja2 import Environment, FileSystemLoader

from core.db import get_db
from models.user import User
from models.tv_settings import TVSettings, DeliveryType
from core.security import verify_password
from core.scheduler import schedule_playlist_job, cancel_playlist_job, download_playlist

router = APIRouter()
env = Environment(loader=FileSystemLoader("./templates"))
_download_task: Optional[asyncio.Task] = None


def _is_authenticated(request: Request, db: Session) -> bool:
    username = request.cookies.get("auth")
    return bool(username and db.query(User).filter(User.username == username).first())


@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, db: Session = Depends(get_db)):
    if not request.cookies.get("auth"):
        return HTMLResponse(env.get_template("login.html").render())

    tv = db.query(TVSettings).first()
    last_cached = tv.last_cached_at.strftime("%d.%m.%Y %H:%M UTC") if tv and tv.last_cached_at else None
    return HTMLResponse(env.get_template("admin.html").render(
        current_link=tv.tv_link if tv else "",
        delivery_type=(tv.delivery_type if tv else DeliveryType.REDIRECT),
        update_interval_hours=(tv.update_interval_hours if tv else 6),
        last_cached_at=last_cached,
        xxx_link=(tv.xxx_link or "") if tv else "",
    ))


@router.post("/admin/login")
async def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return HTMLResponse(
            env.get_template("login.html").render(error="Неверный логин или пароль"),
            status_code=401,
        )
    resp = RedirectResponse("/admin", status_code=302)
    resp.set_cookie("auth", user.username, httponly=True)
    return resp


@router.post("/admin/update")
async def update_link(
    request: Request,
    tv_link: str = Form(...),
    delivery_type: str = Form(...),
    update_interval_hours: int = Form(6),
    xxx_link: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    global _download_task
    if not _is_authenticated(request, db):
        return RedirectResponse("/admin", status_code=302)

    tv = db.query(TVSettings).first()
    tv.tv_link = tv_link
    tv.delivery_type = delivery_type
    tv.update_interval_hours = max(1, min(24, update_interval_hours))
    tv.xxx_link = xxx_link.strip() if xxx_link and xxx_link.strip() else None
    db.commit()

    if delivery_type == DeliveryType.CACHED and tv_link:
        schedule_playlist_job(tv.update_interval_hours)
        if _download_task and not _download_task.done():
            _download_task.cancel()
        _download_task = asyncio.create_task(download_playlist())
    else:
        cancel_playlist_job()

    return RedirectResponse("/admin", status_code=302)
