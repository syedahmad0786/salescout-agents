"""FastAPI surface for Revenue Intelligence Council."""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

sys.path.insert(0, str(Path(__file__).parent / "src"))

from salescout.council import CouncilRecord, CouncilRequest, Decision, decide, execute, get_run  # noqa: E402

app = FastAPI(title="Revenue Intelligence Council", version="1.0.0")
_RATE: dict[tuple[str, date], int] = defaultdict(int)


def _limit(request: Request) -> None:
    key = ((request.headers.get("x-forwarded-for") or request.client.host).split(",")[0], date.today())
    _RATE[key] += 1
    if _RATE[key] > 5:
        raise HTTPException(429, "Public demo limit reached: five runs per IP per day")


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok", "time": datetime.now(UTC), "mode": "replay"}


@app.get("/api/v1/capabilities")
def capabilities() -> dict:
    return {
        "system": "Revenue Intelligence Council",
        "orchestration": "LangGraph",
        "features": ["company research", "qualification", "evidence-linked messaging", "human approval"],
        "limits": {"runs_per_ip_day": 5, "max_agents": 3, "max_steps": 12, "timeout_seconds": 90},
        "external_mutations": "never",
    }


@app.post("/api/v1/accounts/analyze", response_model=CouncilRecord)
def analyze(payload: CouncilRequest, request: Request) -> CouncilRecord:
    _limit(request)
    try:
        return execute(payload)
    except ValueError as exc:
        code = 409 if "idempotency" in str(exc) else 422
        raise HTTPException(code, str(exc)) from exc


@app.get("/api/v1/runs/{run_id}", response_model=CouncilRecord)
def run(run_id: str) -> CouncilRecord:
    record = get_run(run_id)
    if not record:
        raise HTTPException(404, "Run not found in this demo instance")
    return record


@app.post("/api/v1/runs/{run_id}/decisions", response_model=CouncilRecord)
def decision(run_id: str, payload: Decision) -> CouncilRecord:
    try:
        return decide(run_id, payload)
    except KeyError as exc:
        raise HTTPException(404, "Run not found in this demo instance") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


PAGE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Revenue Intelligence Council</title><style>
:root{--navy:#0b1e35;--cream:#f4efe5;--ink:#152336;--cobalt:#315ed8;--rust:#b64c2f;--line:#cfc4b3}*{box-sizing:border-box}body{margin:0;background:var(--cream);color:var(--ink);font-family:Segoe UI,Arial,sans-serif}main{max-width:1120px;margin:auto;padding:34px 22px 70px}.case-no{font:700 11px Consolas,monospace;letter-spacing:.17em;text-transform:uppercase;color:var(--rust)}h1{max-width:850px;margin:10px 0;font:650 clamp(44px,8vw,88px)/.92 Georgia,serif;letter-spacing:-.055em}.lede{max-width:690px;font:18px/1.55 Georgia,serif}.folder{margin-top:34px;display:grid;grid-template-columns:300px 1fr;background:white;border:1px solid var(--line);box-shadow:12px 12px 0 #dacfbf}.controls{padding:24px;background:var(--navy);color:var(--cream)}label{display:block;margin-bottom:8px}select,button{width:100%;padding:12px;border:1px solid #70819a;border-radius:0;background:#102a49;color:var(--cream);font-weight:700}button{margin-top:12px;background:var(--cream);color:var(--navy);border-color:var(--cream);cursor:pointer}button:focus-visible,select:focus-visible{outline:3px solid #e2a78e;outline-offset:2px}.boundary{font-size:13px;line-height:1.55;color:#b9c4d2}.brief{padding:25px;min-height:430px}.empty{text-align:center;color:#7c746c;margin-top:155px}.meta{display:flex;gap:12px;flex-wrap:wrap;border-bottom:1px solid var(--line);padding-bottom:15px;margin-bottom:15px}.pill{font:700 12px Consolas,monospace;padding:6px 9px;background:#e6ebfb;color:var(--cobalt)}.pill.score{background:#f3ded7;color:var(--rust)}.agent{display:grid;grid-template-columns:150px 1fr;gap:14px;padding:11px 0;border-bottom:1px solid #e5ddd0}.agent strong{font:700 12px Consolas,monospace;text-transform:uppercase;color:var(--cobalt)}.agent span{color:#596474}.draft{margin-top:18px;border-left:4px solid var(--rust);padding:14px 16px;background:#faf6ef}.draft h3{margin:4px 0 8px}.draft p{line-height:1.5}.foot{margin-top:22px;font:12px Consolas,monospace;color:#746c63}@media(max-width:700px){main{padding:24px 16px}.folder{grid-template-columns:1fr;box-shadow:7px 7px 0 #dacfbf}.brief{min-height:360px}.empty{margin-top:100px}.agent{grid-template-columns:1fr;gap:4px}}
</style></head><body><main><div class="case-no">Portfolio system 04 · evidence before outreach</div><h1>The council drafts. A person decides.</h1><p class="lede">Research, qualification, strategy, and writing share one evidence record. The final output is a reviewable draft—never a sent email or a CRM write.</p><section class="folder"><div class="controls"><label class="case-no" for="scenario">Synthetic account</label><select id="scenario"><option value="data_fragmentation">Fieldstone Commerce</option><option value="operations_scale">Harbor Logistics</option><option value="agency_capacity">Signal House</option><option value="compliance_gap">ClearLedger</option><option value="low_fit">Solo Orchard · low fit</option></select><button id="run">Convene the council</button><p class="boundary">Public replay uses synthetic company packets. Approval marks a draft usable; it does not send or synchronize anything. API contract: <code>/docs</code>.</p></div><div class="brief" id="brief"><p class="empty">Choose an account to inspect the evidence-to-draft chain.</p></div></section><p class="foot">Agentic AI &amp; LLM Systems Specialist · Ahmad Bukhari</p></main><script>
const brief=document.querySelector('#brief'),button=document.querySelector('#run');button.addEventListener('click',async()=>{button.disabled=true;button.textContent='Council working…';brief.innerHTML='<p class="empty">Research → qualify → strategy → draft gate</p>';try{const scenario=document.querySelector('#scenario').value;const response=await fetch('/api/v1/accounts/analyze',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({scenario,input:{},mode:'replay',idempotency_key:`account-${scenario}-0001`})});const data=await response.json();if(!response.ok)throw new Error(data.detail||'Run failed');brief.innerHTML=`<div class="meta"><span class="pill">${data.outputs.company}</span><span class="pill score">fit ${data.outputs.analysis.fit_score}/100</span><span class="pill">${data.status.replaceAll('_',' ')}</span></div>`+data.agent_steps.map(step=>`<div class="agent"><strong>${step.agent}</strong><span>${step.action}</span></div>`).join('')+`<article class="draft"><div class="case-no">Draft only · 0 sends · 0 CRM writes</div><h3>${data.outputs.drafts[0].subject}</h3><p>${data.outputs.drafts[0].body}</p></article>`}catch(error){brief.innerHTML=`<p class="empty">${error.message}</p>`}finally{button.disabled=false;button.textContent='Convene the council'}});
</script></body></html>'''


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index() -> str:
    return PAGE
