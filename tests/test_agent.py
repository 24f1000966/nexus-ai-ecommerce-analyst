import pytest

from app import agent, db


@pytest.mark.parametrize("question,intent", [
    ("What are the top 5 selling products?", "top_products"),
    ("Show the sales trend by month", "sales_trend"),
    ("Which products are low in stock?", "low_stock"),
    ("What is your return policy?", "policy"),
    ("Why did sales drop in July?", "why_drop"),
    ("Detect anomalies in sales", "anomaly"),
    ("Tell me about elephants", "general"),
])
def test_intent_classification(question, intent):
    assert agent.classify_intent(question) == intent


def test_why_drop_finds_the_planted_electronics_stockout():
    r = agent.answer("Why did sales drop in July?")
    assert r.intent == "why_drop"
    assert "2026-07" in r.answer and "Electronics" in r.answer
    assert len(r.steps) >= 6
    assert r.sources, "root-cause analysis should cite policy context"


def test_anomaly_detection_flags_july():
    r = agent.answer("Detect anomalies in sales")
    assert "2026-07" in r.answer


def test_policy_answer_has_citations():
    r = agent.answer("Can I pay cash on delivery?")
    assert r.intent == "policy"
    assert r.sources[0]["doc"] == "shipping_policy"


def test_unknown_question_offline_explains_capabilities():
    r = agent.answer("how many unicorns live on mars")
    assert r.intent == "unknown"
    assert "top products" in r.answer


def test_kpis_report_demo_source():
    k = agent.dashboard_kpis()
    assert k["is_demo"] and k["total_orders"] > 0 and k["anomaly_months"] == ["2026-07"]


@pytest.mark.parametrize("sql", [
    "DELETE FROM orders",
    "SELECT 1; DROP TABLE orders",
    "ATTACH DATABASE 'x.db' AS x",
    "PRAGMA writable_schema = 1",
    "WITH x AS (SELECT 1) INSERT INTO orders VALUES (1,1,'2026-01-01','Delivered')",
])
def test_untrusted_sql_is_read_only(sql):
    with pytest.raises(Exception):
        db.run_untrusted_select(sql)


def test_untrusted_select_works():
    df = db.run_untrusted_select("SELECT category, COUNT(*) AS n FROM products GROUP BY category")
    assert len(df) == 5
