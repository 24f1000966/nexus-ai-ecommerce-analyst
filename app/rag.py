"""
Minimal, dependency-free RAG retriever.

Uses TF-IDF-style keyword overlap scoring instead of embeddings so the demo
runs with zero extra installs and no API key. Swap `retrieve()`'s internals
for a real embedding model + vector DB (e.g. sentence-transformers + Chroma)
once you're ready — the interface (question -> list of (doc_name, chunk,
score)) stays the same, so nothing else in the app needs to change.
"""
import re
from collections import Counter
from pathlib import Path

DOCS_DIR = Path(__file__).parent.parent / "data" / "docs"

_STOPWORDS = {
    "the", "a", "an", "is", "are", "of", "to", "for", "and", "or", "in",
    "on", "what", "how", "do", "does", "my", "i", "can", "we", "our", "it",
    "be", "was", "were", "this", "that", "with", "as", "if", "not",
}


def _tokenize(text: str):
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS]


def _load_chunks():
    """Split each doc into paragraph-level chunks."""
    chunks = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for para in re.split(r"\n\s*\n", text):
            para = para.strip()
            if len(para) > 20:
                chunks.append((path.stem, para))
    return chunks


_CHUNKS = _load_chunks()


def retrieve(question: str, top_k: int = 3):
    """Return the top_k (doc_name, chunk_text, score) most relevant chunks."""
    q_tokens = Counter(_tokenize(question))
    if not q_tokens:
        return []

    scored = []
    for doc_name, chunk in _CHUNKS:
        c_tokens = Counter(_tokenize(chunk))
        overlap = sum((q_tokens & c_tokens).values())
        if overlap > 0:
            scored.append((doc_name, chunk, overlap))

    scored.sort(key=lambda x: x[2], reverse=True)
    return scored[:top_k]
