"""
Simulated Product: TaskFlow API
================================
A simple FastAPI task-management application.
This repo serves as a reference client for TooLoo integration tests.

Known issues (intentional for TooLoo to discover and fix):
  1. tasks router does NOT validate `priority` enum — accepts any string.   ✅ FIXED
  2. DELETE /tasks/{id} returns 200 even when the task does not exist.       ✅ FIXED
  3. The /users/{id}/tasks endpoint performs a pure Python loop instead
     of a single JOIN query (N+1 anti-pattern).                              ✅ FIXED
  4. No global exception handler — unhandled DB errors bubble as 500 HTML.  ✅ FIXED
  5. Missing `updated_at` timestamp on task mutation endpoints.              ✅ FIXED
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from database import init_db
from routers import tasks, users

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="TaskFlow API",
    description="Simulated client for TooLoo integration testing",
    version="0.1.0",
    lifespan=lifespan,
)

# FIX 4: Global exception handler — DB errors return structured JSON, not HTML
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error("Database error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "A database error occurred. Please try again later."},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred."},
    )


app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(users.router, prefix="/users", tags=["users"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "taskflow-api", "version": "0.1.0"}
