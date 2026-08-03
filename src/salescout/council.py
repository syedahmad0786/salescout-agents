"""Evidence-backed, draft-only Revenue Intelligence Council."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field


ACCOUNT_SCENARIOS: dict[str, dict[str, Any]] = {
    "saas_growth": {"company": "Northstar Metrics", "sector": "B2B SaaS", "signals": ["Hiring customer success roles", "Published a multi-region launch"], "risks": ["No public procurement timeline"], "fit": 84},
    "services_expansion": {"company": "Cedar Creative", "sector": "Creative services", "signals": ["Added two service lines", "Case-study volume doubled"], "risks": ["Decision team not public"], "fit": 78},
    "operations_scale": {"company": "Harbor Logistics", "sector": "Logistics", "signals": ["Opened a second operations hub", "Manual intake is described publicly"], "risks": ["Integration inventory unknown"], "fit": 88},
    "compliance_gap": {"company": "ClearLedger", "sector": "Finance operations", "signals": ["Published audit-readiness guidance", "Growing partner network"], "risks": ["Strict vendor review likely"], "fit": 74},
    "customer_churn": {"company": "Juniper Cloud", "sector": "Cloud services", "signals": ["Launched a retention program", "Support leadership role is open"], "risks": ["Churn rate not disclosed"], "fit": 81},
    "data_fragmentation": {"company": "Fieldstone Commerce", "sector": "E-commerce", "signals": ["Lists five disconnected operating tools", "New analytics lead joined"], "risks": ["Data ownership unclear"], "fit": 91},
    "agency_capacity": {"company": "Signal House", "sector": "Marketing agency", "signals": ["Client roster expanded", "Operations coordinator role is open"], "risks": ["Budget not public"], "fit": 86},
    "healthcare_admin": {"company": "Wellway Admin", "sector": "Healthcare administration", "signals": ["Expanding non-clinical scheduling", "Published privacy controls"], "risks": ["Patient PHI is excluded from analysis"], "fit": 70},
    "manufacturing_quality": {"company": "Atlas Components", "sector": "Manufacturing", "signals": ["Quality incident review is manual", "New plant announced"], "risks": ["OT network access out of scope"], "fit": 76},
    "low_fit": {"company": "Solo Orchard", "sector": "Local retail", "signals": ["Single location"], "risks": ["No scale or integration signal", "Likely below minimum project scope"], "fit": 28},
}


class CouncilRequest(BaseModel):
    scenario: Literal[
        "saas_growth", "services_expansion", "operations_scale", "compliance_gap", "customer_churn",
        "data_fragmentation", "agency_capacity", "healthcare_admin", "manufacturing_quality", "low_fit"
    ] = "data_fragmentation"
    input: dict[str, Any] = Field(default_factory=dict)
    mode: Literal["replay", "live"] = "replay"
    idempotency_key: str = Field(min_length=8, max_length=120)


class EvidenceRef(BaseModel):
    evidence_id: str
    source: str
    locator: str
    retrieved_at: datetime
    content_hash: str
    excerpt: str


class Proposal(BaseModel):
    action_type: Literal["review_outreach_draft"] = "review_outreach_draft"
    payload: dict[str, Any]
    reasoning: str
    confidence: float = Field(ge=0, le=1)
    required_approver: str = "account owner"


class Decision(BaseModel):
    decision: Literal["approve", "reject"]
    actor: str = Field(min_length=2, max_length=120)
    reason: str = Field(min_length=3, max_length=500)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CouncilRecord(BaseModel):
    run_id: str
    status: Literal["awaiting_approval", "approved_for_manual_use", "rejected"]
    scenario: str
    mode: str
    created_at: datetime
    input_hash: str
    agent_steps: list[dict[str, Any]]
    outputs: dict[str, Any]
    evidence: list[EvidenceRef]
    proposal: Proposal
    decision: Decision | None = None
    errors: list[str] = Field(default_factory=list)


class CouncilState(TypedDict, total=False):
    scenario: str
    fixture: dict[str, Any]
    evidence: list[dict[str, Any]]
    analysis: dict[str, Any]
    strategy: dict[str, Any]
    drafts: list[dict[str, Any]]
    trace: list[dict[str, Any]]


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def research_node(state: CouncilState) -> dict:
    fixture = ACCOUNT_SCENARIOS[state["scenario"]]
    evidence = []
    for index, text in enumerate(fixture["signals"] + fixture["risks"], start=1):
        evidence.append(EvidenceRef(
            evidence_id=f"ev-{index}", source="synthetic company packet",
            locator=f"{state['scenario']}:{index}", retrieved_at=datetime.now(UTC),
            content_hash=_hash(text), excerpt=text,
        ).model_dump(mode="json"))
    return {"fixture": fixture, "evidence": evidence, "trace": [{"agent": "company-researcher", "action": "packet-read", "evidence": len(evidence)}]}


def qualification_node(state: CouncilState) -> dict:
    fixture = state["fixture"]
    return {
        "analysis": {
            "fit_score": fixture["fit"],
            "qualified": fixture["fit"] >= 65,
            "buying_signals": fixture["signals"],
            "risks": fixture["risks"],
        },
        "trace": state["trace"] + [{"agent": "opportunity-analyst", "action": "qualified", "fit_score": fixture["fit"]}],
    }


def strategy_node(state: CouncilState) -> dict:
    fixture, analysis = state["fixture"], state["analysis"]
    angle = f"Help {fixture['company']} connect operating evidence before adding more automation"
    if not analysis["qualified"]:
        angle = "Do not pursue now; retain only as a future-fit watch item"
    claims = [
        {"text": signal, "evidence_ids": [f"ev-{index}"]}
        for index, signal in enumerate(fixture["signals"], start=1)
    ]
    return {"strategy": {"recommended_angle": angle, "grounded_claims": claims}, "trace": state["trace"] + [{"agent": "message-strategist", "action": "angle-drafted"}]}


def writer_node(state: CouncilState) -> dict:
    fixture, analysis = state["fixture"], state["analysis"]
    first_signal = fixture["signals"][0]
    drafts = [{
        "subject": f"A systems question for {fixture['company']}",
        "body": f"I noticed {first_signal.lower()}. I drafted a short systems review around where evidence, approvals, and handoffs may be slowing the next stage. If useful, an account owner can review it before anything is sent.",
        "grounded_claim_ids": ["ev-1"],
        "send_status": "draft_only",
    }]
    if not analysis["qualified"]:
        drafts[0]["body"] = "No outreach recommended. The current public evidence does not support an implementation conversation."
        drafts[0]["grounded_claim_ids"] = []
    return {"drafts": drafts, "trace": state["trace"] + [{"agent": "outreach-writer", "action": "drafted", "sent": False, "crm_writes": 0}]}


def build_council_graph():
    graph = StateGraph(CouncilState)
    graph.add_node("researcher", research_node)
    graph.add_node("qualifier", qualification_node)
    graph.add_node("strategist", strategy_node)
    graph.add_node("writer", writer_node)
    graph.add_edge(START, "researcher")
    graph.add_edge("researcher", "qualifier")
    graph.add_edge("qualifier", "strategist")
    graph.add_edge("strategist", "writer")
    graph.add_edge("writer", END)
    return graph.compile()


_RUNS: dict[str, CouncilRecord] = {}
_KEYS: dict[str, str] = {}


def execute(request: CouncilRequest) -> CouncilRecord:
    payload_hash = _hash(request.model_dump(mode="json"))
    existing = _KEYS.get(request.idempotency_key)
    if existing:
        record = _RUNS[existing]
        if record.input_hash != payload_hash:
            raise ValueError("idempotency key was already used for different input")
        return record
    if request.mode != "replay":
        raise ValueError("live research requires provider approval and is disabled in the public preview")
    state = build_council_graph().invoke({"scenario": request.scenario, "trace": []})
    evidence = [EvidenceRef.model_validate(item) for item in state["evidence"]]
    fixture = state["fixture"]
    proposal = Proposal(
        payload={
            "company": fixture["company"], "analysis": state["analysis"],
            "strategy": state["strategy"], "drafts": state["drafts"],
        },
        reasoning="Research, qualification, and wording are evidence-linked; an account owner must decide whether the draft is usable.",
        confidence=min(0.95, max(0.3, state["analysis"]["fit_score"] / 100)),
    )
    run_id = f"run_{payload_hash[:16]}"
    record = CouncilRecord(
        run_id=run_id, status="awaiting_approval", scenario=request.scenario, mode=request.mode,
        created_at=datetime.now(UTC), input_hash=payload_hash, agent_steps=state["trace"],
        outputs={
            "company": fixture["company"], "sector": fixture["sector"],
            "analysis": state["analysis"], "strategy": state["strategy"], "drafts": state["drafts"],
            "emails_sent": 0, "crm_writes": 0, "mutations_performed": 0,
        },
        evidence=evidence, proposal=proposal,
    )
    _RUNS[run_id] = record
    _KEYS[request.idempotency_key] = run_id
    return record


def decide(run_id: str, decision: Decision) -> CouncilRecord:
    record = _RUNS.get(run_id)
    if not record:
        raise KeyError(run_id)
    if record.status != "awaiting_approval":
        raise ValueError("this run is not awaiting a decision")
    record.decision = decision
    record.status = "approved_for_manual_use" if decision.decision == "approve" else "rejected"
    record.outputs.update({"emails_sent": 0, "crm_writes": 0, "mutations_performed": 0})
    return record


def get_run(run_id: str) -> CouncilRecord | None:
    return _RUNS.get(run_id)
