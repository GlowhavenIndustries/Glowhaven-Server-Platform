import os
from pathlib import Path

os.environ["HELIX_DB_PATH"] = str(Path(__file__).parent / "test.db")
os.environ["HELIX_BOOTSTRAP_PASSWORD"] = "TestPassword!234"
os.environ["HELIX_SECURE_COOKIES"] = "false"

from fastapi.testclient import TestClient

from helix.main import app, db

client = TestClient(app)


def login():
    response = client.post("/api/auth/login", json={"username": "admin", "password": "TestPassword!234"})
    assert response.status_code == 200
    csrf = client.get("/api/csrf")
    assert csrf.status_code == 200
    return client.cookies.get("helix_csrf")


def teardown_module():
    try:
        Path(db.path).unlink()
    except FileNotFoundError:
        pass


def test_login_and_csrf():
    csrf = login()
    response = client.post("/api/enrollment-tokens", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200
    assert len(response.json()["token"]) > 20


def test_mutation_requires_csrf():
    login()
    response = client.post("/api/enrollment-tokens")
    assert response.status_code == 403


def test_agent_registration_and_heartbeat():
    csrf = login()
    enroll = client.post("/api/enrollment-tokens", headers={"X-CSRF-Token": csrf}).json()["token"]
    registered = client.post("/api/agent/register", json={
        "enrollment_token": enroll,
        "name": "srv-01",
        "hostname": "srv-01",
        "platform": "Linux",
        "arch": "x86_64",
        "os_version": "test",
    })
    assert registered.status_code == 200
    key = registered.json()["agent_key"]
    hb = client.post("/api/agent/heartbeat", headers={"X-Helix-Agent-Key": key}, json={
        "hostname": "srv-01", "platform": "Linux", "arch": "x86_64", "os_version": "test",
        "cpu_percent": 12, "memory_percent": 20, "disk_percent": 30, "uptime_seconds": 100,
        "inventory": {"cpu_count": 8}, "labels": {"env": "prod"},
    })
    assert hb.status_code == 200
    servers = client.get("/api/servers")
    assert servers.status_code == 200
    assert servers.json()[0]["status"] == "online"


def test_job_action_validation():
    csrf = login()
    enroll = client.post("/api/enrollment-tokens", headers={"X-CSRF-Token": csrf}).json()["token"]
    registered = client.post("/api/agent/register", json={
        "enrollment_token": enroll, "name": "srv-02", "hostname": "srv-02", "platform": "Linux", "arch": "x86_64", "os_version": "test"
    }).json()
    response = client.post(f"/api/servers/{registered['server_id']}/jobs", headers={"X-CSRF-Token": csrf}, json={"action":"service_restart","params":{"service":"bad service"}})
    assert response.status_code == 422
