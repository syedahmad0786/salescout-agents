"""The three agents in the SaleScout crew.

researcher  -> reads the company's site + recent news, writes research notes
analyst     -> scores fit, extracts buying signals and talking points (JSON)
writer      -> produces the outreach brief + two ready-to-send emails
"""

from __future__ import annotations

import json
import re
import time

from langchain_core.messages import HumanMessage, SystemMessage

from .config import MAX_PAGES, get_llm, provider_name
from .state import ScoutState
from .tools import (
    extract_text,
    fetch,
    fetch_homepage,
    find_key_pages,
    normalize_domain,
    search_news,
)


def _event(agent: str, action: str, detail: str = "") -> dict:
    return {"agent": agent, "action": action, "detail": detail, "ts": time.time()}


def _extract_json(raw: str) -> dict:
    """Pull the first JSON object out of an LLM reply, defensively."""
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


# --------------------------------------------------------------------------- #
# 1. RESEARCHER
# --------------------------------------------------------------------------- #

RESEARCHER_SYSTEM = (
    "You are a meticulous B2B sales researcher. Using ONLY the provided page "
    "text and news snippets, write structured research notes with sections: "
    "Company Overview, Products & Services, Target Customers, Recent "
    "Developments, Tech & Tooling Hints. Be factual — if something is not in "
    "the sources, say 'not found' rather than guessing."
)


def researcher(state: ScoutState) -> dict:
    domain = normalize_domain(state["domain"])
    trace = [_event("researcher", "start", f"target={domain} · llm={provider_name()}")]
    errors: list[str] = []
    pages: dict[str, str] = {}

    try:
        home_url, home_html = fetch_homepage(domain)
        pages[home_url] = extract_text(home_html)
        trace.append(_event("researcher", "fetched", home_url))

        for url in find_key_pages(home_html, home_url, limit=MAX_PAGES - 1):
            try:
                pages[url] = extract_text(fetch(url))
                trace.append(_event("researcher", "fetched", url))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{url}: {exc}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"homepage: {exc}")
        trace.append(_event("researcher", "failed", str(exc)))
        return {"pages": {}, "errors": errors, "trace": trace}

    news = search_news(f"{domain} company news")
    trace.append(_event("researcher", "news_search", f"{len(news)} results"))

    news_block = "\n".join(
        f"- {n.get('title', '')} — {n.get('body', n.get('excerpt', ''))[:200]}"
        for n in news[:6]
    )
    pages_block = "\n\n".join(f"[{url}]\n{text}" for url, text in pages.items())

    llm = get_llm(temperature=0.1)
    reply = llm.invoke(
        [
            SystemMessage(content=RESEARCHER_SYSTEM),
            HumanMessage(
                content=f"Company website pages:\n{pages_block}\n\n"
                f"Recent news:\n{news_block or 'none found'}"
            ),
        ]
    )
    trace.append(_event("researcher", "notes_written", f"{len(reply.content)} chars"))

    company_name = domain.split(".")[0].replace("-", " ").title()
    return {
        "company_name": company_name,
        "pages": pages,
        "search_results": news,
        "research_notes": reply.content,
        "errors": errors,
        "trace": trace,
    }


# --------------------------------------------------------------------------- #
# 2. ANALYST
# --------------------------------------------------------------------------- #

ANALYST_SYSTEM = (
    "You are a revenue analyst qualifying outbound prospects. Given research "
    "notes, reply with ONLY a JSON object:\n"
    "{\n"
    '  "fit_score": <0-100 int>,\n'
    '  "company_snapshot": "<one paragraph>",\n'
    '  "buying_signals": ["..."],\n'
    '  "pain_points": ["..."],\n'
    '  "talking_points": ["..."],\n'
    '  "tech_stack_hints": ["..."],\n'
    '  "recommended_angle": "<the single best opening angle>"\n'
    "}"
)


def analyst(state: ScoutState) -> dict:
    trace = [_event("analyst", "start")]
    llm = get_llm(temperature=0.1)
    reply = llm.invoke(
        [
            SystemMessage(content=ANALYST_SYSTEM),
            HumanMessage(content=state.get("research_notes", "")),
        ]
    )
    analysis = _extract_json(reply.content)
    if not analysis:
        analysis = {"fit_score": 0, "company_snapshot": reply.content[:500]}
        trace.append(_event("analyst", "json_fallback", "model reply was not JSON"))
    trace.append(_event("analyst", "scored", f"fit_score={analysis.get('fit_score')}"))
    return {"analysis": analysis, "trace": trace}


# --------------------------------------------------------------------------- #
# 3. WRITER
# --------------------------------------------------------------------------- #

WRITER_BRIEF_SYSTEM = (
    "You are a sales enablement writer. Turn the research notes and analysis "
    "into a crisp outreach brief in Markdown with sections: TL;DR, Company "
    "Snapshot, Why Now (buying signals), Pain Hypotheses, Talking Points, "
    "Recommended Angle. Keep it under 450 words. No preamble."
)

WRITER_EMAIL_SYSTEM = (
    "You write concise, personalized cold emails (no fluff, no 'I hope this "
    "finds you well'). Reply with ONLY a JSON array of exactly two objects: "
    '[{"subject": "...", "body": "..."}, {"subject": "...", "body": "..."}] '
    "— first a cold opener under 120 words, second a value-add follow-up "
    "under 80 words. Ground both in the provided analysis."
)


def writer(state: ScoutState) -> dict:
    trace = [_event("writer", "start")]
    llm = get_llm(temperature=0.4)
    context = (
        f"Company: {state.get('company_name')}\n\n"
        f"Research notes:\n{state.get('research_notes', '')}\n\n"
        f"Analysis:\n{json.dumps(state.get('analysis', {}), indent=2)}"
    )

    brief = llm.invoke(
        [SystemMessage(content=WRITER_BRIEF_SYSTEM), HumanMessage(content=context)]
    )
    trace.append(_event("writer", "brief_written", f"{len(brief.content)} chars"))

    emails_raw = llm.invoke(
        [SystemMessage(content=WRITER_EMAIL_SYSTEM), HumanMessage(content=context)]
    )
    match = re.search(r"\[.*\]", emails_raw.content, re.S)
    emails: list[dict] = []
    if match:
        try:
            emails = json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    if not emails:
        emails = [{"subject": "Draft", "body": emails_raw.content}]
        trace.append(_event("writer", "json_fallback", "email reply was not JSON"))
    trace.append(_event("writer", "emails_drafted", f"{len(emails)} drafts"))

    return {"brief_md": brief.content, "emails": emails, "trace": trace}
