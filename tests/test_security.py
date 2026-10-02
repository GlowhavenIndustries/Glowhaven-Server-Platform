import os
from pathlib import Path

os.environ["HELIX_DB_PATH"] = str(Path(__file__).parent / "test.db")
os.environ["HELIX_BOOTSTRAP_PASSWORD"] = "TestPassword!234"
os.environ["HELIX_SECURE_COOKIES"] = "false"

from fastapi.testclient import TestClient

from helix.main import app, db, rate_limiter

client = TestClient(app)


def login():
    rate_limiter.requests.clear()
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


def test_password_complexity_and_user_management():
    csrf = login()
    # Weak password fails validation
    weak_resp = client.post("/api/users", headers={"X-CSRF-Token": csrf}, json={"username": "op_weak", "password": "weak", "role": "operator"})
    assert weak_resp.status_code == 422

    # Strong password succeeds
    create_resp = client.post("/api/users", headers={"X-CSRF-Token": csrf}, json={"username": "op_user", "password": "OpUserPassword123!", "role": "operator"})
    assert create_resp.status_code == 200

    # Login as operator
    op_client = TestClient(app)
    op_login = op_client.post("/api/auth/login", json={"username": "op_user", "password": "OpUserPassword123!"})
    assert op_login.status_code == 200
    op_csrf = op_client.get("/api/csrf").json()["csrf_token"]

    # Operator cannot manage users or create enrollment tokens
    user_mgmt_attempt = op_client.get("/api/users")
    assert user_mgmt_attempt.status_code == 403
    token_attempt = op_client.post("/api/enrollment-tokens", headers={"X-CSRF-Token": op_csrf})
    assert token_attempt.status_code == 403


def test_totp_mfa_flow_and_stepup():
    csrf = login()
    mfa_user_resp = client.post("/api/users", headers={"X-CSRF-Token": csrf}, json={"username": "mfa_user", "password": "MfaUserPassword123!", "role": "operator"})
    assert mfa_user_resp.status_code == 200

    mfa_client = TestClient(app)
    mfa_client.post("/api/auth/login", json={"username": "mfa_user", "password": "MfaUserPassword123!"})
    mfa_csrf = mfa_client.get("/api/csrf").json()["csrf_token"]

    # Setup TOTP
    setup_resp = mfa_client.post("/api/auth/mfa/setup", headers={"X-CSRF-Token": mfa_csrf})
    assert setup_resp.status_code == 200
    totp_sec = setup_resp.json()["secret"]

    # Enable TOTP using valid code
    from helix.security import _totp_at
    import time
    now_counter = int(time.time() // 30)
    code = _totp_at(totp_sec, now_counter)

    enable_resp = mfa_client.post("/api/auth/mfa/enable", headers={"X-CSRF-Token": mfa_csrf}, json={"totp_code": code})
    assert enable_resp.status_code == 200

    # Logout and try login without TOTP code
    mfa_client.post("/api/auth/logout", headers={"X-CSRF-Token": mfa_csrf})
    login_no_totp = mfa_client.post("/api/auth/login", json={"username": "mfa_user", "password": "MfaUserPassword123!"})
    assert login_no_totp.status_code == 401

    # Login with valid TOTP code
    now_counter = int(time.time() // 30)
    code2 = _totp_at(totp_sec, now_counter)
    login_totp = mfa_client.post("/api/auth/login", json={"username": "mfa_user", "password": "MfaUserPassword123!", "totp_code": code2})
    assert login_totp.status_code == 200
    assert login_totp.json()["totp_enabled"] is True


def test_account_lockout():
    csrf = login()
    client.post("/api/users", headers={"X-CSRF-Token": csrf}, json={"username": "lock_target", "password": "TargetPassword123!", "role": "viewer"})

    target_client = TestClient(app)
    for _ in range(5):
        res = target_client.post("/api/auth/login", json={"username": "lock_target", "password": "WrongPassword!"})
        assert res.status_code == 401

    # 6th attempt should be locked out (HTTP 429)
    locked_res = target_client.post("/api/auth/login", json={"username": "lock_target", "password": "WrongPassword!"})
    assert locked_res.status_code == 429


def test_audit_integrity_verification():
    csrf = login()
    verify_resp = client.get("/api/audit/verify")
    assert verify_resp.status_code == 200
    assert verify_resp.json()["verified"] is True

    # Tamper with an audit entry in the database directly
    db.execute("UPDATE audit_log SET target='tampered_target' WHERE id=1")

    tampered_verify = client.get("/api/audit/verify")
    assert tampered_verify.status_code == 200
    assert tampered_verify.json()["verified"] is False
    assert tampered_verify.json()["tampered_id"] == 1
