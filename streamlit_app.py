"""
Autonomous Business Data Analyst — E-commerce demo
Run: streamlit run streamlit_app.py
"""
import streamlit as st

from app import agent, charts, db, llm_backend

st.set_page_config(
    page_title="Autonomous Business Data Analyst",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown("""
<style>
#MainMenu, footer, header {visibility: hidden;}
.block-container {padding-top: 2rem; max-width: 1100px;}

.app-title {font-size: 1.9rem; font-weight: 800; margin-bottom: 0;}
.app-subtitle {color: #52514e; font-size: 0.95rem; margin-top: 0.1rem; margin-bottom: 1.4rem;}

.kpi-card {
    background: #f9f9f7; border: 1px solid rgba(11,11,11,0.08);
    border-radius: 12px; padding: 0.9rem 1.1rem; height: 100%;
}
.kpi-label {color: #898781; font-size: 0.78rem; font-weight: 600;
            text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.25rem;}
.kpi-value {color: #0b0b0b; font-size: 1.55rem; font-weight: 800; line-height: 1.1;}
.kpi-sub {color: #52514e; font-size: 0.8rem; margin-top: 0.2rem;}

.status-pill {display:inline-flex; align-items:center; gap:0.4rem; font-size:0.85rem;
              padding: 0.3rem 0.7rem; border-radius: 999px; font-weight: 600;}
.status-on {background:#e6f6e6; color:#0ca30c;}
.status-off {background:#fdf1e0; color:#b06b00;}
.dot {width:8px; height:8px; border-radius:50%; display:inline-block;}
.dot-on {background:#0ca30c;} .dot-off {background:#fab219;}

.anomaly-banner {
    background: #fdeceb; border: 1px solid rgba(208,59,59,0.25); border-left: 4px solid #d03b3b;
    border-radius: 10px; padding: 0.8rem 1.1rem; margin-bottom: 1.2rem;
}
.anomaly-banner b {color: #d03b3b;}

.sample-q button {text-align: left !important; justify-content: flex-start !important;}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<div class="app-title">📊 Autonomous Business Data Analyst</div>', unsafe_allow_html=True)
st.markdown('<div class="app-subtitle">RAG + Agentic AI over an e-commerce dataset — ask a question below, '
            'or click a sample question in the sidebar.</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# KPI row (computed once, cached for the session)
# ---------------------------------------------------------------------------
if "kpis" not in st.session_state:
    st.session_state["kpis"] = agent.dashboard_kpis()
k = st.session_state["kpis"]

c1, c2, c3, c4 = st.columns(4)
for col, label, value, sub in [
    (c1, "Total Revenue", f"₹{k['total_revenue']:,.0f}", "Jan – Aug 2026"),
    (c2, "Total Orders", f"{k['total_orders']:,}", "Delivered / Shipped"),
    (c3, "Avg Order Value", f"₹{k['avg_order_value']:,.0f}", "Per order"),
    (c4, "Active Alerts", f"{k['active_anomalies']}", f"{k['low_stock_count']} product(s) low on stock"),
]:
    col.markdown(f"""<div class="kpi-card"><div class="kpi-label">{label}</div>
                  <div class="kpi-value">{value}</div><div class="kpi-sub">{sub}</div></div>""",
                 unsafe_allow_html=True)

st.write("")

if k["active_anomalies"]:
    months = ", ".join(k["anomaly_months"])
    bcol1, bcol2 = st.columns([5, 1])
    with bcol1:
        st.markdown(f"""<div class="anomaly-banner">⚠️ <b>Anomaly detected</b> — revenue dropped
                    sharply in <b>{months}</b>. The agent already knows why — ask it.</div>""",
                    unsafe_allow_html=True)
    with bcol2:
        if st.button("Explain this ↗", use_container_width=True):
            st.session_state["pending_question"] = "Why did sales drop in July?"

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    if llm_backend.available():
        st.markdown('<span class="status-pill status-on"><span class="dot dot-on"></span> '
                    'LLM-grounded answers</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-pill status-off"><span class="dot dot-off"></span> '
                    'Rule-based mode (offline)</span>', unsafe_allow_html=True)
        st.caption("Set ANTHROPIC_API_KEY or OPENAI_API_KEY to upgrade answer-writing to a real LLM.")

    st.divider()
    st.subheader("Try asking")

    groups = {
        "📈 Sales": ["What are the top 5 selling products?", "Show the sales trend by month", "Show revenue by category"],
        "📦 Inventory": ["Which products are low in stock?"],
        "👥 Customers": ["What is the average order value?", "Show sales by city", "Who are our top customers?"],
        "📄 Policy (RAG)": ["What is your return policy?"],
        "🤖 Agentic / Autonomous": ["Why did sales drop in July?", "Detect anomalies in sales"],
    }
    for group, qs in groups.items():
        st.markdown(f"**{group}**")
        for q in qs:
            if st.button(q, key=f"sb_{q}", use_container_width=True):
                st.session_state["pending_question"] = q
        st.write("")

    st.divider()
    with st.expander("Database schema"):
        st.code(db.SCHEMA_DESCRIPTION, language="text")

    if st.session_state.get("history"):
        if st.button("🗑️ Clear conversation", use_container_width=True):
            st.session_state["history"] = []
            st.rerun()

# ---------------------------------------------------------------------------
# Chat state
# ---------------------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state["history"] = []

pending = st.session_state.pop("pending_question", None)
typed = st.chat_input("Ask a business question…")
question = pending or typed

if question:
    with st.spinner("Agent is reasoning…"):
        resp = agent.answer(question)
    st.session_state["history"].append((question, resp))

# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------
if not st.session_state["history"]:
    st.info("No questions yet — try one from the sidebar, or type your own below.")

for q, resp in st.session_state["history"]:
    with st.chat_message("user"):
        st.markdown(q)
    with st.chat_message("assistant", avatar="📊"):
        if resp.steps:
            with st.expander(f"Agent reasoning trace ({len(resp.steps)} step(s))"):
                for step in resp.steps:
                    st.write("• " + step)
        st.markdown(resp.answer)

        if resp.table is not None and len(resp.table):
            tab_chart, tab_table = st.tabs(["Chart", "Table"]) if resp.chart else (None, None)
            if resp.chart:
                x, y = resp.chart["x"], resp.chart["y"]
                with tab_chart:
                    if resp.chart["type"] == "line":
                        fig = charts.line_chart(resp.table, x, y)
                    else:
                        fig = charts.bar_chart(resp.table, x, y,
                                                highlight_negative=(resp.intent == "why_drop"))
                    st.pyplot(fig, use_container_width=True)
                with tab_table:
                    st.dataframe(resp.table, use_container_width=True, hide_index=True)
            else:
                st.dataframe(resp.table, use_container_width=True, hide_index=True)
