from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from jinja2 import Environment, FileSystemLoader
from core.db import get_db
from models.user import User
from models.tv_settings import TVSettings
from core.security import verify_password, hash_password

router = APIRouter()
env = Environment(loader=FileSystemLoader("./templates"))


@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, db: Session = Depends(get_db)):
    user_cookie = request.cookies.get("auth")
    if not user_cookie:
        template = env.get_template("login.html")
        return HTMLResponse(template.render())

    settings = db.query(TVSettings).first()
    if not settings:
        settings = TVSettings(tv_link="")
        db.add(settings)
        db.commit()
        db.refresh(settings)
    template = env.get_template("admin.html")
    return HTMLResponse(template.render(current_link=settings.tv_link))


@router.post("/admin/login")
async def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        template = env.get_template("login.html")
        return HTMLResponse(template.render(error="Неверный логин или пароль"), status_code=401)

    resp = RedirectResponse("/admin", status_code=302)
    resp.set_cookie("auth", user.username, httponly=True)
    return resp


@router.post("/admin/update")
async def update_link(request: Request, tv_link: str = Form(...), db: Session = Depends(get_db)):
    username = request.cookies.get("auth")
    if not username:
        return RedirectResponse("/admin", status_code=302)

    settings = db.query(TVSettings).first()
    settings.tv_link = tv_link
    db.commit()
    return RedirectResponse("/admin", status_code=302)
