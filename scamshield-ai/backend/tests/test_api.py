import os
os.environ["DATABASE_URL"] = "sqlite:///./test_scamshield.db"
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine
Base.metadata.create_all(bind=engine)
client = TestClient(app)

def test_register_and_scan():
    r = client.post("/api/auth/register", json={"name":"Test User","email":"test-run@example.com","password":"LongPassword!123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization":f"Bearer {token}"}
    scan = client.post("/api/scans/message", headers=headers, json={"text":"Your bank account will be blocked. Share OTP now."})
    assert scan.status_code == 200
    assert scan.json()["risk_score"] > 0
