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

Questions that match no known intent go to `_general()`: RAG first (is it a
policy question?), then LLM text-to-SQL when a key is configured. Model-written
SQL runs through db.run_untrusted_select(), which SQLite enforces as read-only.
"""
import calendar
import re
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
        return "general"
    return best


@dataclass
class AgentResponse:
    intent: str
    answer: str
    table: Optional[pd.DataFrame] = None
    chart: Optional[dict] = None      # {"type": "bar"/"line", "x": col, "y": col}
    steps: list = field(default_factory=list)   # trace of reasoning steps, for transparency
    sources: list = field(default_factory=list)  # RAG citations: [{"doc", "section", "score", "text"}]
    sql: Optional[str] = None                    # model-written SQL (text-to-SQL path only)


def _sources(hits) -> list:
    return [{"doc": h.doc, "section": h.section, "score": h.score, "text": h.text} for h in hits]


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
    tenant = db.current_tenant()
    revenue_df = db.run_sql("""
        SELECT ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue,
               COUNT(DISTINCT o.order_id) AS orders,
               MIN(o.order_date) AS first_date, MAX(o.order_date) AS last_date
        FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
        WHERE o.status != 'Cancelled'
    """).iloc[0]
    aov = _q_avg_order_value().iloc[0]["avg_order_value"]
    _, anomalies = detect_anomalies()
    low_stock = _q_low_stock()
    return {
        "total_revenue": float(revenue_df["revenue"] or 0),
        "total_orders": int(revenue_df["orders"] or 0),
        "avg_order_value": float(aov or 0),
        "active_anomalies": len(anomalies),
        "anomaly_months": anomalies["month"].tolist() if len(anomalies) else [],
        "low_stock_count": len(low_stock),
        "period": _period_label(revenue_df["first_date"], revenue_df["last_date"]),
        "data_source": tenant.label,
        "is_demo": tenant.is_demo,
    }


def _period_label(first, last) -> str:
    if not first or not last:
        return "No orders yet"
    f, l = pd.to_datetime(first), pd.to_datetime(last)
    return f"{f:%b %Y} – {l:%b %Y}" if (f.year, f.month) != (l.year, l.month) else f"{f:%b %Y}"


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


def _month_in_question(question: str, months: list[str]) -> Optional[str]:
    """Map 'July' / 'jul' in the question to the latest matching 'YYYY-MM' in the data."""
    q = question.lower()
    for num in range(1, 13):
        names = (calendar.month_name[num].lower(), calendar.month_abbr[num].lower())
        if any(re.search(rf"\b{n}\b", q) for n in names):
            matches = [m for m in months if m.endswith(f"-{num:02d}")]
            return matches[-1] if matches else None
    return None


NO_DATA = ("There isn't enough data for this analysis yet. Upload your orders, products, "
           "customers and order items on the **Data** page.")

HELP_TEXT = (
    "I couldn't map that question to an analysis I know. I can answer questions about "
    "**top products**, **sales trends**, **revenue by category or city**, **low stock**, "
    "**average order value**, **top customers**, **policies** (returns, shipping, COD), and I can "
    "explain **why sales dropped** or **detect anomalies**. With an LLM key configured I can also "
    "write SQL for free-form questions."
)


def answer(question: str) -> AgentResponse:
    intent = classify_intent(question)
    steps = [f"Classified intent: {intent}"]
    try:
        return _HANDLERS[intent](question, steps)
    except (IndexError, KeyError, ValueError, ZeroDivisionError):
        # Small or partial company datasets can leave a query with no rows to describe.
        steps.append("Analysis stopped: the query returned too little data.")
        return AgentResponse(intent, NO_DATA, None, None, steps)


def _simple(intent, question, steps, df, step, template_fn, chart=None):
    steps.append(step)
    if df.empty:
        return AgentResponse(intent, NO_DATA, None, None, steps)
    ans = _grounded_or_template(question, df.to_string(index=False), "", template_fn(df))
    return AgentResponse(intent, ans, df, chart, steps)


def _top_products(question, steps):
    def t(df):
        top = df.iloc[0]
        return (f"The best-selling product is **{top['name']}** ({top['category']}) with "
                f"₹{top['revenue']:,.0f} in revenue from {int(top['units_sold'])} units sold. "
                f"Top {len(df)} shown below.")
    return _simple("top_products", question, steps, _q_top_products(), "Ran top-products-by-revenue query.",
                   t, {"type": "bar", "x": "name", "y": "revenue"})


def _sales_trend(question, steps):
    def t(df):
        latest, prev = df.iloc[-1], df.iloc[-2] if len(df) > 1 else df.iloc[-1]
        delta = latest["revenue"] - prev["revenue"]
        direction = "up" if delta >= 0 else "down"
        return (f"Revenue for {latest['month']} was ₹{latest['revenue']:,.0f}, "
                f"{direction} ₹{abs(delta):,.0f} vs the previous month.")
    return _simple("sales_trend", question, steps, _q_sales_trend(), "Ran monthly revenue trend query.",
                   t, {"type": "line", "x": "month", "y": "revenue"})


def _category_revenue(question, steps):
    def t(df):
        top = df.iloc[0]
        return f"**{top['category']}** leads with ₹{top['revenue']:,.0f} in total revenue."
    return _simple("category_revenue", question, steps, _q_category_revenue(), "Ran revenue-by-category query.",
                   t, {"type": "bar", "x": "category", "y": "revenue"})


def _low_stock(question, steps):
    df = _q_low_stock()
    steps.append("Ran low-stock (<40 units) query.")
    template = (f"{len(df)} product(s) are below the 40-unit stock threshold, "
                f"led by **{df.iloc[0]['name']}** at {int(df.iloc[0]['stock_qty'])} units left."
                if len(df) else "No products are currently below the stock threshold.")
    ans = _grounded_or_template(question, df.to_string(index=False), "", template)
    chart = {"type": "bar", "x": "name", "y": "stock_qty"} if len(df) else None
    return AgentResponse("low_stock", ans, df, chart, steps)


def _avg_order_value(question, steps):
    df = _q_avg_order_value()
    if df.empty or pd.isna(df.iloc[0]["avg_order_value"]):
        df = df.iloc[0:0]
    return _simple("avg_order_value", question, steps, df, "Computed average order value.",
                   lambda d: f"The average order value (AOV) is ₹{d.iloc[0]['avg_order_value']:,.0f}.")


def _sales_by_region(question, steps):
    def t(df):
        top = df.iloc[0]
        return f"**{top['city']}** is the top-revenue city at ₹{top['revenue']:,.0f}."
    return _simple("sales_by_region", question, steps, _q_sales_by_region(), "Ran revenue-by-city query.",
                   t, {"type": "bar", "x": "city", "y": "revenue"})


def _top_customers(question, steps):
    def t(df):
        top = df.iloc[0]
        return (f"**{top['name']}** ({top['city']}) is the top customer, spending "
                f"₹{top['total_spent']:,.0f} across {int(top['orders'])} orders.")
    return _simple("top_customers", question, steps, _q_top_customers(), "Ran top-customers-by-spend query.", t)


def _policy(question, steps, hits=None):
    hits = hits if hits is not None else rag.retrieve(question, top_k=3)
    steps.append(f"RAG: retrieved {len(hits)} relevant chunk(s) from the knowledge base "
                 f"(TF-IDF + cosine similarity).")
    if not hits:
        return AgentResponse("policy", "I couldn't find anything relevant in the policy documents.",
                             None, None, steps)
    context = rag.format_context(hits)
    template = "Here is what the policy documents say:\n\n" + "\n\n".join(
        f"> {' '.join(h.text.split())}\n\n— *{h.cite()}*" for h in hits)
    steps.append("Grounded the answer in the retrieved chunks." if llm_backend.available()
                 else "Offline mode: showing the retrieved passages with citations.")
    ans = _grounded_or_template(question, "", context, template)
    return AgentResponse("policy", ans, None, None, steps, sources=_sources(hits))


def _why_drop(question, steps):
    # multi-step agentic chain: trend -> find the month to explain -> break down
    # that month by category -> check stock for the worst category -> RAG
    # for any relevant policy context -> synthesize.
    trend = _q_sales_trend()
    if len(trend) < 2:
        steps.append("Step 1: pulled monthly revenue trend — fewer than 2 months of data.")
        return AgentResponse("why_drop", NO_DATA, None, None, steps)
    trend["pct_change"] = trend["revenue"].pct_change() * 100
    steps.append("Step 1: pulled monthly revenue trend.")

    asked = _month_in_question(question, trend["month"].tolist())
    if asked and trend.index[trend["month"] == asked][0] > 0:
        target = trend.loc[trend["month"] == asked].iloc[0]
        steps.append(f"Step 2: focused on the month you asked about, {asked} "
                     f"({target['pct_change']:+.1f}% month-over-month).")
    else:
        target = trend.loc[trend["pct_change"].idxmin()]
        steps.append(f"Step 2: identified worst month-over-month drop at {target['month']} "
                     f"({target['pct_change']:.1f}%).")
    prev_row = trend.iloc[trend.index.get_loc(target.name) - 1]
    prev_month = prev_row["month"]

    cat_this = _q_category_revenue(target["month"])
    cat_prev = _q_category_revenue(prev_month)
    merged = cat_this.merge(cat_prev, on="category", suffixes=("_this", "_prev"), how="outer").fillna(0)
    merged["drop"] = merged["revenue_prev"] - merged["revenue_this"]
    worst_cat = merged.sort_values("drop", ascending=False).iloc[0]
    steps.append(f"Step 3: broke down {target['month']} vs {prev_month} by category — "
                 f"'{worst_cat['category']}' changed the most (₹{worst_cat['drop']:,.0f} lower).")

    stock = _q_low_stock(threshold=10**9)
    cat_stock = stock[stock["category"] == worst_cat["category"]]
    steps.append(f"Step 4: checked current stock levels for '{worst_cat['category']}'.")

    hits = rag.retrieve(f"{worst_cat['category']} out of stock restock shipping", top_k=2)
    context = rag.format_context(hits)
    steps.append(f"Step 5: RAG retrieved {len(hits)} policy chunk(s) for context.")

    avg_stock = cat_stock["stock_qty"].mean() if len(cat_stock) else None
    stock_note = (f"Current average stock for {worst_cat['category']} is only "
                  f"{avg_stock:.0f} units, consistent with a stock-out. " if avg_stock is not None
                  and avg_stock < 40 else "")
    policy_note = (f"Relevant policy (*{hits[0].cite()}*): {' '.join(hits[0].text.split())}"
                   if hits else "")

    if target["pct_change"] >= 0:
        template = (f"Revenue did not drop in **{target['month']}** — it rose {target['pct_change']:.1f}% "
                    f"to ₹{target['revenue']:,.0f}. Ask \"detect anomalies\" to find months that did drop.")
    else:
        template = (
            f"Revenue dropped {abs(target['pct_change']):.1f}% in **{target['month']}** "
            f"(₹{target['revenue']:,.0f}, down from ₹{prev_row['revenue']:,.0f} the prior month). "
            f"The **{worst_cat['category']}** category drove the decline, falling ₹{worst_cat['drop']:,.0f}. "
            f"{stock_note}{policy_note}"
        )
    data_summary = (f"Trend:\n{trend.to_string(index=False)}\n\nCategory breakdown "
                    f"({target['month']} vs {prev_month}):\n{merged.to_string(index=False)}\n\n"
                    f"Stock for {worst_cat['category']}:\n{cat_stock.to_string(index=False)}")
    ans = _grounded_or_template(question, data_summary, context, template)
    return AgentResponse("why_drop", ans, merged, {"type": "bar", "x": "category", "y": "drop"}, steps,
                         sources=_sources(hits))


def _anomaly(question, steps):
    trend, anomalies = detect_anomalies()
    steps.append(f"Scanned monthly trend for >10% MoM drops; found {len(anomalies)}.")
    if trend.empty:
        return AgentResponse("anomaly", NO_DATA, None, None, steps)
    if len(anomalies):
        rows = "; ".join(f"{r['month']} ({r['pct_change']:.1f}%)" for _, r in anomalies.iterrows())
        template = (f"Detected {len(anomalies)} anomalous month(s): {rows}. "
                    f"Ask \"why did sales drop\" for a root-cause breakdown.")
    else:
        template = "No significant month-over-month revenue anomalies detected."
    ans = _grounded_or_template(question, trend.to_string(index=False), "", template)
    return AgentResponse("anomaly", ans, trend, {"type": "line", "x": "month", "y": "revenue"}, steps)


def _general(question, steps):
    """No intent matched: try the knowledge base, then LLM text-to-SQL, then explain what's supported."""
    hits = rag.retrieve(question, top_k=3)
    if hits and hits[0].score >= 0.15:
        steps.append(f"Knowledge base match (score {hits[0].score:.2f}) — answering from documents.")
        return _policy(question, steps, hits)

    if not llm_backend.available():
        steps.append("No knowledge-base match and no LLM configured for free-form SQL.")
        return AgentResponse("unknown", HELP_TEXT, None, None, steps)

    steps.append("Text-to-SQL: asked the LLM to write a query for this question.")
    try:
        sql = llm_backend.generate_sql(question, db.SCHEMA_DESCRIPTION)
        df = db.run_untrusted_select(sql)
    except Exception as e:
        steps.append(f"Generated SQL was rejected or failed: {e}")
        return AgentResponse("unknown", HELP_TEXT, None, None, steps)
    steps.append(f"Ran read-only SQL, got {len(df)} row(s).")
    if df.empty:
        return AgentResponse("text_to_sql", "The query ran but returned no rows.", None, None, steps, sql=sql)

    chart = None
    if df.shape[1] == 2 and pd.api.types.is_numeric_dtype(df.iloc[:, 1]) and len(df) > 1:
        x = str(df.columns[0])
        chart = {"type": "line" if any(k in x.lower() for k in ("month", "date")) else "bar",
                 "x": x, "y": str(df.columns[1])}
    ans = _grounded_or_template(question, df.head(50).to_string(index=False), "",
                                f"Here are the results ({len(df)} row(s)).")
    return AgentResponse("text_to_sql", ans, df, chart, steps, sql=sql)


_HANDLERS = {
    "top_products": _top_products,
    "sales_trend": _sales_trend,
    "category_revenue": _category_revenue,
    "low_stock": _low_stock,
    "avg_order_value": _avg_order_value,
    "sales_by_region": _sales_by_region,
    "top_customers": _top_customers,
    "policy": _policy,
    "why_drop": _why_drop,
    "anomaly": _anomaly,
    "general": _general,
}
