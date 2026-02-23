"""Tests for the TaskFlow API.

Run with:
    pytest tests/ -v

Some tests intentionally FAIL to give TooLoo something to fix.
"""

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestTaskCRUD:
    def test_create_task(self):
        resp = client.post("/tasks/", json={"title": "Write tests", "priority": "high"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Write tests"
        assert data["priority"] == "high"

    def test_create_task_invalid_priority_is_rejected(self):
        """BUG: This currently passes (no validation), but it should return 422."""
        resp = client.post("/tasks/", json={"title": "Bad task", "priority": "CRITICAL"})
        # Expecting 422 Unprocessable Entity — FAILS because no enum validation
        assert resp.status_code == 422

    def test_delete_nonexistent_task_returns_404(self):
        """BUG: Currently returns 200 even when task doesn't exist."""
        resp = client.delete("/tasks/99999")
        assert resp.status_code == 404

    def test_update_task_sets_updated_at(self):
        """BUG: updated_at is never populated on PATCH."""
        create_resp = client.post("/tasks/", json={"title": "Timestamps matter"})
        assert create_resp.status_code == 201
        task_id = create_resp.json()["id"]

        patch_resp = client.patch(f"/tasks/{task_id}", json={"status": "done"})
        assert patch_resp.status_code == 200
        updated = patch_resp.json()
        assert updated["updated_at"] is not None  # FAILS — always None


class TestUsersTasks:
    def test_get_user_tasks_uses_db_filter(self):
        """Regression: ensure /users/{id}/tasks filters at DB level, not Python."""
        # Create a user
        user_resp = client.post("/users/", json={"name": "Alice", "email": "alice@test.com"})
        assert user_resp.status_code in (201, 409)
        user_id = user_resp.json().get("id", 1)

        resp = client.get(f"/users/{user_id}/tasks")
        assert resp.status_code == 200
        # All returned tasks must belong to the user
        for task in resp.json():
            assert task.get("owner_id") == user_id  # FAILS due to N+1 pattern returning wrong data
