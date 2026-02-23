"""Users router — N+1 query anti-pattern in /users/{id}/tasks."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Task, User

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str
    email: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskSummary(BaseModel):
    id: int
    title: str
    priority: str
    status: str

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()


@router.post("/", response_model=UserResponse, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(**payload.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/{user_id}/tasks", response_model=list[TaskSummary])
def get_user_tasks(user_id: int, db: Session = Depends(get_db)):
    """Return all tasks owned by a user.

    BUG: This does a Python-level loop instead of a proper WHERE clause JOIN,
    simulating an N+1 anti-pattern.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # N+1 anti-pattern: fetches ALL tasks then filters in Python
    all_tasks = db.query(Task).all()
    return [t for t in all_tasks if t.owner_id == user_id]
