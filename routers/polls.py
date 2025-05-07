from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta

from main import get_db
from models import User, Poll, PollOption, PollVote
from config import templates
from sqlalchemy.exc import SQLAlchemyError
from services.gcu import get_current_user

router = APIRouter(
    prefix="/p",
    tags=["polls"]
)

@router.get("/{channel_name}")
async def channel_polls(
    request: Request,
    channel_name: str,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login")
    
    try:
        # Get all polls for the channel
        polls = db.query(Poll).filter(Poll.channel == channel_name).order_by(Poll.created_at.desc()).all()
        
        # Format polls data
        formatted_polls = [{
            "id": poll.id,
            "title": poll.title,
            "description": poll.description,
            "created_at": poll.created_at,
            "ends_at": poll.ends_at,
            "is_active": poll.is_active,
            "creator_username": poll.creator.username,
            "options": [{"id": opt.id, "text": opt.text, "votes_count": opt.votes_count} for opt in poll.options],
            "total_votes": poll.total_votes,
            "user_vote": next((vote.option_id for vote in current_user.poll_votes if vote.option.poll_id == poll.id), None)
        } for poll in polls]

        return templates.TemplateResponse("channel_polls.html", {
            "request": request,
            "user": current_user,
            "channel_name": channel_name,
            "polls": formatted_polls
        })
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{channel_name}/create")
async def create_poll(
    request: Request,
    channel_name: str,
    title: str = Form(...),
    description: str = Form(None),
    duration_hours: Optional[int] = Form(None),
    options: List[str] = Form(...),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401)
    
    try:
        ends_at = None
        if duration_hours:
            ends_at = datetime.utcnow() + timedelta(hours=duration_hours)

        poll = Poll(
            title=title,
            description=description,
            channel=channel_name,
            creator_id=current_user.id,
            ends_at=ends_at
        )
        db.add(poll)
        db.flush()

        for option_text in options:
            if option_text.strip():
                option = PollOption(text=option_text, poll_id=poll.id)
                db.add(option)

        db.commit()
        return RedirectResponse(url=f"/p/{channel_name}", status_code=303)
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{channel_name}/vote/{poll_id}")
async def vote_on_poll(
    channel_name: str,
    poll_id: int,
    option_id: int = Form(...),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    
    # Check if poll exists
    poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if not poll:
        return JSONResponse(status_code=404, content={"detail": "Poll not found"})

    current_time = datetime.utcnow()
    if poll.ends_at and current_time > (poll.ends_at + timedelta(minutes=5)):
        return JSONResponse(status_code=400, content={"detail": "Poll has ended"})
    
    # Check if option belongs to poll
    option = db.query(PollOption).filter(
        PollOption.id == option_id,
        PollOption.poll_id == poll_id
    ).first()
    if not option:
        return JSONResponse(status_code=404, content={"detail": "Option not found"})

    try:
        existing_vote = db.query(PollVote).filter(
            PollVote.user_id == current_user.id,
            PollVote.option.has(poll_id=poll_id)
        ).first()

        if existing_vote:
            if existing_vote.option_id == option_id:
                db.delete(existing_vote)
            else:
                existing_vote.option_id = option_id
        else:
            vote = PollVote(user_id=current_user.id, option_id=option_id)
            db.add(vote)

        db.commit()
        db.refresh(poll)

        # Return updated poll data
        return {
            "poll_id": poll.id,
            "options": [{"id": opt.id, "votes_count": opt.votes_count} for opt in poll.options],
            "total_votes": poll.total_votes,
            "user_vote": option_id if not existing_vote or existing_vote.option_id == option_id else None
        }
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        return JSONResponse(status_code=500, content={"detail": "Database error"}) 