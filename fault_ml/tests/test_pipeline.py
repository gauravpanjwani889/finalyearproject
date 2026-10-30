"""Pipeline tests. Chalao:  python -m pytest tests -q   (fault_ml/ folder se)
Real AG reference run (Shreeya ke out.mat se) pe features/predictor/API ka behaviour check karte hain."""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pytest
from ml_signals import to_uniform, detect_onset, FS
from ml_features import extract
import ml_config as C

REF = Path(__file__).resolve().parents[1] / "reference" / "AG_reference_run.npz"
MODEL = Path(os.environ.get("FAULT_MODEL", Path(__file__).resolve().parents[1] / "models" / "fault_model.joblib"))


@pytest.fixture(scope="module")
def ref():
    d = np.load(REF); return d["t"], d["X"]


def test_fault_flags_mapping():
    assert C.fault_flags("BCG") == {"FaultA": "off", "FaultB": "on", "FaultC": "on", "GroundFault": "on"}
    assert C.fault_flags("CA")["FaultA"] == "on" and C.fault_flags("CA")["FaultC"] == "on"
    assert C.fault_flags("ABC")["GroundFault"] == "off" and C.fault_flags("ABCG")["GroundFault"] == "on"
    assert all(v == "off" for v in C.fault_flags("NORMAL").values())


def test_uniform_grid(ref):
    tu, Xu = to_uniform(*ref)
    assert len(tu) == 20001 and np.allclose(np.diff(tu), 1 / FS)


def test_onset_detector_real_run(ref):
    _, Xu = to_uniform(*ref)
    k = detect_onset(Xu)
    assert k is not None and abs(k / FS - 0.2000) < 0.001           # asli fault 0.2000 s pe
    assert detect_onset(Xu[: int(0.19 * FS)]) is None                # healthy hisse pe false alarm nahi


def test_features_real_AG_signature(ref):
    _, Xu = to_uniform(*ref)
    f, n, _ = extract(Xu)
    g = lambda k: f[n.index(k)]
    assert np.all(np.isfinite(f))
    assert g("ia_rms_ratio") > 10 and 0.8 < g("ib_rms_ratio") < 1.2 and 0.8 < g("ic_rms_ratio") < 1.2
    assert 0.8 < g("I0_over_I1") < 1.2 and 0.8 < g("I2_over_I1") < 1.2     # SLG: I0=I1=I2
    assert g("va_rms_ratio") < 0.7 and g("vc_rms_ratio") < 0.7 and g("vb_rms_ratio") > 0.9   # Vab, Vca sag; Vbc nahi


@pytest.mark.skipif(not MODEL.exists(), reason="model trained nahi hai")
def test_predictor_and_api(ref):
    from ml_predict import FaultPredictor
    import ml_predict
    p = FaultPredictor(MODEL).predict_run(*ref)
    assert p["fault_type"] in p["probabilities"] and abs(sum(p["probabilities"].values()) - 1) < 1e-6
    assert p["onset_detected"] and p["relay_tripped"]
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import api_router
    api_router.DEFAULT_MODEL = MODEL; api_router._pred = None
    app = FastAPI(); app.include_router(api_router.router)
    c = TestClient(app)
    assert c.get("/api/ml/status").json()["model_loaded"]
    t, X = ref
    body = {"time": t.tolist(), "va": X[:, 0].tolist(), "vb": X[:, 1].tolist(), "vc": X[:, 2].tolist(),
            "ia": X[:, 3].tolist(), "ib": X[:, 4].tolist(), "ic": X[:, 5].tolist(), "trip": X[:, 6].tolist()}
    r = c.post("/api/ml/predict", json=body); assert r.status_code == 200, r.text
    assert r.json()["fault_type"] == p["fault_type"]
    # decimated (kam samples) data reject hona chahiye
    bad = {k: v[::40] for k, v in body.items()}
    assert c.post("/api/ml/predict", json=bad).status_code == 422
