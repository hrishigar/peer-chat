from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from main import get_db
from models import User
from config import templates
from services.gcu import get_current_user

router = APIRouter(
    prefix="/profile",
    tags=["profile"]
)

@router.get("")
async def profile_page(
    request: Request, 
    current_user: Optional[User] = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login")
        
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": current_user,
    })

@router.post("/update")
async def update_profile(
    request: Request,
    email: str = Form(None),
    bio: str = Form(None),
    avatar_url: str = Form(None),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Update user information
        current_user.email = email
        current_user.bio = bio
        current_user.avatar_url = avatar_url
        
        db.commit()
        
        return RedirectResponse(url="/profile", status_code=303)
    except Exception as e:
        print(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail="Error updating profile")