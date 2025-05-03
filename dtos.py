from pydantic import BaseModel
from datetime import datetime
from typing import List


class PollOptionCreate(BaseModel):
    text: str

class PollCreate(BaseModel):
    title: str
    description: str | None = None
    options: List[str]
    duration_hours: int | None = None

class PollOptionResponse(BaseModel):
    id: int
    text: str
    votes_count: int

class PollResponse(BaseModel):
    id: int
    title: str
    description: str | None
    created_at: datetime
    ends_at: datetime | None
    is_active: bool
    creator_username: str
    options: List[PollOptionResponse]
    total_votes: int
    user_vote: int | None

class ReportCreate(BaseModel):
    message_id: int
    reason: str
    details: str | None = None