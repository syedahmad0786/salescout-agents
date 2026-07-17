"""LLM provider factory — free by default.

Priority:
1. If ``GROQ_API_KEY`` is set   -> Groq (free tier, fast Llama 3.3 70B)
2. Otherwise                    -> Ollama running locally (100% free, offline)

No paid API is ever required.
"""

from __future__ import annotations

import os

DEFAULT_OLLAMA_MODEL = "llama3.1"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"

# How many site pages the researcher is allowed to crawl per company.
MAX_PAGES = int(os.getenv("SALESCOUT_MAX_PAGES", "4"))

# Character budget per page fed to the LLM (keeps local models snappy).
PAGE_CHAR_BUDGET = int(os.getenv("SALESCOUT_PAGE_CHARS", "6000"))


def get_llm(temperature: float = 0.2):
    """Return a chat model instance for whichever free provider is available."""
    if os.getenv("GROQ_API_KEY"):
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL),
            temperature=temperature,
        )

    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
        temperature=temperature,
    )


def provider_name() -> str:
    """Human-readable name of the active provider (for the UI/trace)."""
    if os.getenv("GROQ_API_KEY"):
        return f"Groq · {os.getenv('GROQ_MODEL', DEFAULT_GROQ_MODEL)}"
    return f"Ollama · {os.getenv('OLLAMA_MODEL', DEFAULT_OLLAMA_MODEL)}"
