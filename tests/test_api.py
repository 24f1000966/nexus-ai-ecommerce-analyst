"""End-to-end platform flow through the HTTP API."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.config import SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASSWORD
from backend.main import api

SAMPLE = Path(__file__).parent.parent / "trial-data" / "sample-company-data"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.4\n%test\n"
PASSWORD = "Company@123"


@pytest.fixture(scope="module")
def client():
    with TestClient(api) as c:
        yield c


def login(client, email, password=PASSWORD):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def register(client, name, gstin, pan, email):
    form = {
        "company_name": name, "website": f"https://{email.split('@')[1]}", "address": "Bengaluru",
        "cin": "U74999KA2015PTC123456", "gstin": gstin, "pan": pan, "md_name": "A. Founder",
        "data_types": "orders,products,customers", "data_purpose": "Sales analytics",
        "admin_name": "Finance Head", "admin_designation": "CFO", "admin_email": email,
        "admin_password": PASSWORD,
    }
    files = {"logo": ("logo.png", PNG, "image/png"), "signatory_letter": ("letter.pdf", PDF, "application/pdf")}
    r = client.post("/api/auth/register-company", data=form, files=files)
    assert r.status_code == 201, r.text
    return r.json()["company_id"]


@pytest.fixture(scope="module")
def companies(client):
    a = register(client, "TrendVista", "29ABCDE1234F1Z5", "ABCDE1234F", "cfo@trendvista.in")
    b = register(client, "UrbanKart", "27PQRSX5678K1Z3", "PQRSX5678K", "cfo@urbankart.in")
    return {"a": a, "b": b, "super": login(client, SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASSWORD)}


def test_pending_company_cannot_use_analytics(client, companies):
    h = login(client, "cfo@trendvista.in")
    assert client.get("/api/kpis", headers=h).status_code == 403


def test_super_admin_sees_verification_checks(client, companies):
    r = client.get(f"/api/admin/companies/{companies['a']}", headers=companies["super"])
    checks = {c["key"]: c["passed"] for c in r.json()["checks"]}
    assert checks["pan_gstin_match"] and checks["domain_match"]


def test_approve_then_demo_data(client, companies):
    for cid in (companies["a"], companies["b"]):
        r = client.post(f"/api/admin/companies/{cid}/approve", json={}, headers=companies["super"])
        assert r.status_code == 200
    k = client.get("/api/kpis", headers=login(client, "cfo@trendvista.in")).json()
    assert k["is_demo"] is True


def test_csv_validation_errors_are_readable(client, companies):
    h = login(client, "cfo@trendvista.in")
    bad = b"order_id,customer_id,order_date\n1,2,2026-01-01\n"
    r = client.post("/api/company/data/orders", files={"file": ("orders.csv", bad, "text/csv")}, headers=h)
    assert r.status_code == 422 and "status" in r.json()["detail"]
    dup = b"order_id,customer_id,order_date,status\n1,2,2026-01-01,Delivered\n1,3,2026-01-02,Delivered\n"
    r = client.post("/api/company/data/orders", files={"file": ("orders.csv", dup, "text/csv")}, headers=h)
    assert r.status_code == 422 and "unique" in r.json()["detail"]


def test_upload_switches_company_to_its_own_data(client, companies):
    h = login(client, "cfo@trendvista.in")
    for table in ("customers", "products", "orders", "order_items"):
        raw = (SAMPLE / f"{table}.csv").read_bytes()
        r = client.post(f"/api/company/data/{table}", files={"file": (f"{table}.csv", raw, "text/csv")}, headers=h)
        assert r.status_code == 200, r.text
    status = r.json()
    assert status["complete"] and status["active_source"] == "company" and status["warnings"] == []

    k = client.get("/api/kpis", headers=h).json()
    assert k["is_demo"] is False and k["period"] == "Sep 2025 – Mar 2026"

    # Biggest drop is the post-Diwali slump; February is the planted Beauty supply problem.
    ans = client.post("/api/ask", json={"question": "Why did sales drop?"}, headers=h).json()
    assert "2025-11" in ans["answer"] and ans["data_source"] == "Your uploaded data"
    ans = client.post("/api/ask", json={"question": "Why did sales drop in February?"}, headers=h).json()
    assert "2026-02" in ans["answer"] and "Beauty" in ans["answer"]


def test_other_company_is_isolated(client, companies):
    h = login(client, "cfo@urbankart.in")
    assert client.get("/api/kpis", headers=h).json()["is_demo"] is True
    ans = client.post("/api/ask", json={"question": "Why did sales drop?"}, headers=h).json()
    assert "Electronics" in ans["answer"]


def test_company_knowledge_base_feeds_rag(client, companies):
    h = login(client, "cfo@trendvista.in")
    raw = (SAMPLE / "trendvista_policies.md").read_bytes()
    r = client.post("/api/company/docs", files={"file": ("trendvista_policies.md", raw, "text/markdown")}, headers=h)
    assert r.status_code == 201
    q = {"question": "What is the festive exchange policy?"}
    ans = client.post("/api/ask", json=q, headers=h).json()
    assert ans["sources"] and "Festive" in ans["sources"][0]["section"]

    ans_b = client.post("/api/ask", json=q, headers=login(client, "cfo@urbankart.in")).json()
    assert all("Festive" not in s["section"] for s in ans_b["sources"])


def test_members_cannot_manage_data(client, companies):
    admin = login(client, "cfo@trendvista.in")
    r = client.post("/api/company/members", headers=admin, json={
        "full_name": "Ops Head", "designation": "Head of Operations",
        "email": "ops@trendvista.in", "password": "Member@123"})
    assert r.status_code == 201
    member = login(client, "ops@trendvista.in", "Member@123")
    assert client.get("/api/company/data", headers=member).status_code == 403
    assert client.post("/api/ask", json={"question": "top products"}, headers=member).status_code == 200
