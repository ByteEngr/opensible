"""Unit and integration tests for admin worker management API routes and admin auth checks."""
from __future__ import annotations

import pytest
from flask import Flask, request
from api.admin_routes import check_admin_auth
from auth.service import generate_token
from auth.middleware import get_internal_call_secret


@pytest.fixture
def test_app(data_dir, monkeypatch):
    """Create a test Flask application with admin blueprint registered."""
    import app as main_app_mod
    app = main_app_mod.app
    app.config["TESTING"] = True
    return app


def test_check_admin_auth_direct():
    """Direct unit tests for check_admin_auth helper logic."""
    app = Flask("test_app")
    with app.test_request_context("/"):
        # Case 1: No current_user set
        assert check_admin_auth() is False

        # Case 2: Internal caller
        request.current_user = {"user_id": "__internal__", "roles": ["admin"]}
        assert check_admin_auth() is True

        # Case 3: Standard admin role (lowercase)
        request.current_user = {"user_id": "u-123", "username": "alice", "roles": ["admin"]}
        assert check_admin_auth() is True

        # Case 4: Title-case Admin role
        request.current_user = {"user_id": "u-124", "username": "bob", "roles": ["Admin"]}
        assert check_admin_auth() is True

        # Case 5: Non-admin role
        request.current_user = {"user_id": "u-125", "username": "charlie", "roles": ["operator", "viewer"]}
        assert check_admin_auth() is False

        # Case 6: Empty roles list
        request.current_user = {"user_id": "u-126", "username": "dave", "roles": []}
        assert check_admin_auth() is False


def test_api_admin_list_workers_unauthenticated(test_app):
    """Unauthenticated requests to /api/admin/workers should return 401."""
    with test_app.test_client() as client:
        res = client.get("/api/admin/workers")
        assert res.status_code == 401
        data = res.get_json()
        assert data["error"] == "Authentication required"


def test_api_admin_list_workers_non_admin(test_app, data_dir):
    """Authenticated non-admin user requests should return 403 Permission Denied."""
    non_admin_token = generate_token(
        user_id="user-non-admin",
        username="regular_user",
        roles=["viewer"],
        data_dir=data_dir,
    )
    with test_app.test_client() as client:
        res = client.get(
            "/api/admin/workers",
            headers={"Authorization": f"Bearer {non_admin_token}"},
        )
        assert res.status_code == 403
        data = res.get_json()
        assert data["success"] is False
        assert data["error"] == "Permission denied"


def test_api_admin_list_workers_admin_user(test_app, data_dir, workers_env):
    """Authenticated admin user requests should succeed with 200 OK."""
    admin_token = generate_token(
        user_id="user-admin-1",
        username="admin_user",
        roles=["admin"],
        data_dir=data_dir,
    )
    with test_app.test_client() as client:
        res = client.get(
            "/api/admin/workers",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert "workers" in data


def test_api_admin_list_workers_internal_call(test_app, workers_env):
    """Internal system calls with X-Internal-Call header should succeed with 200 OK."""
    internal_secret = get_internal_call_secret()
    with test_app.test_client() as client:
        res = client.get(
            "/api/admin/workers",
            headers={"X-Internal-Call": internal_secret},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True


def test_api_admin_create_worker_non_admin_rejected(test_app, data_dir):
    """POST /api/admin/workers by non-admin should be rejected with 403."""
    non_admin_token = generate_token(
        user_id="user-operator",
        username="operator",
        roles=["operator"],
        data_dir=data_dir,
    )
    with test_app.test_client() as client:
        res = client.post(
            "/api/admin/workers",
            headers={"Authorization": f"Bearer {non_admin_token}"},
            json={"name": "test-worker"},
        )
        assert res.status_code == 403
        data = res.get_json()
        assert data["error"] == "Permission denied"
