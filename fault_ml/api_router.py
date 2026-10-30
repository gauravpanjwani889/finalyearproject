"""FastAPI router. Backend me add karo:

    from fault_ml.api_router import router as ml_router
    app.include_router(ml_router)

Endpoints:  GET /api/ml/status     POST /api/ml/predict   (full-resolution waveform JSON)
Ya seedha sim_runner me:  pred = FaultPredictor().predict_run(time, signals)   # signals = ScopeData (N, 9)
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ml_predict import FaultPredictor, DEFAULT_MODEL
import numpy as np

router = APIRouter(prefix="/api/ml", tags=["ml"])
_pred: Optional[FaultPredictor] = None


def _get() -> FaultPredictor:
    global _pred
    if _pred is None:
        if not DEFAULT_MODEL.exists():
            raise HTTPException(503, "Model trained nahi hai: pehle `python train.py` chalao")
        _pred = FaultPredictor(DEFAULT_MODEL)
    return _pred


class WaveformIn(BaseModel):
    time: List[float]
    va: List[float]; vb: List[float]; vc: List[float]
    ia: List[float]; ib: List[float]; ic: List[float]
    trip: Optional[List[float]] = None


@router.get("/status")
def status():
    if not DEFAULT_MODEL.exists():
        return {"model_loaded": False}
    p = _get()
    return {"model_loaded": True, "classes": p.classes, **p.meta}


@router.post("/predict")
def predict(w: WaveformIn):
    n = len(w.time)
    trip = w.trip if w.trip is not None else [0.0] * n
    X = np.column_stack([w.va, w.vb, w.vc, w.ia, w.ib, w.ic, trip])
    try:
        return _get().predict_run(np.array(w.time), X)
    except ValueError as e:
        raise HTTPException(422, str(e))

ML_STORE = {}


@router.get("/run/{run_id}")
def ml_for_run(run_id: str):
    if run_id not in ML_STORE:
        raise HTTPException(404, "Is run ke liye ML prediction available nahi hai")
    return ML_STORE[run_id]
