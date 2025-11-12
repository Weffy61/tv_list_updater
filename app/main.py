from fastapi import FastAPI
from core.db import Base, engine, SessionLocal
from models.user import User
from core.security import hash_password
from core.config import settings
from routes import admin, redirect

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TV Redirector")
app.include_router(admin.router)
app.include_router(redirect.router)

with SessionLocal() as db:
    if not db.query(User).first():
        user = User(
            username=settings.ADMIN_USERNAME,
            password_hash=hash_password(settings.ADMIN_PASSWORD)
        )
        db.add(user)
        db.commit()



