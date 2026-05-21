import asyncio

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from jinja2 import Environment, FileSystemLoader

from core.db import get_db
from models.user import User
from models.tv_settings import TVSettings
from core.security import verify_password
from core.scheduler import schedule_playlist_job, cancel_playlist_job, download_playlist

router = APIRouter()
env = Environment(loader=FileSystemLoader("./templates"))


@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, db: Session = Depends(get_db)):
    user_cookie = request.cookies.get("auth")
    if not user_cookie:
        return HTMLResponse(env.get_template("login.html").render())

    tv = db.query(TVSettings).first()
    if not tv:
        tv = TVSettings(tv_link="", delivery_type="redirect", update_interval_hours=6, cached_filename="playlist.m3u")
        db.add(tv)
        db.commit()
        db.refresh(tv)

    last_cached = tv.last_cached_at.strftime("%d.%m.%Y %H:%M UTC") if tv.last_cached_at else None
    return HTMLResponse(env.get_template("admin.html").render(
        current_link=tv.tv_link,
        delivery_type=tv.delivery_type or "redirect",
        update_interval_hours=tv.update_interval_hours or 6,
        last_cached_at=last_cached,
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
    db: Session = Depends(get_db),
):
    if not request.cookies.get("auth"):
        return RedirectResponse("/admin", status_code=302)

    tv = db.query(TVSettings).first()
    tv.tv_link = tv_link
    tv.delivery_type = delivery_type
    tv.update_interval_hours = max(1, min(24, update_interval_hours))
    db.commit()

    if delivery_type == "cached" and tv_link:
        schedule_playlist_job(tv_link, tv.update_interval_hours)
        asyncio.create_task(download_playlist(tv_link))
    else:
        cancel_playlist_job()

    return RedirectResponse("/admin", status_code=302)
