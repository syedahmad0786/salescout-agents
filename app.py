"""SaleScout — Streamlit UI with live agent traces.

Run:  streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import streamlit as st

from salescout.config import provider_name
from salescout.graph import build_graph
from salescout.tools import normalize_domain

st.set_page_config(page_title="SaleScout", page_icon="🔭", layout="wide")

st.title("SaleScout")
st.caption(
    f"Multi-agent sales research crew · researcher → analyst → writer · "
    f"LLM: **{provider_name()}** (free)"
)

domain_input = st.text_input(
    "Company domain", placeholder="acme.com", help="Just the domain — no https://"
)

if st.button("Run the crew", type="primary", disabled=not domain_input):
    domain = normalize_domain(domain_input)
    app = build_graph()

    final_state: dict = {}
    with st.status(f"Scouting **{domain}** ...", expanded=True) as status:
        # stream node-by-node so the user watches agents hand off work
        for chunk in app.stream({"domain": domain}, stream_mode="updates"):
            for node, update in chunk.items():
                for event in update.get("trace", []):
                    st.write(
                        f"\`{event['agent']}\` **{event['action']}** "
                        f"{str(event.get('detail', ''))[:90]}"
                    )
                final_state.update(update)
        status.update(label="Crew finished", state="complete")

    if not final_state.get("brief_md"):
        st.error("Run ended early — the researcher could not gather enough material.")
        for err in final_state.get("errors", []):
            st.caption(f"· {err}")
        st.stop()

    analysis = final_state.get("analysis", {})
    col1, col2, col3 = st.columns(3)
    col1.metric("Fit score", f"{analysis.get('fit_score', 'n/a')}/100")
    col2.metric("Pages read", len(final_state.get("pages", {})))
    col3.metric("News items", len(final_state.get("search_results", [])))

    tab_brief, tab_emails, tab_research = st.tabs(
        ["Outreach brief", "Email drafts", "Raw research"]
    )

    with tab_brief:
        st.markdown(final_state["brief_md"])
        st.download_button(
            "Download brief (.md)",
            final_state["brief_md"],
            file_name=f"{domain.replace('.', '_')}_brief.md",
        )

    with tab_emails:
        for i, email in enumerate(final_state.get("emails", []), start=1):
            st.subheader(f"Draft {i}: {email.get('subject', '')}")
            st.code(email.get("body", ""), language=None)

    with tab_research:
        st.markdown(final_state.get("research_notes", ""))
        with st.expander("Sources"):
            for url in final_state.get("pages", {}):
                st.write(url)
            for hit in final_state.get("search_results", [])[:6]:
                st.write(hit.get("url", hit.get("href", "")))
