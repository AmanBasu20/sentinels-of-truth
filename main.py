from fastapi import FastAPI
from pydantic import BaseModel
from orchestrator import app as langgraph_app
from database import init_db

init_db()
api = FastAPI(title="Sentinels of Truth API")

class ClaimRequest(BaseModel):
    claim: str

@api.post("/api/verify")
async def verify_claim(request: ClaimRequest):
    final_state = langgraph_app.invoke({
        "claim": request.claim,
        "trace": ["System received new claim from web UI."]
    })
    return {
        "claim": final_state["claim"],
        "verdict": final_state["report"].status,
        "confidence": final_state["report"].confidence,
        "action_taken": final_state["beta_action"],
        "history": final_state["trace"]
    }