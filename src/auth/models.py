from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable
from sqlalchemy.orm import relationship
from src.database import Base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Enum, Text, func, TIMESTAMP
from datetime import datetime
from enum import Enum as PyEnum

class User(SQLAlchemyBaseUserTable[int] ,Base):
    __tablename__ = 'users'
    id = Column("id", Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password: str = Column(String(length=1024), nullable=False)

class TaskStatus(PyEnum):
    PENDING = "Ожидание выполнения"
    COMPLETED = "Завершено"
    IN_PROGRESS = "В процессе"

# Team model
class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    members = Column(JSON, nullable=False)  # JSON field with user IDs
    leader_id = Column(Integer, nullable=False)  # ID of the team leader

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # ID of the task creator
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column("created_at", TIMESTAMP, default=datetime.utcnow())
    priority = Column(Integer, nullable=False, default=1)
    due_date = Column(DateTime, nullable=True)  # Null if no deadline
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)

# TeamTask model for team tasks
class TeamTask(Base):
    __tablename__ = "team_tasks"
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)  # ID of the team to which the task belongs
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # ID of the task creator
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Assignee ID, nullable initially
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)  # Null if no deadline
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)

    # Relationships
    team = relationship("Team", back_populates="tasks")
    creator = relationship("User", foreign_keys=[creator_id])
    assignee = relationship("User", foreign_keys=[assignee_id])

# Relationships between models
Team.tasks = relationship("TeamTask", back_populates="team", cascade="all, delete-orphan")