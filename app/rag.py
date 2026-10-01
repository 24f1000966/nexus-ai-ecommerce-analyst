"""
Retrieval-Augmented Generation (RAG) over policy / knowledge-base documents.

Pipeline (see docs/RAG.md for the diagram):

  1. Ingest   - load the platform docs in data/docs/*.md plus any documents the
                current company uploaded (tenant.docs).
  2. Chunk    - split each document on markdown headings, then into paragraph
                chunks; every chunk remembers its document and section title.
  3. Index    - turn every chunk into a TF-IDF vector (sublinear term frequency
                x smoothed inverse document frequency, L2-normalised).
  4. Retrieve - vectorise the question the same way and rank chunks by cosine
                similarity; keep the top_k above a minimum score.
  5. Generate - the agent passes the retrieved chunks to the LLM as grounding
                context (or shows them directly in offline mode), with citations.

It is dependency-free on purpose so the demo runs with no API key. The public
interface — retrieve(question) -> list[Hit] — stays the same if the TF-IDF
index is replaced by dense embeddings + a vector DB (e.g. pgvector).
"""
import math
import re
import threading
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from app import db

DOCS_DIR = Path(__file__).parent.parent / "data" / "docs"
MIN_SCORE = 0.08          # cosine similarity below this is treated as "not relevant"

_STOPWORDS = {
    "the", "a", "an", "is", "are", "of", "to", "for", "and", "or", "in", "on",
    "what", "how", "do", "does", "my", "i", "can", "we", "our", "it", "be",
    "was", "were", "this", "that", "with", "as", "if", "not", "you", "your",
    "any", "from", "by", "at", "will", "there", "which", "who", "me", "us",
    "tell", "about", "please", "have", "has", "q", "a",
}


def _stem(word: str) -> str:
    """Tiny suffix stripper so 'returns', 'returned' and 'returning' all match 'return'."""
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def tokenize(text: str) -> list[str]:
    return [_stem(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS]


@dataclass(frozen=True)
class Chunk:
    doc: str
    section: str
    text: str


@dataclass(frozen=True)
class Hit:
    doc: str
    section: str
    text: str
    score: float

    def cite(self) -> str:
        return f"{self.doc} › {self.section}" if self.section else self.doc


def chunk_document(doc_name: str, markdown: str, min_chars: int = 80, max_chars: int = 600) -> list[Chunk]:
    """Split on headings, then on blank lines (one paragraph / one FAQ entry per chunk).
    Fragments shorter than min_chars are merged into the next paragraph."""
    chunks, section, buffer = [], "", ""

    def flush():
        nonlocal buffer
        if len(buffer.strip()) > 20:
            chunks.append(Chunk(doc_name, section, buffer.strip()))
        buffer = ""

    for block in re.split(r"\n\s*\n", markdown):
        block = block.strip()
        if not block:
            continue
        heading = re.match(r"^#{1,6}\s+(.*)", block)
        if heading:
            flush()
            section = heading.group(1).strip()
            rest = block[heading.end():].strip()
            if rest:
                buffer = rest
            continue
        if buffer and (len(buffer) >= min_chars or len(buffer) + len(block) > max_chars):
            flush()
        buffer = f"{buffer}\n\n{block}" if buffer else block
    flush()
    return chunks


class TfidfIndex:
    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        token_lists = [tokenize(f"{c.section} {c.text}") for c in chunks]
        n = len(chunks)
        df = Counter(t for tokens in token_lists for t in set(tokens))
        self.idf = {t: math.log((1 + n) / (1 + d)) + 1 for t, d in df.items()}
        self.vectors = [self._vectorize(tokens) for tokens in token_lists]

    def _vectorize(self, tokens: list[str]) -> dict[str, float]:
        tf = Counter(tokens)
        vec = {t: (1 + math.log(c)) * self.idf[t] for t, c in tf.items() if t in self.idf}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def search(self, question: str, top_k: int = 3, min_score: float = MIN_SCORE) -> list[Hit]:
        q = self._vectorize(tokenize(question))
        if not q:
            return []
        scored = []
        for chunk, vec in zip(self.chunks, self.vectors):
            score = sum(w * vec.get(t, 0.0) for t, w in q.items())   # cosine (both unit length)
            if score >= min_score:
                scored.append(Hit(chunk.doc, chunk.section, chunk.text, round(score, 3)))
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:top_k]


def _platform_docs() -> list[tuple[str, str]]:
    return [(p.stem, p.read_text(encoding="utf-8")) for p in sorted(DOCS_DIR.glob("*.md"))]


_PLATFORM_DOCS = _platform_docs()
_indexes: dict[tuple, TfidfIndex] = {}
_lock = threading.Lock()


def index_for(tenant: db.Tenant) -> TfidfIndex:
    """One index per distinct document set; rebuilt only when a company's docs change."""
    key = tuple((name, hash(text)) for name, text in tenant.docs)
    with _lock:
        if key not in _indexes:
            if len(_indexes) > 64:
                _indexes.clear()
            chunks = [c for name, text in (*_PLATFORM_DOCS, *tenant.docs) for c in chunk_document(name, text)]
            _indexes[key] = TfidfIndex(chunks)
        return _indexes[key]


def retrieve(question: str, top_k: int = 3) -> list[Hit]:
    """Return the top_k chunks most relevant to the question for the current tenant."""
    return index_for(db.current_tenant()).search(question, top_k)


def format_context(hits: list[Hit]) -> str:
    return "\n\n".join(f"[{h.cite()}]\n{h.text}" for h in hits)
