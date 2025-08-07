from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel
from datetime import datetime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    full_name: str
    role: str # 'student' or 'teacher'

    sessions: List["Session"] = Relationship(back_populates="student")

class Session(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    topic: str
    transcript: str
    feedback_json: str
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    
    student_id: int = Field(foreign_key="user.id")
    student: User = Relationship(back_populates="sessions")

class Topic(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    is_active: bool = Field(default=True)