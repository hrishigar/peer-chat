from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from main import get_db, pwd_context
from models import User
from config import templates
from services.gcu import get_current_user

router = APIRouter(
    prefix="",
    tags=["settings"]
)

@router.get("/settings")
async def settings_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "user": current_user
    })

@router.post("/api/settings/generate-username")
async def generate_username(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    new_username = User.generate_unique_username(db)
    return {"username": new_username}

@router.post("/api/settings/profile")
async def update_profile(
    username: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check if username is taken by another user
    if username != current_user.username:
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken")
        current_user.username = username
    
    db.commit()
    return RedirectResponse(url="/settings", status_code=303)

@router.post("/api/settings/password")
async def change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify current password
    if not pwd_context.verify(current_password, current_user.password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Verify new passwords match
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")
    
    # Update password
    current_user.password = pwd_context.hash(new_password)
    db.commit()
    
    return RedirectResponse(url="/settings", status_code=303)
