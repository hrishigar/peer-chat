"""Get current user"""
from typing import Optional
from fastapi import Depends, Cookie
from sqlalchemy.orm import Session
from database import get_db
from models import User
from config import SECRET_KEY
import jwt


async def get_current_user(session_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    if not session_token:
        return None
    try:
        payload = jwt.decode(session_token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("username")
        if username:
            user = db.query(User).filter(User.username == username).first()
            return user
    except jwt.InvalidTokenError:
        return None
    return None
