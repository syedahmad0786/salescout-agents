"""LangGraph wiring: researcher -> analyst -> writer, with a guard edge
that ends the run early if research produced nothing usable."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .agents import analyst, researcher, writer
from .state import ScoutState


def _research_succeeded(state: ScoutState) -> str:
    """Only continue to analysis if the researcher produced notes."""
    return "analyst" if state.get("research_notes") else END


def build_graph():
    graph = StateGraph(ScoutState)

    graph.add_node("researcher", researcher)
    graph.add_node("analyst", analyst)
    graph.add_node("writer", writer)

    graph.add_edge(START, "researcher")
    graph.add_conditional_edges(
        "researcher", _research_succeeded, {"analyst": "analyst", END: END}
    )
    graph.add_edge("analyst", "writer")
    graph.add_edge("writer", END)

    return graph.compile()


def run_scout(domain: str) -> ScoutState:
    """Convenience entry point: research one company end to end."""
    app = build_graph()
    return app.invoke({"domain": domain})
