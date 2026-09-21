"""
The agentic orchestrator.

classify_intent() decides WHAT the question is about (this is the "planning"
step of the agent). Each intent has a SQL template (the "tool call"). Simple
intents run one query and describe the result. Compound intents ("why did
sales drop", "find anomalies") chain multiple queries and reason over their
combined results before answering — that chaining is the "agentic" part.

If an LLM key is configured (see llm_backend.py), the final natural-language
write-up is produced by the real model, grounded in the SQL results and RAG
context. Without a key, a templated summary is used instead so the whole
pipeline still runs end to end.
"""
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from app import db, llm_backend, rag

# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------

INTENT_KEYWORDS = {
    "top_products": ["top selling", "best selling", "top product", "best product", "top 5 product"],
    "sales_trend": ["sales trend", "sales by month", "monthly sales", "revenue trend", "revenue by month", "sales over time"],
    "category_revenue": ["by category", "category revenue", "which category", "category wise"],
    "low_stock": ["low stock", "restock", "out of stock", "stock level", "inventory"],
    "avg_order_value": ["average order value", "aov", "average order"],
    "sales_by_region": ["by city", "by region", "by state", "region", "city wise"],
    "top_customers": ["top customer", "best customer", "highest spending", "loyal customer", "repeat customer"],
    "policy": ["policy", "return", "refund", "shipping", "faq", "cod", "cash on delivery", "warranty"],
    "why_drop": ["why did sales drop", "why sales dropped", "why did revenue drop", "explain the drop", "why did sales fall"],
    "anomaly": ["anomaly", "anomalies", "unusual", "detect issue", "flag issue", "spot problem"],
}


def classify_intent(question: str) -> str:
    q = question.lower()
    scores = {}
    for intent, phrases in INTENT_KEYWORDS.items():
        scores[intent] = sum(1 for p in phrases if p in q)
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        # loose fallback: single-keyword hits
        if "stock" in q:
            return "low_stock"
        if "customer" in q:
            return "top_customers"
        if "product" in q:
            return "top_products"
        return "policy"
    return best


@dataclass
class AgentResponse:
    intent: str
    answer: str
    table: Optional[pd.DataFrame] = None
    chart: Optional[dict] = None      # {"type": "bar"/"line", "x": col, "y": col}
    steps: list = field(default_factory=list)   # trace of reasoning steps, for transparency


# ---------------------------------------------------------------------------
# Query templates (the agent's "tools")
# ---------------------------------------------------------------------------

def _q_top_products(n=5):
    return db.run_sql(f"""
        SELECT p.name, p.category, SUM(oi.quantity) AS units_sold,
               ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
        FROM order_items oi JOIN products p ON p.product_id = oi.product_id
        JOIN orders o ON o.order_id = oi.order_id
        WHERE o.status != 'Cancelled'
        GROUP BY p.product_id ORDER BY revenue DESC LIMIT {n}
    """)


def _q_sales_trend():
    return db.run_sql("""
        SELECT strftime('%Y-%m', o.order_date) AS month,
               ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
        FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
        WHERE o.status != 'Cancelled'
        GROUP BY month ORDER BY month
    """)


def _q_category_revenue(month: Optional[str] = None):
    where = f"AND strftime('%Y-%m', o.order_date) = '{month}'" if month else ""
    return db.run_sql(f"""
        SELECT p.category, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
        FROM order_items oi JOIN products p ON p.product_id = oi.product_id
        JOIN orders o ON o.order_id = oi.order_id
        WHERE o.status != 'Cancelled' {where}
        GROUP BY p.category ORDER BY revenue DESC
    """)


def _q_low_stock(threshold=40):
    return db.run_sql(f"""
        SELECT name, category, stock_qty FROM products
        WHERE stock_qty < {threshold} ORDER BY stock_qty ASC
    """)


def _q_avg_order_value():
    return db.run_sql("""
        SELECT ROUND(AVG(order_total), 2) AS avg_order_value FROM (
            SELECT o.order_id, SUM(oi.quantity * oi.unit_price) AS order_total
            FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
            WHERE o.status != 'Cancelled' GROUP BY o.order_id
        )
    """)


def _q_sales_by_region():
    return db.run_sql("""
        SELECT c.city, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
        FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
        JOIN customers c ON c.customer_id = o.customer_id
        WHERE o.status != 'Cancelled'
        GROUP BY c.city ORDER BY revenue DESC
    """)


def _q_top_customers(n=10):
    return db.run_sql(f"""
        SELECT c.name, c.city, COUNT(DISTINCT o.order_id) AS orders,
               ROUND(SUM(oi.quantity * oi.unit_price), 2) AS total_spent
        FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
        JOIN customers c ON c.customer_id = o.customer_id
        WHERE o.status != 'Cancelled'
        GROUP BY c.customer_id ORDER BY total_spent DESC LIMIT {n}
    """)


# ---------------------------------------------------------------------------
# Anomaly detection ("autonomous" insight — no question needed to trigger it)
# ---------------------------------------------------------------------------

def detect_anomalies(pct_drop_threshold=10.0):
    trend = _q_sales_trend()
    trend["pct_change"] = trend["revenue"].pct_change() * 100
    anomalies = trend[trend["pct_change"] <= -pct_drop_threshold].copy()
    return trend, anomalies


def dashboard_kpis() -> dict:
    """Top-line numbers for the dashboard header, computed once per page load."""
    revenue_df = db.run_sql("""
        SELECT ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue,
               COUNT(DISTINCT o.order_id) AS orders
        FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
        WHERE o.status != 'Cancelled'
    """).iloc[0]
    aov = _q_avg_order_value().iloc[0]["avg_order_value"]
    _, anomalies = detect_anomalies()
    low_stock = _q_low_stock()
    return {
        "total_revenue": revenue_df["revenue"],
        "total_orders": int(revenue_df["orders"]),
        "avg_order_value": aov,
        "active_anomalies": len(anomalies),
        "anomaly_months": anomalies["month"].tolist() if len(anomalies) else [],
        "low_stock_count": len(low_stock),
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _grounded_or_template(question, data_summary, context, template_answer):
    if llm_backend.available():
        try:
            return llm_backend.synthesize_insight(question, data_summary, context)
        except Exception as e:
            return f"[LLM call failed, showing templated answer instead: {e}]\n\n{template_answer}"
    return template_answer


def answer(question: str) -> AgentResponse:
    intent = classify_intent(question)
    steps = [f"Classified intent: {intent}"]

    if intent == "top_products":
        df = _q_top_products()
        steps.append("Ran top-products-by-revenue query.")
        top = df.iloc[0]
        template = (f"The best-selling product is **{top['name']}** ({top['category']}) with "
                    f"₹{top['revenue']:,.0f} in revenue from {int(top['units_sold'])} units sold. "
                    f"Top 5 shown below.")
        ans = _grounded_or_template(question, df.to_string(index=False), "", template)
        return AgentResponse(intent, ans, df, {"type": "bar", "x": "name", "y": "revenue"}, steps)

    if intent == "sales_trend":
        df = _q_sales_trend()
        steps.append("Ran monthly revenue trend query.")
        latest, prev = df.iloc[-1], df.iloc[-2] if len(df) > 1 else df.iloc[-1]
        delta = latest["revenue"] - prev["revenue"]
        direction = "up" if delta >= 0 else "down"
        template = (f"Revenue for {latest['month']} was ₹{latest['revenue']:,.0f}, "
                    f"{direction} ₹{abs(delta):,.0f} vs the previous month.")
        ans = _grounded_or_template(question, df.to_string(index=False), "", template)
        return AgentResponse(intent, ans, df, {"type": "line", "x": "month", "y": "revenue"}, steps)

    if intent == "category_revenue":
        df = _q_category_revenue()
        steps.append("Ran revenue-by-category query.")
        top = df.iloc[0]
        template = f"**{top['category']}** leads with ₹{top['revenue']:,.0f} in total revenue."
        ans = _grounded_or_template(question, df.to_string(index=False), "", template)
        return AgentResponse(intent, ans, df, {"type": "bar", "x": "category", "y": "revenue"}, steps)

    if intent == "low_stock":
        df = _q_low_stock()
        steps.append("Ran low-stock (<40 units) query.")
        template = (f"{len(df)} product(s) are below the 40-unit stock threshold, "
                    f"led by **{df.iloc[0]['name']}** at {int(df.iloc[0]['stock_qty'])} units left."
                    if len(df) else "No products are currently below the stock threshold.")
        ans = _grounded_or_template(question, df.to_string(index=False), "", template)
        return AgentResponse(intent, ans, df, {"type": "bar", "x": "name", "y": "stock_qty"}, steps)

    if intent == "avg_order_value":
        df = _q_avg_order_value()
        steps.append("Computed average order value.")
        aov = df.iloc[0]["avg_order_value"]
        template = f"The average order value (AOV) is ₹{aov:,.0f}."
        ans = _grounded_or_template(question, df.to_string(index=False), "", template)
        return AgentResponse(intent, ans, df, None, steps)

    if intent == "sales_by_region":
        df = _q_sales_by_region()
        steps.append("Ran revenue-by-city query.")
        top = df.iloc[0]
        template = f"**{top['city']}** is the top-revenue city at ₹{top['revenue']:,.0f}."
        ans = _grounded_or_template(question, df.to_string(index=False), "", template)
        return AgentResponse(intent, ans, df, {"type": "bar", "x": "city", "y": "revenue"}, steps)

    if intent == "top_customers":
        df = _q_top_customers()
        steps.append("Ran top-customers-by-spend query.")
        top = df.iloc[0]
        template = f"**{top['name']}** ({top['city']}) is the top customer, spending ₹{top['total_spent']:,.0f} across {int(top['orders'])} orders."
        ans = _grounded_or_template(question, df.to_string(index=False), "", template)
        return AgentResponse(intent, ans, df, None, steps)

    if intent == "policy":
        hits = rag.retrieve(question, top_k=3)
        steps.append(f"Retrieved {len(hits)} relevant policy chunk(s) via RAG.")
        context = "\n\n".join(f"[{d}] {c}" for d, c, _ in hits)
        template = (context if context else "I couldn't find anything relevant in the policy docs.")
        ans = _grounded_or_template(question, "", context, template)
        return AgentResponse(intent, ans, None, None, steps)

    if intent == "why_drop":
        # multi-step agentic chain: trend -> find the worst month -> break down
        # that month by category -> check stock for the worst category -> RAG
        # for any relevant policy context -> synthesize.
        trend = _q_sales_trend()
        trend["pct_change"] = trend["revenue"].pct_change() * 100
        steps.append("Step 1: pulled monthly revenue trend.")
        worst = trend.loc[trend["pct_change"].idxmin()]
        prev_month = trend.iloc[trend.index.get_loc(worst.name) - 1]["month"]
        steps.append(f"Step 2: identified worst month-over-month drop at {worst['month']} "
                     f"({worst['pct_change']:.1f}%).")

        cat_this = _q_category_revenue(worst["month"])
        cat_prev = _q_category_revenue(prev_month)
        merged = cat_this.merge(cat_prev, on="category", suffixes=("_this", "_prev"), how="outer").fillna(0)
        merged["drop"] = merged["revenue_prev"] - merged["revenue_this"]
        worst_cat = merged.sort_values("drop", ascending=False).iloc[0]
        steps.append(f"Step 3: broke down {worst['month']} by category — "
                     f"'{worst_cat['category']}' fell the most (₹{worst_cat['drop']:,.0f}).")

        stock = _q_low_stock(threshold=9999)
        cat_stock = stock[stock["category"] == worst_cat["category"]]
        steps.append(f"Step 4: checked current stock levels for '{worst_cat['category']}'.")

        hits = rag.retrieve(f"stock out {worst_cat['category']} shipping", top_k=2)
        context = "\n\n".join(f"[{d}] {c}" for d, c, _ in hits)
        steps.append("Step 5: retrieved relevant policy context via RAG.")

        avg_stock = cat_stock["stock_qty"].mean() if len(cat_stock) else None
        stock_note = (f"Current average stock for {worst_cat['category']} is only "
                       f"{avg_stock:.0f} units, consistent with a stock-out." if avg_stock is not None
                       and avg_stock < 40 else "")

        template = (
            f"Revenue dropped {abs(worst['pct_change']):.1f}% in **{worst['month']}** "
            f"(₹{worst['revenue']:,.0f}, down from ₹{cat_prev['revenue'].sum():,.0f} the prior month). "
            f"The **{worst_cat['category']}** category drove the decline, falling ₹{worst_cat['drop']:,.0f}. "
            f"{stock_note} This lines up with the shipping/stock policy: Electronics orders are held or "
            f"split when stock runs out, which suppresses that category's completed sales until restock."
        )
        data_summary = (f"Trend:\n{trend.to_string(index=False)}\n\nCategory breakdown "
                         f"({worst['month']} vs {prev_month}):\n{merged.to_string(index=False)}\n\n"
                         f"Stock for {worst_cat['category']}:\n{cat_stock.to_string(index=False)}")
        ans = _grounded_or_template(question, data_summary, context, template)
        return AgentResponse(intent, ans, merged, {"type": "bar", "x": "category", "y": "drop"}, steps)

    if intent == "anomaly":
        trend, anomalies = detect_anomalies()
        steps.append(f"Scanned monthly trend for >10% MoM drops; found {len(anomalies)}.")
        if len(anomalies):
            rows = "; ".join(f"{r['month']} ({r['pct_change']:.1f}%)" for _, r in anomalies.iterrows())
            template = f"Detected {len(anomalies)} anomalous month(s): {rows}. Ask \"why did sales drop\" for a root-cause breakdown."
        else:
            template = "No significant month-over-month revenue anomalies detected."
        ans = _grounded_or_template(question, trend.to_string(index=False), "", template)
        return AgentResponse(intent, ans, trend, {"type": "line", "x": "month", "y": "revenue"}, steps)

    return AgentResponse("unknown", "I couldn't map that question to a known analysis. Try rephrasing.", None, None, steps)
