from app import db, rag


def test_chunks_keep_document_and_section():
    md = ("# Shipping\n\nStandard shipping takes 4-6 business days across India.\n\n"
          "## COD\n\nCash on Delivery is available under 5000 rupees.")
    chunks = rag.chunk_document("ship", md)
    assert [c.section for c in chunks] == ["Shipping", "COD"]
    assert all(c.doc == "ship" for c in chunks)


def test_retrieves_the_relevant_paragraph():
    hits = rag.retrieve("Can I pay cash on delivery?")
    assert hits, "expected at least one hit"
    assert "Cash on Delivery" in hits[0].text
    assert hits[0].doc == "shipping_policy"


def test_scores_are_sorted_and_bounded():
    hits = rag.retrieve("return refund electronics seal", top_k=5)
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)
    assert all(0 < s <= 1.0001 for s in scores)


def test_irrelevant_question_returns_nothing():
    assert rag.retrieve("quantum chromodynamics lattice gauge") == []


def test_tenant_documents_are_searched_only_for_that_tenant():
    doc = ("acme:policy", "# Gift Wrap\n\nAcme offers premium gift wrapping with handwritten notes for 99 rupees.")
    tenant = db.Tenant(key="demo", label="demo", docs=(doc,))
    with db.use_tenant(tenant):
        hits = rag.retrieve("gift wrapping handwritten note")
    assert hits and hits[0].doc == "acme:policy"
    assert rag.retrieve("gift wrapping handwritten note") == []   # default tenant can't see it
