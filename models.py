from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel
from datetime import datetime

# This is the existing Session model, unchanged
class Session(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    topic: str
    transcript: str
    feedback_json: str
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    
    student_id: int = Field(foreign_key="user.id")
    student: "User" = Relationship(back_populates="sessions")

# This is the existing BatchJob model, unchanged
class BatchJob(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

# This is the existing Topic model, unchanged
class Topic(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    is_active: bool = Field(default=True)

# --- CORRECTED User and Class Models ---

class Class(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    class_code: str = Field(unique=True, index=True)
    
    teacher_id: int = Field(foreign_key="user.id")
    teacher: "User" = Relationship(
        back_populates="taught_classes",
        sa_relationship_kwargs={'foreign_keys': 'Class.teacher_id'}
    )
    
    students: List["User"] = Relationship(
        back_populates="student_class",
        sa_relationship_kwargs={'foreign_keys': '[User.class_id]'}
    )

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    full_name: str
    role: str # 'student' or 'teacher'
    class_id: Optional[int] = Field(default=None, foreign_key="class.id")

    # Existing relationships
    sessions: List["Session"] = Relationship(back_populates="student")
    batch_jobs: List["BatchJob"] = Relationship()
    
    # Corrected relationships for classes
    taught_classes: List["Class"] = Relationship(
        back_populates="teacher",
        sa_relationship_kwargs={'foreign_keys': '[Class.teacher_id]'}
    )
    student_class: Optional["Class"] = Relationship(
        back_populates="students",
        sa_relationship_kwargs={'foreign_keys': 'User.class_id'}
    )