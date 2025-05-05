from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from datetime import datetime
import enum
import random

Base = declarative_base()

def generate_random_username():
    return f"anon{random.randint(1000, 9999)}"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    bio = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    messages = relationship("Message", back_populates="user")
    posts = relationship("ForumPost", back_populates="author")
    comments = relationship("ForumComment", back_populates="author")
    viewed_posts = relationship("PostView", back_populates="user")
    created_polls = relationship("Poll", back_populates="creator")

    post_votes = relationship("PostVote", back_populates="user")
    comment_votes = relationship("CommentVote", back_populates="user")
    poll_votes = relationship("PollVote", back_populates="user")

    submitted_reports = relationship("Report", back_populates="reporter")

    @property
    def message_count(self):
        return len(self.messages)

    @property
    def post_count(self):
        return len(self.posts)

    @property
    def comment_count(self):
        return len(self.comments)

    @property
    def total_interactions(self):
        return self.message_count + self.post_count + self.comment_count

    @classmethod
    def generate_unique_username(cls, db):
        while True:
            username = generate_random_username()
            existing = db.query(cls).filter(cls.username == username).first()
            if not existing:
                return username


class PostView(Base):
    __tablename__ = "post_views"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("forum_posts.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    viewed_at = Column(DateTime, default=datetime.utcnow)
    
    post = relationship("ForumPost", back_populates="views_by_users")
    user = relationship("User", back_populates="viewed_posts")

class PostTag(enum.Enum):
    EDUCATION = "Education"
    TECHNOLOGY = "Technology" 
    PROGRAMMING = "Programming"
    CAREER = "Career"
    CAMPUS_LIFE = "Campus Life"
    EVENTS = "Events"
    PROJECTS = "Projects"
    INTERNSHIPS = "Internships"
    ACADEMICS = "Academics"
    GENERAL = "General"

class ForumPost(Base):
    __tablename__ = "forum_posts"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    author_id = Column(Integer, ForeignKey("users.id"))
    tag = Column(Enum(PostTag), nullable=False, default=PostTag.GENERAL)
    author = relationship("User", back_populates="posts")
    comments = relationship("ForumComment", back_populates="post", cascade="all, delete-orphan")
    views = Column(Integer, default=0)
    views_by_users = relationship("PostView", back_populates="post")
    votes = relationship("PostVote", back_populates="post")

    @property
    def upvotes(self):
        return sum(1 for vote in self.votes if vote.vote_type == 'up')

    @property
    def downvotes(self):
        return sum(1 for vote in self.votes if vote.vote_type == 'down')

    @property
    def score(self):
        return self.upvotes - self.downvotes


class ForumComment(Base):
    __tablename__ = "forum_comments"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    author_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("forum_posts.id"))
    parent_id = Column(Integer, ForeignKey("forum_comments.id"), nullable=True)
    author = relationship("User", back_populates="comments")
    post = relationship("ForumPost", back_populates="comments")
    replies = relationship(
        "ForumComment",
        backref=backref("parent", remote_side=[id]),
        cascade="all, delete-orphan",
        order_by="ForumComment.created_at"
    )
    votes = relationship("CommentVote", back_populates="comment")

    @property
    def upvotes(self):
        return sum(1 for vote in self.votes if vote.vote_type == 'up')

    @property
    def downvotes(self):
        return sum(1 for vote in self.votes if vote.vote_type == 'down')

    @property
    def score(self):
        return self.upvotes - self.downvotes

    def get_user_vote(self, user_id):
        user_vote = next((vote for vote in self.votes if vote.user_id == user_id), None)
        return user_vote.vote_type if user_vote else None

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    channel = Column(String, nullable=False, default="general")
    user_id = Column(Integer, ForeignKey("users.id"))
    parent_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    user = relationship("User", back_populates="messages")
    replies = relationship(
        "Message",
        backref=backref("parent_message", remote_side=[id]),
        cascade="all, delete-orphan"
    )
    reports = relationship("Report", back_populates="message")

class PostVote(Base):
    __tablename__ = "post_votes"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("forum_posts.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    vote_type = Column(String)  # 'up' or 'down'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    post = relationship("ForumPost", back_populates="votes")
    user = relationship("User", back_populates="post_votes")

class CommentVote(Base):
    __tablename__ = "comment_votes"
    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(Integer, ForeignKey("forum_comments.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    vote_type = Column(String)  # 'up' or 'down'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    comment = relationship("ForumComment", back_populates="votes")
    user = relationship("User", back_populates="comment_votes")

class Poll(Base):
    __tablename__ = "polls"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    ends_at = Column(DateTime, nullable=True)
    channel = Column(String, nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"))
    
    creator = relationship("User", back_populates="created_polls")
    options = relationship("PollOption", back_populates="poll", cascade="all, delete-orphan")
    
    @property
    def is_active(self):
        if not self.ends_at:
            return True
        return datetime.utcnow() < self.ends_at
    
    @property
    def total_votes(self):
        return sum(option.votes_count for option in self.options)

class PollOption(Base):
    __tablename__ = "poll_options"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False)
    poll_id = Column(Integer, ForeignKey("polls.id"))
    
    poll = relationship("Poll", back_populates="options")
    votes = relationship("PollVote", back_populates="option", cascade="all, delete-orphan")
    
    @property
    def votes_count(self):
        return len(self.votes)

class PollVote(Base):
    __tablename__ = "poll_votes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    option_id = Column(Integer, ForeignKey("poll_options.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="poll_votes")
    option = relationship("PollOption", back_populates="votes")

class ReportReason(enum.Enum):
    HARASSMENT = "Harassment"
    SPAM = "Spam"
    INAPPROPRIATE = "Inappropriate Content"
    HATE_SPEECH = "Hate Speech"
    OTHER = "Other"

class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"))
    reporter_id = Column(Integer, ForeignKey("users.id"))
    reason = Column(Enum(ReportReason), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")
    
    message = relationship("Message", back_populates="reports")
    reporter = relationship("User", back_populates="submitted_reports")


