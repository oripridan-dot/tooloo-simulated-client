"""
Simulated Product: TaskFlow API
================================
A simple FastAPI task-management application.
This repo serves as a reference client for TooLoo integration tests.

All intentional bugs have been fixed by TooLoo eradication mandate:
  1. tasks router now validates `priority` enum (low/medium/high only).
  2. DELETE /tasks/{id} returns 404 when the task does not exist.
  3. /users/{id}/tasks uses a single SQL WHERE filter (no N+1).
  4. updated_at is now populated on every PATCH.
  5. Global exception handler added for unhandled SQLAlchemy errors.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from database import init_db
from routers import tasks, users

logger = logging.getLogger("taskflow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="TaskFlow API",
    description="Simulated client for TooLoo integration testing",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(users.router, prefix="/users", tags=["users"])


# FIX 5: global exception handler for unhandled DB errors
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error("Unhandled DB error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "A database error occurred. Please try again later."},
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "taskflow-api", "version": "0.2.0"}
