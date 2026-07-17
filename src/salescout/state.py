"""Shared graph state for the SaleScout agent crew."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class ScoutState(TypedDict, total=False):
    """State passed between agents in the LangGraph pipeline.

    ``errors`` and ``trace`` use ``operator.add`` reducers so every agent
    can append events without clobbering what earlier agents wrote.
    """

    # inputs
    domain: str

    # researcher outputs
    company_name: str
    pages: dict[str, str]            # url -> extracted page text
    search_results: list[dict]       # news / web results
    research_notes: str

    # analyst outputs
    analysis: dict[str, Any]         # fit score, signals, angles

    # writer outputs
    brief_md: str
    emails: list[dict]               # [{"subject": ..., "body": ...}]

    # bookkeeping (append-only)
    errors: Annotated[list[str], operator.add]
    trace: Annotated[list[dict], operator.add]
