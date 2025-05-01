from fastapi import (
    FastAPI, WebSocket, WebSocketDisconnect, Depends, Cookie, Request
)
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from passlib.context import CryptContext
import json
from typing import Optional

from config import templates
from database import engine, get_db
from models import User, Message, Poll, Base
from dtos import *
from services.gcu import get_current_user
from services.cm import ConnectionManager


app = FastAPI()


Base.metadata.create_all(bind=engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


manager = ConnectionManager()


@app.get("/login")
async def login_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user)
):
    if current_user:
        return RedirectResponse(url="/profile")
    return templates.TemplateResponse("login.html", {
        "request": request,
        "user": None
    })



@app.get("/register")
async def register_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user)
):
    if current_user:
        return RedirectResponse(url="/profile")
    return templates.TemplateResponse("register.html", {
        "request": request,
        "user": None
    })


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie(key="session_token")
    return response


@app.get("/")
async def root(request: Request, current_user: Optional[User] = Depends(get_current_user), db: Session = Depends(get_db)):
    message_channels = db.query(Message.channel).distinct().limit(10).all()

    all_channels = set([channel[0] for channel in message_channels])

    channels = sorted(list(all_channels))

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": current_user,
        "channels": channels
    })

@app.get("/c/{channel_name}")
async def channel_chat(
    request: Request, 
    channel_name: str,
    current_user: Optional[User] = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login")
        
    messages = db.query(Message).join(User).filter(
        Message.channel == channel_name
    ).order_by(Message.timestamp).all()
    
    formatted_messages = []
    for msg in messages:
        message_data = {
            "id": msg.id,
            "content": msg.content,
            "username": msg.user.username,
            "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "is_own": msg.user.username == current_user.username,
        }
        
        if msg.parent_message_id:
            parent = db.query(Message).join(User).filter(Message.id == msg.parent_message_id).first()
            if parent:
                message_data["parent_message"] = {
                    "id": parent.id,
                    "content": parent.content,
                    "username": parent.user.username
                }
        
        formatted_messages.append(message_data)
    
    # Get channel polls
    polls = db.query(Poll).filter(Poll.channel == channel_name).all()
    formatted_polls = [{
        "id": poll.id,
        "title": poll.title,
        "description": poll.description,
        "created_at": poll.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "ends_at": poll.ends_at.strftime("%Y-%m-%d %H:%M:%S") if poll.ends_at else None,
        "is_active": poll.is_active,
        "creator_username": poll.creator.username,
        "options": [{"id": opt.id, "text": opt.text, "votes_count": opt.votes_count} for opt in poll.options],
        "total_votes": poll.total_votes,
        "user_vote": next((vote.option_id for vote in current_user.poll_votes if vote.option.poll_id == poll.id), None)
    } for poll in polls]
    
    return templates.TemplateResponse("channel.html", {
        "request": request,
        "user": current_user,
        "messages": formatted_messages,
        "channel_name": channel_name,
        "polls": formatted_polls
    })

@app.websocket("/ws/{channel_name}")
async def websocket_endpoint(
    websocket: WebSocket, 
    channel_name: str,
    session_token: Optional[str] = Cookie(None)
):
    if not session_token:
        await websocket.close(code=1008)
        return
    db = next(get_db())
    try:
        current_user = await get_current_user(session_token=session_token, db=db)
        if not current_user:
            await websocket.close(code=1008)
            return
            
        await manager.connect(websocket)

        try:
            while True:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                message = Message(
                    content=message_data['content'],
                    user_id=current_user.id,
                    channel=channel_name,
                    parent_message_id=message_data.get('parent_message_id')
                )
                db.add(message)
                db.commit()
                db.refresh(message)
                
                # Get parent message info if this is a reply
                parent_message_info = None
                if message.parent_message_id:
                    parent_message = db.query(Message).join(User).filter(Message.id == message.parent_message_id).first()
                    if parent_message:
                        parent_message_info = {
                            'id': parent_message.id,
                            'content': parent_message.content,
                            'username': parent_message.user.username
                        }
                
                # Prepare response data
                response_data = {
                    'id': message.id,
                    'content': message.content,
                    'username': current_user.username,
                    'timestamp': message.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    'parent_message': parent_message_info
                }
                
                await manager.broadcast(json.dumps(response_data))
        except WebSocketDisconnect:
            manager.disconnect(websocket)
    except Exception as e:
        await websocket.close(code=1011)
    finally:
        db.close()

@app.get("/channels")
async def channels_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login")
    
    # Get all unique channels from messages
    message_channels = db.query(Message.channel).distinct().all()
    channels = sorted([channel[0] for channel in message_channels])
    
    return templates.TemplateResponse("channels.html", {
        "request": request,
        "user": current_user,
        "channels": channels
    })

import routers.forum as forum
from routers import user
import routers.polls as polls
from routers import leaderboard
from services import auth_service, chat_protocol
from routers import profile, settings

# Add routers
app.include_router(forum.router)
app.include_router(user.router)
app.include_router(polls.router)
app.include_router(leaderboard.router)
app.include_router(auth_service.router)
app.include_router(chat_protocol.router)
app.include_router(profile.router)
app.include_router(settings.router)


