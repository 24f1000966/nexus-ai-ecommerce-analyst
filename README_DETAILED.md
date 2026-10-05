# Nexus AI — Autonomous Business Data Analyst for E-commerce

**A multi-tenant SaaS platform where e-commerce companies register, get verified, upload their order/product/customer data, and then use an agentic AI analyst to answer business questions over that data using SQL tools and RAG (Retrieval-Augmented Generation).**

> **Project Stage:** MVP (production-ready, 31 tests pass, all Phase 3 features complete)  
> **Latest Commit:** Multi-tenant isolation + per-company data upload + tenant-scoped RAG + LLM text-to-SQL + knowledge bases

---

## How It Works

### 1. Registration Flow
1. **Company registers** on `/register` (3 steps):
   - Company details + MD info + data types
   - Logo PNG/JPG/WebP + authorization letter PDF
   - Admin account creation

2. **Super Admin reviews** on `/admin`:
   - Automated sanity checks: GSTIN/PAN/CIN format, PAN embedded in GSTIN, corporate email, domain match
   - Download letter, approve/reject/suspend

3. **Company admin gets access** once approved:
   - Dashboard shows demo dataset (10k demo orders)
   - Can upload their own 4 CSVs (customers, products, orders, order_items)
   - Can invite team members (viewers with read-only dashboard access)
   - Can add policy/FAQ documents to the knowledge base

### 2. Analyst Experience

**Ask a question → Multi-step agentic reasoning → Answer + Data + Chart + Citations**

```
User: "Why did sales drop in February?"
  ↓
Agent classifies intent → "why_drop"
  ↓
Step 1: Pulls monthly revenue trend
Step 2: Identifies Feb as the worst month (-53.7% MoM)
Step 3: Breaks down by category → Beauty drove the decline
Step 4: Checks current stock → Only 5 Beauty items in stock
Step 5: RAG retrieves policy: "Beauty supplier often delayed 3-4 weeks"
  ↓
Answer: "Revenue dropped 53.7% in Feb (₹642k, down from ₹1.4M in Jan).
The Beauty category fell the most (₹350k loss). Current stock is critically
low — the supplier was delayed. See policy [Beauty Products › Supply]."
  ↓
Shows table + bar chart + 3 RAG citations with scores
```

---

## System Architecture

### Data Model

**Two-database setup:**
- **Platform DB** (`platform.db` local / Postgres in production): Users, Companies, Audit logs, Uploaded CSVs, Knowledge documents
- **Analytics DB** (SQLite, per-company, in-memory): Tenant's isolated data; loaded from uploaded CSVs

```
Platform (multi-tenant)
├── Companies (registration, status, logos, letters)
├── Users (super_admin, company_admin, member)
├── Audit logs
├── CSV Datasets (one row per upload)
└── Knowledge Docs (company's own FAQs/policies)

Analytics (tenant-scoped)
├── Tenant A → customers, products, orders, order_items
└── Tenant B → customers, products, orders, order_items
```

### Agent Architecture

```
                         Question
                            ↓
        ╔════════════════════════════════════════╗
        ║   Intent Classification (Keywords)     ║
        ║   Maps to one of 11 intents            ║
        ╚════════════════════════════════════════╝
                            ↓
        ┌─────────────────────────────────────────┐
        │ Intent-Specific Handler                 │
        │                                         │
        │ Simple (5 intents):                     │
        │   top_products → SQL → Template         │
        │   sales_trend → SQL → Template          │
        │   etc.                                  │
        │                                         │
        │ Compound (2 intents):                   │
        │   why_drop → 5-step chain               │
        │   anomaly → trend analysis              │
        │                                         │
        │ RAG (1 intent):                         │
        │   policy → retrieve (TF-IDF)            │
        │                                         │
        │ Fallback (1 intent):                    │
        │   general → RAG + LLM text-to-SQL       │
        │            or just explain capabilities│
        └─────────────────────────────────────────┘
                            ↓
        ╔════════════════════════════════════════╗
        ║   SQL Execution (Read-Only Enforced)   ║
        ║   → Data → Pandas DataFrame            ║
        ╚════════════════════════════════════════╝
                            ↓
        ╔════════════════════════════════════════╗
        ║   LLM or Template Answer Synthesis     ║
        ║   - Grounded in SQL results             ║
        ║   - Cited policy context (RAG)          ║
        ║   - Falls back to rule-based if no LLM  ║
        ╚════════════════════════════════════════╝
```

### RAG Pipeline

**Goal:** Ground policy questions in company's own docs + platform defaults.

```
Ingest
  Platform docs: data/docs/{faq,return_policy,shipping_policy}.md
  + Company docs: uploaded .md / .txt files

Chunk (on-demand)
  Split each doc on headings (##, ###, etc.)
  Then on paragraphs
  Each chunk = (doc_name, section_title, paragraph_text)

Index (TF-IDF + cosine)
  Tokenize → remove stopwords → stem (return, returning, returns → return)
  Compute term frequency (sublinear) × inverse document frequency
  Normalize vectors (L2)
  Per-tenant cache (invalidate on doc upload)

Retrieve
  Question → same tokenization/stem
  Cosine similarity with all chunks
  Score ≥ 0.08 → return top-3 with scores

Generate
  Agent passes chunks to LLM as context
  LLM grounds answer in retrieved text + SQL results
  Offline: agent shows chunk text with citations
```

**Why TF-IDF, not embeddings?**
- Zero dependencies: demo runs offline, no API key
- Fast: chunks indexed once, reused across questions
- Swappable: replace internals with pgvector / Chroma without changing agent interface

---

## Intents & Examples

| Intent | Question | Output |
|--------|----------|--------|
| **top_products** | "What are the top 5 selling products?" | Bar chart; template answer |
| **sales_trend** | "Show the sales trend by month" | Line chart; month-over-month delta |
| **category_revenue** | "Revenue by category" | Bar chart; top category |
| **low_stock** | "Which products are low in stock?" | Bar chart; count + worst SKU |
| **avg_order_value** | "What is AOV?" | Template; single value |
| **sales_by_region** | "Show sales by city" | Bar chart; top city |
| **top_customers** | "Who are the top customers?" | (table only; rule-based) |
| **policy** | "What is your return policy?" | RAG retrieval; template or LLM groundedanswer |
| **why_drop** | "Why did sales drop in July?" | 5-step chain: trend → month → category → stock → RAG → synthesis |
| **anomaly** | "Detect anomalies in sales" | Scan for >10% MoM drops; flag each |
| **general** | "Tell me about blue products" | RAG fallback → LLM text-to-SQL (if key) → capabilities message |

---

## Multi-Tenant Data Isolation

### How It Works
1. **Context variable** (`_current: ContextVar[Tenant]`) holds the active tenant
2. Every `db.run_sql(query)` runs in the current tenant's SQLite connection
3. Set with `use_tenant(tenant)` context manager
4. API endpoint:
   ```python
   @app.post("/api/ask")
   def ask(req: AskRequest, user: User = Depends(require_approved_user), db: Session = Depends(get_db)):
       with use_tenant(tenant_for(db, user.company_id)):
           resp = agent.answer(req.question)
       return {**resp, "data_source": tenant.label}
   ```

### Tenant Lifecycle
- **Demo tenant** (default): Ships with 10k synthetic orders, pre-indexed for demo
- **Company tenant** (on CSV upload):
  - Validate + normalize 4 CSVs (check required columns, data types, cross-table refs)
  - Insert into platform.db as `CompanyDataset` rows (CSV stored as bytes)
  - Load frames → build in-memory SQLite DB
  - Wrap in `Tenant` object
  - Cache by version hash (invalidate on re-upload or doc change)
  - Company sees its data in the analyst; other companies cannot

---

## Knowledge Base (RAG)

### Ingest
- **Platform docs** (always available):
  - `data/docs/faq.md` — order tracking, cancellations, loyalty, restocking
  - `data/docs/return_policy.md` — 15-day window, Electronics exchange-only, final-sale items
  - `data/docs/shipping_policy.md` — 4-6 days free over ₹999, Express 1-2 days, COD limits

- **Company docs** (uploaded on Data page):
  - TrendVista adds `trendvista_policies.md` — Festive exchange window, Beauty supplier delays, own delivery SLA
  - UrbanKart uploads separate doc — its own COD terms, same default policies

### Retrieval
For "What is the festive exchange policy?":
1. Query tokenized → ["festiv", "exchang", "polici"] (stopwords removed, stemmed)
2. All chunks scored:
   - TrendVista's "Festive Exchange Window" → score 0.52 (exact match)
   - Shipping policy "Exchange for damaged items" → score 0.28 (partial)
   - FAQ "Loyalty → early exchange access" → score 0.15 (tangential)
3. Return top-3 if score ≥ 0.08
4. Chat shows citations: `[1] trendvista_policies › Festive Exchange Window (score 0.52)`

### Agent Integration
- `policy` intent: Retrieve + template or LLM answer
- `why_drop`: Retrieve 2 chunks on relevant category/issue for context
- `general` (LLM path): Retrieve first, check score; if high enough, answer from RAG only; else generate SQL

---

## Text-to-SQL (LLM Path)

When an LLM key (Claude / OpenAI) is configured:

```python
def generate_sql(question: str, schema: str) -> str:
    prompt = f"Schema:\n{schema}\n\nQuestion: {question}\n\nSQL:"
    sql = llm.generate(prompt)
    return sql  # extracted from ```sql ``` fence

def ask(question: str):
    # ... try registered intents first ...
    if no_match:
        sql = generate_sql(question, SCHEMA_DESCRIPTION)
        df = run_untrusted_select(sql)  # Read-only enforced by SQLite
        # LLM synthesizes insight from df + RAG context
```

**Safety:** SQL runs in SQLite's read-only mode; every DML/DDL/pragma is rejected.

---

## Key Files

```
nexus-ai-ecommerce-analyst/
├── app/
│   ├── agent.py             # 11 intent handlers, multi-step chains
│   ├── rag.py               # TF-IDF index, chunk_document, retrieve
│   ├── db.py                # Tenant context vars, SQL safety guards
│   ├── llm_backend.py       # Claude/OpenAI routing, SQL generation
│   └── charts.py            # Chart type + axis selection
├── backend/
│   ├── main.py              # FastAPI app, routes, health checks
│   ├── models.py            # SQLAlchemy: Company, User, Dataset, KnowledgeDoc
│   ├── security.py          # JWT, password hashing (scrypt), role checks
│   ├── verification.py      # GSTIN/PAN/CIN validation regex
│   ├── tenant_data.py       # CSV validation, tenant caching, per-company DB loading
│   ├── routers/
│   │   ├── auth.py          # register, login, /me
│   │   ├── admin.py         # review companies, approve/reject/suspend
│   │   ├── company.py       # team member CRUD
│   │   └── data.py          # CSV upload, template download, doc mgmt
│   ├── database.py          # SQLAlchemy engine, session factory
│   └── config.py            # Env vars, is_production checks
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── AnalystPage.jsx   # Chat, KPIs, sidebar with samples
│   │   │   ├── AdminPage.jsx     # Verification checks, decide action
│   │   │   ├── DataPage.jsx      # 4-table upload progress, doc mgmt
│   │   │   ├── TeamPage.jsx      # Member CRUD, password gen
│   │   │   ├── RegisterPage.jsx  # 3-step company registration
│   │   │   └── LoginPage.jsx
│   │   ├── components/
│   │   │   ├── ChatMessage.jsx   # User bubble, assistant bubble (answer + trace + sources + SQL + table/chart)
│   │   │   ├── Markdown.jsx      # **bold**, *italic*, >, - , ¶
│   │   │   ├── AppShell.jsx      # Nav, company logo, logout
│   │   │   ├── Sidebar.jsx       # Sample questions, schema, clear
│   │   │   └── ...
│   │   ├── auth/AuthContext.jsx  # Session + role-based home routing
│   │   ├── api.js               # Axios client, token storage, error handling
│   │   └── App.jsx              # Routes, guards
│   ├── package.json
│   └── vite.config.js
├── tests/
│   ├── conftest.py              # Pytest setup: scratch DB isolation
│   ├── test_rag.py              # RAG chunking, retrieval, tenant docs
│   ├── test_agent.py            # Intent classification, why_drop chain, read-only SQL
│   └── test_api.py              # E2E: register, approve, upload, isolation, knowledge base
├── data/
│   ├── ecommerce.db             # Demo 10k orders (planted July anomaly)
│   ├── docs/                    # Platform default FAQs, policies
│   └── generate_data.py         # Synth data gen script
├── trial-data/
│   ├── sample-company-data/     # TrendVista CSVs (1.7k orders, Feb Beauty supply demo)
│   ├── logo-*.png
│   └── authorization-letter-sample.pdf
├── render.yaml                  # Render Blueprint (API + React + Postgres)
├── requirements.txt             # Production deps
├── requirements-server.txt      # Lean API deps (no Streamlit)
└── README.md                    # Quick start & architecture overview
```

---

## Workflows

### 1. Company Registration → Analyst Access
```
User registers on /register
  ↓
Super Admin reviews verification checks on /admin
  ↓
Super Admin clicks Approve
  ↓
Company Admin can now log in
  ↓
Dashboard shows demo dataset (10k orders)
  ↓
(Optional) Upload 4 CSVs on /data page
  ↓
Analyst switches to company data
```

### 2. CSV Upload
```
Admin on /data page
  ↓
Click "Upload CSV" for customers table
  ↓
Select customers.csv (180 rows)
  ↓
API validates: required columns, data types, PKs unique, no orphans
  ↓
Stores in platform.db as BLOB
  ↓
Loads into in-memory SQLite tenant DB
  ↓
Cache invalidated → next question uses new data
  ↓
Chat shows "Your uploaded data" badge
```

### 3. Policy Question → RAG Answer
```
User asks "What is the festive exchange policy?"
  ↓
Agent classifies → policy intent
  ↓
RAG retrieves top-3 chunks (platform defaults + TrendVista docs)
  ↓
If LLM key set: LLM synthesizes grounded answer
  Else: Agent shows chunk text with citations
  ↓
Chat bubble shows answer + [1] citation with doc › section › score
```

### 4. Why-Drop Root Cause (Agentic Chain)
```
User asks "Why did sales drop in February?"
  ↓
Agent classifies → why_drop intent
  ↓
Step 1: SELECT SUM(revenue) by month → identified Feb as -53.7% MoM
Step 2: (user asked Feb) → focus on that month
Step 3: SELECT revenue by category for Feb vs Jan
        → Beauty fell ₹350k (worst category)
Step 4: SELECT stock_qty for Beauty products
        → only 5 items in stock
Step 5: RAG retrieve("Beauty out of stock supply")
        → "Supplier often delayed 3-4 weeks"
  ↓
Synthesize: "Revenue dropped 53.7% in Feb. Beauty category fell the most
due to low stock (5 units). The supplier was delayed."
  ↓
Show table (category breakdown) + bar chart (category drops) + 2 RAG sources
```

---

## Security

- **Passwords:** scrypt (2^14 rounds) with per-user salt
- **Sessions:** Signed JWT, 12-hour expiry, HS256
- **SQL:** Read-only enforcement via SQLite authorizer
- **Uploads:** Extension + size (5 MB) + magic-byte checks; SVG refused (XSS risk)
- **Isolation:** Every endpoint checks both role AND company approval
- **Logos:** Signed HMAC URLs (prevent enumeration)

**Not yet (Phase 4):** Login rate-limiting, email verification, password reset (consider Supabase Auth for these)

---

## Roadmap

- **Phase 3 (done):** Company data upload + tenant scoping + per-company RAG ✅
- **Phase 4 (next):** Auto-refresh CSV on schedule, email alerts on anomalies, export reports as PDF
- **Phase 5:** Forecasting (time-series), per-role views (Marketing only sees marketing KPIs), LLM-based anomaly detection

---

## Running Locally

```bash
# Install deps
pip install -r requirements.txt
cd frontend && npm install

# Seed demo data
python data/generate_data.py

# Start backend (terminal 1)
uvicorn backend.main:api --reload --port 8000

# Start frontend (terminal 2)
cd frontend && npm run dev  # → http://localhost:5173

# Run tests (terminal 3)
pytest -v
```

Super admin login: `superadmin@nexusai.in` / `Nexus@12345` (dev default)

---

## Deployment (Render Free Tier)

1. `render.yaml` creates API + React site + Postgres DB
2. Set `NEXUS_ADMIN_PASSWORD` (10+ chars) at creation time
3. Render hands out `DATABASE_URL` → auto-mapped to Postgres driver
4. Logos/letters stored in DB → survive ephemeral disks
5. **Note:** Free Postgres expires after 30 days; upgrade or point at Neon/Supabase

---

## Performance Notes

- RAG index cached per tenant; rebuilt only on doc upload (~100ms for 10k words)
- In-memory SQLite (1.7k orders) → queries <10ms
- API calls → 200–500ms total (TF-IDF + SQL + LLM synthesis)
- Frontend chat re-renders only on new messages (React 19 strict mode)

---

## Q&A

**Q: Can Company A see Company B's data?**  
A: No. Context var + tenant routing ensures queries run only on the active user's tenant.

**Q: What if I don't upload all 4 CSVs?**  
A: Analyst stays on demo data until all four tables are present. You can upload/replace any table anytime.

**Q: Can I add my own SQL?**  
A: If an LLM key is configured, free-form questions trigger text-to-SQL. SQL runs read-only; no data changes possible.

**Q: How do the RAG citations work?**  
A: Retrieved chunks are shown in the chat as `[1] doc_name › section (score 0.45)`. Click to expand and see the full text.

**Q: Is this HIPAA/GDPR compliant?**  
A: Not yet. Production deployments should add encryption at rest, audit logging (done), and IP allowlisting.

---

**Built for PPD II (Major Project).** See `tests/` for 31 passing integration + unit tests.
