"""
Thin LLM abstraction. If ANTHROPIC_API_KEY or OPENAI_API_KEY is set in the
environment, real calls are used for text-to-SQL generation and for writing
the final natural-language insight. Otherwise `available()` returns False and
the rest of the app falls back to the rule-based agent in agent.py — so the
demo works fully offline, and plugging in a key later upgrades it with zero
other code changes.
"""
import os

_ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
_OPENAI_KEY = os.environ.get("OPENAI_API_KEY")


def available() -> bool:
    return bool(_ANTHROPIC_KEY or _OPENAI_KEY)


def _call_anthropic(system: str, prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=_ANTHROPIC_KEY)
    resp = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


def _call_openai(system: str, prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=_OPENAI_KEY)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content


def ask(system: str, prompt: str) -> str:
    """Route to whichever provider has a key configured."""
    if _ANTHROPIC_KEY:
        return _call_anthropic(system, prompt)
    if _OPENAI_KEY:
        return _call_openai(system, prompt)
    raise RuntimeError("No LLM API key configured; call available() first.")


def generate_sql(question: str, schema: str) -> str:
    system = (
        "You are a SQLite expert. Given a table schema and a business "
        "question, output ONLY the SQL query (no markdown, no explanation) "
        "that answers it."
    )
    prompt = f"Schema:\n{schema}\n\nQuestion: {question}\n\nSQL:"
    sql = ask(system, prompt).strip()
    return sql.strip("`").replace("sql\n", "", 1) if sql.startswith("```") else sql


def synthesize_insight(question: str, data_summary: str, retrieved_context: str = "") -> str:
    system = (
        "You are a business data analyst for an e-commerce company. Answer "
        "the user's question in 3-5 sentences, grounded strictly in the "
        "provided data and context. Mention concrete numbers."
    )
    prompt = (
        f"Question: {question}\n\nData:\n{data_summary}\n\n"
        f"Relevant policy/context:\n{retrieved_context}\n\nAnswer:"
    )
    return ask(system, prompt).strip()
