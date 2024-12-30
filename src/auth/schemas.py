from datetime import datetime
from typing import Optional, List

from fastapi_users import schemas
from pydantic import BaseModel, Field

from src.auth.models import TaskStatus


class UserRead(schemas.BaseUser[int]):
    id: int
    username: str

    class Config:
        from_attributes = True

class UserCreate(schemas.BaseUserCreate):
    username: str
    password: str

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[int] = Field(default=1)

class TaskCreate(TaskBase):
    status: TaskStatus = TaskStatus.PENDING
    pass

class TaskUpdate(TaskBase):
    id: int
    status: TaskStatus = TaskStatus.IN_PROGRESS
    pass

class TeamBase(BaseModel):
    name: str

class TeamCreate(TeamBase):
    pass

class TeamRead(TeamBase):
    id: int
    members: List[int]
    leader_id: int

    class Config:
        orm_mode = True

class TeamUserAdd(BaseModel):
    id: int
    username: str

class TeamUserDelete(TeamUserAdd):
    pass

class TeamTaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    assignee_id: Optional[int] = None
    status: TaskStatus = TaskStatus.PENDING

class TeamTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    assignee_id: Optional[int] = None
    status: Optional[TaskStatus] = None