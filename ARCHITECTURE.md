# Nexus AI — Architecture & Data Flows

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          NEXUS AI PLATFORM                                 │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      Frontend (React 19 + Vite)                       │  │
│  │                                                                        │  │
│  │  ┌────────────┐  ┌──────────────┐  ┌─────┐  ┌──────┐  ┌────────┐    │  │
│  │  │  Register  │→ │ Login/Status  │→ │Data │→ │Team  │  │Analyst │    │  │
│  │  │   Page     │  │   Page        │  │Page │  │Page  │  │ Page   │    │  │
│  │  └────────────┘  └──────────────┘  └─────┘  └──────┘  └────────┘    │  │
│  │                                                                        │  │
│  │  Chat UI: Ask question → show answer + trace + chart + sources       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                               ↑ / ↓ (axios)                                 │
│                          JWT auth header                                    │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      Backend (FastAPI + Uvicorn)                      │  │
│  │                                                                        │  │
│  │  POST /auth/register → Create Company + Admin user                    │  │
│  │  POST /auth/login    → Issue JWT token                               │  │
│  │                                                                        │  │
│  │  GET  /admin/companies       → List pending companies (super admin)  │  │
│  │  POST /admin/companies/{id}/approve → Mark as approved              │  │
│  │                                                                        │  │
│  │  GET  /company/data          → List uploaded tables + docs            │  │
│  │  POST /company/data/{table}  → Validate & store CSV                  │  │
│  │  GET  /company/data/{table}/template → Download template             │  │
│  │  POST /company/docs          → Upload policy markdown                │  │
│  │                                                                        │  │
│  │  GET  /kpis                  → Dashboard top-line numbers            │  │
│  │  POST /ask                   → Route to agent, return answer          │  │
│  │  GET  /schema                → Table schema (for LLM)                │  │
│  │  GET  /samples               → Question templates                    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                               ↑ / ↓                                         │
│                     Context vars (per-tenant)                               │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Agent / RAG / SQL Layer                            │  │
│  │                                                                        │  │
│  │  use_tenant(tenant) ← Company's context var                          │  │
│  │  ↓                                                                     │  │
│  │  agent.answer(question) ← Classify intent & route                    │  │
│  │  ↓                                                                     │  │
│  │  ┌─ SQL tools: _q_top_products(), _q_sales_trend(), etc.            │  │
│  │  ├─ RAG retriever: rag.retrieve(question) ← TF-IDF index            │  │
│  │  ├─ LLM backend: llm_backend.generate_sql() [if key configured]    │  │
│  │  └─ Multi-step chains: why_drop (5 steps), anomaly detection        │  │
│  │  ↓                                                                     │  │
│  │  AgentResponse { answer, steps, table, chart, sources, sql }         │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                               ↑ / ↓                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        Database Layer                                 │  │
│  │                                                                        │  │
│  │  ┌─ Platform DB (SQLAlchemy) ─────────────────────────────────────┐  │  │
│  │  │  Local: platform.db (SQLite)                                   │  │  │
│  │  │  Prod:  Postgres (DATABASE_URL)                                │  │  │
│  │  │                                                                 │  │  │
│  │  │  Tables:                                                       │  │  │
│  │  │  · companies (id, name, status, logo_data, letter_data)       │  │  │
│  │  │  · users (id, email, password_hash, company_id, role)         │  │  │
│  │  │  · company_datasets (id, company_id, table_name, csv_data)   │  │  │
│  │  │  · knowledge_docs (id, company_id, title, content)            │  │  │
│  │  │  · audit_log (id, company_id, actor, action, note)            │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                        │  │
│  │  ┌─ Analytics DB (per-tenant) ─────────────────────────────────────┐  │  │
│  │  │  Tenant 1: SQLite :memory: loaded from uploaded CSVs           │  │  │
│  │  │  ├─ customers(customer_id, name, city, state, signup_date)    │  │  │
│  │  │  ├─ products(product_id, name, category, price, stock_qty)    │  │  │
│  │  │  ├─ orders(order_id, customer_id, order_date, status)         │  │  │
│  │  │  └─ order_items(order_item_id, order_id, product_id, qty, price)│  │  │
│  │  │                                                                 │  │  │
│  │  │  Tenant 2: SQLite :memory: (same schema, different data)      │  │  │
│  │  │  Tenant (demo): Pre-built 10k order dataset                    │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Request Flow: Question → Answer

```
1. User sends question in chat
   POST /api/ask { "question": "Why did sales drop in February?" }
   Header: Authorization: Bearer <token>

2. FastAPI endpoint
   ├─ Authenticate (get current user from JWT)
   ├─ Check role (must be company_admin or member)
   ├─ Check company approval (status == "approved")
   └─ Get tenant for this user's company

3. Agent routing
   use_tenant(tenant_for(db, user.company_id)) {
       response = agent.answer(question)
   }

4. Intent classification
   classify_intent("Why did sales drop in February?")
   → Keywords ["why did sales drop"] → intent = "why_drop"

5. Multi-step chain (why_drop handler)
   Step 1: SELECT SUM(quantity * unit_price) by month FROM orders ○ order_items
           → DataFrame: [month, revenue]
   Step 2: Identify worst MoM drop (pct_change)
           → found: 2026-02 dropped 53.7%
   Step 3: SELECT revenue by category for Feb vs Jan
           → Beauty category fell ₹350k
   Step 4: SELECT stock_qty WHERE category = 'Beauty'
           → only 5 items in stock
   Step 5: RAG retrieve("Beauty out of stock supply")
           → [1] trendvista_policies › Beauty Products [score 0.78]
              "Beauty supplier from Mumbai; when delayed, items marked
               Coming soon; typical restock 3-4 weeks"

6. Answer synthesis
   Template: "Revenue dropped 53.7% in **Feb** (₹642k, down from ₹1.4M in Jan).
             The **Beauty** category drove the decline, falling ₹350k.
             Current stock is 5 units — the supplier was delayed."

   If LLM key configured:
   → Pass template + data summary + RAG context to Claude/GPT
   → Get grounded, prose answer (3–5 sentences)

7. Chart generation
   chart: { type: "bar", x: "category", y: "drop" }

8. Return to client
   {
     "intent": "why_drop",
     "answer": "Revenue dropped 53.7% in **Feb**...",
     "steps": [
       "Classified intent: why_drop",
       "Step 1: pulled monthly revenue trend.",
       "Step 2: focused on the month you asked about, 2026-02 (-53.7% MoM).",
       "Step 3: broke down 2026-02 vs 2026-01 by category — 'Beauty' changed the most (₹350k lower).",
       "Step 4: checked current stock levels for 'Beauty'.",
       "Step 5: RAG retrieved 1 policy chunk(s) for context."
     ],
     "table": [
       {"category": "Fashion", "revenue_this": 400000, "revenue_prev": 420000, "drop": 20000},
       {"category": "Beauty", "revenue_this": 50000, "revenue_prev": 400000, "drop": 350000},
       ...
     ],
     "chart": { "type": "bar", "x": "category", "y": "drop" },
     "sources": [
       {
         "doc": "trendvista_policies",
         "section": "Beauty Products",
         "score": 0.78,
         "text": "Beauty and personal-care products are non-returnable once the seal is broken. Our Beauty range is sourced from a single supplier in Mumbai; when that supplier is delayed, Beauty items are marked 'Coming soon' and cannot be ordered until restocked, which typically takes 3-4 weeks."
       }
     ],
     "data_source": "Your uploaded data",
     "sql": null
   }

9. Frontend renders
   ├─ User bubble: "Why did sales drop in February?"
   ├─ Assistant bubble:
   │  ├─ Markdown answer (bold category, month)
   │  ├─ Reasoning trace (6 steps, collapsible)
   │  ├─ RAG sources (expandable: [1] trendvista_policies › Beauty Products (0.78))
   │  ├─ Chart: bar chart by category
   │  ├─ Table tab: category breakdown
   │  └─ Data source badge: "Your uploaded data"
   └─ Input box ready for next question
```

---

## Multi-Tenant Data Isolation

### Registration & Onboarding

```
Company registers
  ↓
POST /register-company
  ├─ Validate GSTIN/PAN/CIN format
  ├─ Check email domain matches website
  ├─ Store logo & letter as BLOBs
  ├─ Create company (status = "pending")
  └─ Create company_admin user

Super Admin reviews
  ↓
GET /admin/companies/3
  ├─ Run verification_checks() → 6 checks (format, PAN match, corporate email, domain match, logo, letter)
  ├─ Show checks UI (passed/failed)
  └─ Display letter PDF, company details

Super Admin clicks Approve
  ↓
POST /admin/companies/3/approve { reason: "" }
  ├─ company.status = "approved"
  ├─ Add audit log entry
  └─ Commit

Company Admin logs in
  ↓
POST /login { email: "cfo@company.in", password: "..." }
  ├─ Verify password
  ├─ Issue JWT { sub: user_id, role: "company_admin", exp: now + 12h }
  ├─ Return token
  └─ Frontend stores in localStorage

Dashboard loaded
  ↓
GET /kpis (with JWT header)
  ├─ Authenticate (get User from JWT)
  ├─ Check role (company_admin ✓)
  ├─ Check company.status == "approved" ✓
  ├─ Load tenant_for(db, company_id=3)
  │   ├─ Query CompanyDataset rows for company 3
  │   ├─ If all 4 tables uploaded:
  │   │   ├─ Load frames from CSV data
  │   │   ├─ Build in-memory SQLite :memory:
  │   │   └─ Wrap in Tenant(key="company:3:...", label="Your uploaded data", _conn=...)
  │   └─ Else: return Tenant(key="demo", label="Demo dataset", _conn=demo.db)
  ├─ with use_tenant(tenant): get KPIs
  │   ├─ Run SQL in tenant's SQLite connection
  │   └─ Return numbers
  └─ Frontend shows "Using demo dataset" or "Using your uploaded data"
```

### Tenant Scoping in Every Query

```
@app.post("/api/ask")
def ask(req: AskRequest, user: User = Depends(require_approved_user), db: Session = Depends(get_db)):
    tenant = tenant_for(db, user.company_id)  # Load company's data or demo
    with use_tenant(tenant):                   # Set ContextVar("tenant") = tenant
        resp = agent.answer(req.question)      # All SQL runs in tenant's connection
    return { ... }


def agent.answer(question: str) -> AgentResponse:
    intent = classify_intent(question)
    # ... intent handler calls ...
    return _HANDLERS[intent](question, steps)  # Every handler uses db.run_sql()


def db.run_sql(sql: str) -> pd.DataFrame:
    with current_tenant().connection() as conn:  # Gets _current ContextVar
        return pd.read_sql_query(sql, conn)       # Runs on tenant's SQLite


# Result: Company A's SQL always runs on Company A's data (or demo)
#         Company B's SQL always runs on Company B's data (or demo)
#         Cannot query other company's data
```

### CSV Upload Flow

```
Admin on /data page → Select customers.csv (180 rows)
  ↓
POST /company/data/customers (multipart file)
  ├─ Authenticate (company_admin ✓)
  ├─ Read file: raw_bytes = await file.read()
  ├─ Validate CSV:
  │  ├─ Parse as DataFrame (UTF-8, keep_default_na=False)
  │  ├─ Lowercase column names, check required columns present
  │  ├─ Verify data types (customer_id: int, signup_date: YYYY-MM-DD)
  │  ├─ Check no duplicates on primary key (customer_id)
  │  └─ Return cleaned DataFrame
  ├─ Store in DB:
  │  ├─ Check if CompanyDataset exists for (company_id=X, table_name="customers")
  │  ├─ If exists: update csv_data, row_count, uploaded_by, uploaded_at
  │  ├─ Else: create new row
  │  └─ Commit
  ├─ Invalidate tenant cache:
  │  └─ if company_id in _cache: delete from _cache (close old in-memory DB)
  └─ Return status (complete: bool, active_source: "company" or "demo", etc.)

Next request
  ↓
GET /kpis
  ├─ tenant_for(db, company_id=3)
  │  ├─ Check if all 4 tables are uploaded
  │  ├─ If yes: load CSVs, build new :memory: SQLite, cache it
  │  ├─ If no: return demo tenant
  │  └─ Return Tenant
  └─ Analyst now queries company data (or still uses demo)
```

---

## RAG Pipeline

### Indexing (On-Demand, Per-Tenant)

```
Platform docs (loaded once at startup)
  data/docs/faq.md
  data/docs/return_policy.md
  data/docs/shipping_policy.md

Company docs (loaded from platform.db on first query)
  knowledge_docs WHERE company_id = 3
  → [
      { title: "Festive Exchange Policy", content: "# ...", uploaded_by: "...", ... }
    ]

Chunking (on demand for this tenant)
  For each doc (platform + company):
    chunk_document(doc_name, markdown) → list[Chunk]
      ├─ Split on headings (# ## ###)
      ├─ Then on blank lines
      ├─ Merge short paragraphs
      └─ Yield (doc_name, section, paragraph_text)

Indexing
  TfidfIndex(chunks)
    ├─ Tokenize each chunk (lower, remove stopwords, stem)
    ├─ Compute IDF for each term
    ├─ Build vectors (sublinear TF × IDF, L2 normalized)
    └─ Cache by hash(docs) → only rebuild when docs change

Question: "What is the festive exchange policy?"
  ↓
Retrieve
  search(question, top_k=3)
    ├─ Tokenize question
    ├─ Vectorize question
    ├─ Compute cosine similarity with all chunk vectors
    ├─ Filter by score ≥ 0.08
    ├─ Sort by score, return top-3
    └─ Result:
       [
         Hit(doc="trendvista_policies", section="Festive Exchange Window", text="...", score=0.52),
         Hit(doc="shipping_policy", section="Shipping", text="...", score=0.28),
         Hit(doc="faq", section="FAQ", text="...", score=0.15),
       ]

Generate
  If LLM key:
    llm.synthesize_insight(question, data_summary="", context=format_hits(hits))
    → LLM grounds answer in retrieved text
  Else:
    Show chunks with citations:
    "
    [1] trendvista_policies › Festive Exchange Window
    Orders placed between 1 October and 15 November can be exchanged
    until 30 November, even if the normal 10-day exchange window has passed.
    "
```

### Tenant-Scoped RAG

```
User from Company A asks a policy question
  ↓
use_tenant(tenant_for(db, company_a_id))
  ├─ Tenant docs: only knowledge_docs WHERE company_id = company_a_id
  ├─ Platform docs: shared by all companies
  └─ Index: hash(platform_docs + company_a_docs) → _cache[hash]

retrieve(question) → hits
  ├─ Search against Company A's index
  └─ Citations point to "trendvista_policies › ..." or "faq › ..."

User from Company B asks the same question
  ↓
use_tenant(tenant_for(db, company_b_id))
  ├─ Tenant docs: only knowledge_docs WHERE company_id = company_b_id
  ├─ Platform docs: same
  ├─ Index hash is different (no company_b docs)
  └─ TfidfIndex rebuilt, cached

retrieve(question) → different hits
  ├─ No "trendvista_policies" (company A's doc)
  ├─ Only platform "faq", "return_policy", "shipping_policy"
  └─ Citations do not mention Company A's policies
```

---

## Use Case Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                    Nexus AI Use Cases                            │
└──────────────────────────────────────────────────────────────────┘

Super Admin
  ├─ Register companies
  │   └─ Input: company name, MD info, GSTIN/PAN/CIN, logo, letter
  │   └─ Output: company created (status=pending)
  │
  ├─ Review applications
  │   └─ Input: GSTIN/PAN format, domain match, email, letter PDF
  │   └─ Output: approval/rejection decision
  │
  └─ Suspend companies (for fraud/non-compliance)
      └─ Output: company status=suspended, users cannot log in

Company Admin
  ├─ Upload data (CSV)
  │   └─ Input: 4 CSVs (customers, products, orders, order_items)
  │   └─ Output: analyst switches to company data
  │
  ├─ Add team members
  │   └─ Input: name, email, temporary password
  │   └─ Output: member can log in, see dashboard
  │
  ├─ Upload policies
  │   └─ Input: .md/.txt file (FAQ, return policy, etc.)
  │   └─ Output: RAG retriever includes in knowledge base
  │
  └─ Invite viewers (members)
      └─ Output: members see dashboard, cannot modify data

Company Member (Viewer)
  ├─ View KPIs
  │   └─ Output: total revenue, order count, AOV, anomalies
  │
  ├─ Ask questions
  │   ├─ "What are the top 5 selling products?"
  │   ├─ "Why did sales drop in February?"
  │   ├─ "What is your return policy?"
  │   └─ "Show revenue by category"
  │
  ├─ View answer + reasoning trace
  │   └─ Output: natural language + SQL results + chart + citations
  │
  └─ Explore sample questions (sidebar)
      └─ Click to populate and run query
```

---

## Data Flow: Query → Reasoning → Answer

```
Question: "Why did sales drop in February?"

[INTAKE]
  Authenticate ✓ | Approve check ✓ | Load tenant ✓

[INTENT CLASSIFICATION]
  why_drop ← keyword "why did sales drop"

[STEP 1: TREND]
  SELECT strftime('%Y-%m', order_date) AS month,
         SUM(quantity * unit_price) AS revenue
  FROM orders O ○ order_items OI
  WHERE O.status != 'Cancelled'
  GROUP BY month
  ORDER BY month

  Result:
  month       | revenue
  ────────────┼──────────
  2026-01     | 1,389,353
  2026-02     | 642,740   ← -53.7% MoM
  ...

[STEP 2: IDENTIFY MONTH]
  User asked "February" → found 2026-02 in result
  Identified as worst drop
  Previous month: 2026-01 (₹1,389,353)

[STEP 3: CATEGORY BREAKDOWN]
  SELECT p.category, SUM(OI.quantity * OI.unit_price) AS revenue
  FROM order_items OI ○ products P ○ orders O
  WHERE O.order_date BETWEEN '2026-02-01' AND '2026-02-28'
    AND O.status != 'Cancelled'
  GROUP BY category

  vs.

  SELECT p.category, SUM(OI.quantity * OI.unit_price) AS revenue
  FROM order_items OI ○ products P ○ orders O
  WHERE O.order_date BETWEEN '2026-01-01' AND '2026-01-31'
    AND O.status != 'Cancelled'
  GROUP BY category

  Merge & compute drop:
  category       | jan_revenue | feb_revenue | drop
  ───────────────┼─────────────┼─────────────┼──────
  Fashion        | 420,000     | 400,000     | 20,000
  Beauty         | 400,000     | 50,000      | 350,000 ← WORST
  Electronics    | 250,000     | 150,000     | 100,000
  Accessories    | 200,000     | 30,000      | 170,000
  Home Decor     | 119,353     | 12,740      | 106,613

[STEP 4: STOCK CHECK]
  SELECT product_id, name, category, stock_qty
  FROM products
  WHERE category = 'Beauty'
  ORDER BY stock_qty ASC

  Result:
  name                    | stock_qty
  ────────────────────────┼────────
  Kajal Pencil            | 3
  Vitamin C Serum         | 2
  Matte Lipstick          | 0
  Hair Oil 200ml          | 0
  
  Average: 1.25 units (critically low)

[STEP 5: RAG RETRIEVAL]
  retrieve("Beauty out of stock supply restock") → top-2

  Result:
  [1] trendvista_policies › Beauty Products [score 0.78]
      "Beauty and personal-care products are non-returnable once the seal
       is broken. Our Beauty range is sourced from a single supplier in
       Mumbai; when that supplier is delayed, Beauty items are marked
       'Coming soon' and cannot be ordered until restocked, which typically
       takes 3-4 weeks."

  [2] (no match on shipping if using platform defaults; uses company doc)

[SYNTHESIS]
  Template:
  "Revenue dropped 53.7% in **Feb** (₹642,740, down from ₹1,389,353 in Jan).
   The **Beauty** category drove the decline, falling ₹350,000.
   Current average stock for Beauty is only 1 unit, consistent with a
   stock-out. Relevant policy (trendvista_policies › Beauty Products):
   'When that supplier is delayed, Beauty items are marked Coming soon
   and cannot be ordered until restocked, which typically takes 3–4 weeks.'"

  If LLM key configured:
  → Pass to Claude/GPT with data + context
  → Refine to prose, 3–5 sentences

[RESPONSE]
  {
    "intent": "why_drop",
    "answer": "Revenue dropped 53.7% in **Feb**...",
    "steps": [ 6 trace steps ],
    "table": [ category breakdown rows ],
    "chart": { type: "bar", x: "category", y: "drop" },
    "sources": [
      { doc: "trendvista_policies", section: "Beauty Products", score: 0.78, text: "..." }
    ],
    "data_source": "Your uploaded data"
  }

[RENDERING]
  Chat bubble:
  ┌──────────────────────────────────────────┐
  │ Reasoning trace (6 steps, collapsible) ▼ │
  │                                          │
  │ Revenue dropped 53.7% in **Feb**...     │
  │                                          │
  │ [2 sources retrieved (RAG)] ▼            │
  │ └─ [1] trendvista_policies › Beauty    │
  │      (score 0.78) Beauty range sourced… │
  │                                          │
  │ [Chart] [Table]                         │
  │ ┌─────────────────────────────────────┐ │
  │ │  Beauty ████████ 350000             │ │
  │ │  Electronics ████ 100000            │ │
  │ │  Accessories ██████ 170000          │ │
  │ │  Fashion ██ 20000                   │ │
  │ │  Home Decor ██████ 106613           │ │
  │ └─────────────────────────────────────┘ │
  └──────────────────────────────────────────┘
```

---

## LLM Integration (Optional)

### When a Key Is Configured

```
Environment:
  ANTHROPIC_API_KEY=sk-ant-...
  NEXUS_ANTHROPIC_MODEL=claude-sonnet-5  (default)

Free-form question: "Tell me about our most profitable products"
  ↓
classify_intent("Tell me...") → "general" (no keywords match)
  ↓
Try RAG: retrieve("profitable products")
  └─ No high-score match
  ↓
LLM path available?
  └─ Yes, ANTHROPIC_API_KEY is set
  ↓
generate_sql(question, SCHEMA_DESCRIPTION)
  ├─ System: "You are a SQLite expert. Given a table schema and a business
             question, output ONLY the SQL query (no markdown, no explanation)"
  ├─ Prompt: "Schema: customers(...) products(...) ... \n\nQuestion: ...\n\nSQL:"
  ├─ Claude: "SELECT p.name, category, SUM(oi.quantity * oi.unit_price) AS profit
             FROM order_items oi ○ products p ○ orders o
             WHERE o.status != 'Cancelled'
             GROUP BY p.product_id
             ORDER BY profit DESC LIMIT 5"
  └─ Extract from fenced ```sql ... ``` block
  ↓
run_untrusted_select(sql)
  ├─ Parse: SELECT only, no semicolon chaining, no CTEs with INSERT/DELETE
  ├─ Set SQLite authorizer to reject non-SELECT actions
  ├─ Execute
  ├─ Return DataFrame
  └─ Result:
     name                | category    | profit
     ────────────────────┼─────────────┼──────
     Smartwatch          | Electronics | 500,000
     Kurta Set           | Fashion     | 450,000
     Silk Saree          | Fashion     | 380,000
  ↓
synthesize_insight(question, data_summary)
  ├─ System: "You are a business analyst. Answer in 3–5 sentences,
             grounded strictly in the provided data."
  ├─ Prompt: "Question: Tell me about our most profitable products\n\n
             Data: (first 50 rows shown)\n\nAnswer:"
  ├─ Claude: "Your top 3 most profitable products are Smartwatch
             (Electronics, ₹500k), Kurta Set (Fashion, ₹450k), and Silk
             Saree (Fashion, ₹380k). Electronics and Fashion categories
             dominate profitability. These three SKUs account for 23% of
             total profit."
  └─ Return grounded answer
  ↓
Response:
  {
    "intent": "text_to_sql",
    "answer": "Your top 3 most profitable...",
    "table": [ 5 rows ],
    "chart": { type: "bar", x: "name", y: "profit" },
    "sql": "SELECT p.name, ... ORDER BY profit DESC LIMIT 5",
    "data_source": "Your uploaded data"
  }
```

### Fallback Without LLM Key

```
Environment:
  (ANTHROPIC_API_KEY not set)
  (OPENAI_API_KEY not set)

Free-form question: "Tell me about our most profitable products"
  ↓
classify_intent() → "general"
  ↓
Try RAG: retrieve("profitable products")
  └─ No match
  ↓
LLM available? No
  ↓
Message to user:
  "I couldn't map that question to an analysis I know. I can answer
   questions about **top products**, **sales trends**, ... With an LLM key
   configured I can also write SQL for free-form questions."
```

---

End of Architecture Documentation.
