from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from .fixtures import PROFILES, SCENARIOS
from .engine import assess, run_baseline

app = FastAPI(title="CloudRescue", version="0.1.0")

class SimulationRequest(BaseModel):
    scenario_id: str
    workload: str | None = None

@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "cloudrescue"}

@app.get("/report")
def report():
    return run_baseline()

@app.get("/scenarios")
def scenarios():
    return [s.__dict__ for s in SCENARIOS]

@app.post("/simulate")
def simulate(req: SimulationRequest):
    scenario = next((s for s in SCENARIOS if s.scenario_id == req.scenario_id), None)
    if not scenario:
        raise HTTPException(status_code=404, detail="unknown scenario")
    workload_name = req.workload or scenario.workload
    profile = PROFILES.get(workload_name)
    if not profile:
        raise HTTPException(status_code=404, detail="unknown workload")
    return assess(profile, scenario).to_dict()

@app.get("/", response_class=HTMLResponse)
def dashboard():
    report = run_baseline()
    s = report["summary"]
    rows = "".join(
        f"<tr><td>{a['scenario_id']}</td><td>{a['workload']}</td><td>{a['cloud']}</td><td>{a['status']}</td><td>{a['recovery_confidence']}</td><td>{', '.join(a['blockers']) or 'none'}</td></tr>"
        for a in report["assessments"]
    )
    return f"""<!doctype html><html><head><title>CloudRescue</title><style>
    body{{font-family:Arial;background:#07111f;color:#e5eefc;margin:0;padding:36px}} .card{{background:#0f1c2e;border:1px solid #263b55;border-radius:14px;padding:18px;margin:10px;display:inline-block;min-width:180px}} h1{{font-size:34px}} .n{{font-size:28px;font-weight:700}} table{{width:100%;border-collapse:collapse;margin-top:24px;background:#0f1c2e}} td,th{{padding:12px;border-bottom:1px solid #263b55;text-align:left}} .sub{{color:#9fb1c8}}</style></head><body>
    <h1>CloudRescue</h1><p class='sub'>Cloud ransomware resilience & recovery assurance</p>
    <div class='card'><div class='n'>{s['mean_recovery_confidence']}</div>Mean confidence</div>
    <div class='card'><div class='n'>{s['ready']}/{s['scenarios']}</div>Ready scenarios</div>
    <div class='card'><div class='n'>{s['unrecoverable']}</div>Recovery failures</div>
    <div class='card'><div class='n'>{s['rto_targets_met']}/{s['scenarios']}</div>RTO met</div>
    <table><tr><th>Scenario</th><th>Workload</th><th>Cloud</th><th>Status</th><th>Confidence</th><th>Blockers</th></tr>{rows}</table>
    </body></html>"""
