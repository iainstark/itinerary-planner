"""
main.py
=======
The FastAPI web server.

Run locally with:
  uvicorn app.main:app --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.planner import run_chain

app = FastAPI(
    title="Trip Itinerary Planner",
    description="AI-powered itinerary planning with verification",
    version="1.0.0"
)


class PlanRequest(BaseModel):
    brief: str


class PlanResponse(BaseModel):
    final: str
    events: str


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/plan", response_model=PlanResponse)
async def plan_itinerary(request: PlanRequest):
    if not request.brief.strip():
        raise HTTPException(status_code=400, detail="Trip brief cannot be empty.")
    try:
        result = run_chain(request.brief)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


app.mount("/", StaticFiles(directory="static", html=True), name="static")
