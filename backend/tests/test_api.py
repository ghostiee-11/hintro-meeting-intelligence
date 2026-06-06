"""Integration tests covering the unified envelope, auth, and the core workflow.

These run against the configured DATABASE_URL (local Postgres in dev, a Postgres
service in CI).
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_health_contract(client):
    res = await client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "UP"
    assert "checks" in body  # raw contract, not enveloped
    assert "success" not in body


async def test_evaluation_contract(client):
    res = await client.get("/api/evaluation")
    body = res.json()
    assert body["email"] == "aman0611kumar@gmail.com"
    assert "Telegram" in body["externalIntegration"]
    assert "success" not in body  # raw contract


async def test_validation_error_is_enveloped(client):
    res = await client.post(
        "/api/auth/register", json={"email": "bad", "name": "x", "password": "short"}
    )
    assert res.status_code == 422
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "traceId" in body


async def test_unauthorized_is_enveloped(client):
    res = await client.get("/api/meetings")
    assert res.status_code == 401
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


async def test_trace_header_present(client):
    res = await client.get("/api/evaluation")
    assert "x-trace-id" in {k.lower(): v for k, v in res.headers.items()}


async def test_full_workflow(client, unique_email):
    # Register
    reg = await client.post(
        "/api/auth/register",
        json={"email": unique_email, "name": "Flow User", "password": "password123"},
    )
    assert reg.status_code == 201
    token = reg.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create meeting
    meeting_res = await client.post(
        "/api/meetings",
        headers=headers,
        json={
            "title": "Sprint Planning",
            "participants": ["alice@example.com"],
            "meetingDate": "2026-05-20T10:00:00Z",
            "transcript": [
                {"timestamp": "00:10", "speaker": "John", "text": "We should launch next Friday."},
                {"timestamp": "00:20", "speaker": "Alice", "text": "I will prepare release notes."},
            ],
        },
    )
    assert meeting_res.status_code == 201
    meeting = meeting_res.json()["data"]
    assert meeting["segmentCount"] == 2
    meeting_id = meeting["id"]

    # List meetings (pagination envelope)
    listed = await client.get("/api/meetings", headers=headers)
    body = listed.json()["data"]
    assert body["meta"]["total"] >= 1
    assert any(m["id"] == meeting_id for m in body["items"])

    # Create an overdue action item
    ai_res = await client.post(
        "/api/action-items",
        headers=headers,
        json={
            "meetingId": meeting_id,
            "task": "Prepare release notes",
            "assignee": "Alice",
            "dueDate": "2020-01-01T00:00:00Z",
        },
    )
    assert ai_res.status_code == 201
    item = ai_res.json()["data"]
    assert item["status"] == "PENDING"
    item_id = item["id"]

    # It should appear in overdue
    overdue = await client.get("/api/action-items/overdue", headers=headers)
    overdue_ids = [i["id"] for i in overdue.json()["data"]["items"]]
    assert item_id in overdue_ids

    # Update status, then it should no longer be overdue
    patch = await client.patch(
        f"/api/action-items/{item_id}/status", headers=headers, json={"status": "COMPLETED"}
    )
    assert patch.json()["data"]["status"] == "COMPLETED"
    overdue2 = await client.get("/api/action-items/overdue", headers=headers)
    assert item_id not in [i["id"] for i in overdue2.json()["data"]["items"]]


async def test_invalid_status_rejected(client, unique_email):
    reg = await client.post(
        "/api/auth/register",
        json={"email": unique_email, "name": "X User", "password": "password123"},
    )
    token = reg.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}
    meeting_res = await client.post(
        "/api/meetings",
        headers=headers,
        json={
            "title": "M",
            "participants": [],
            "meetingDate": "2026-05-20T10:00:00Z",
            "transcript": [{"timestamp": "00:10", "speaker": "A", "text": "hi"}],
        },
    )
    meeting_id = meeting_res.json()["data"]["id"]
    ai = await client.post(
        "/api/action-items",
        headers=headers,
        json={"meetingId": meeting_id, "task": "t"},
    )
    item_id = ai.json()["data"]["id"]
    bad = await client.patch(
        f"/api/action-items/{item_id}/status", headers=headers, json={"status": "NONSENSE"}
    )
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "VALIDATION_ERROR"
