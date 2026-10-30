"""Inference: ek simulation run (time + 9-channel ScopeData) -> fault type, confidence, Rf estimate."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))   # taaki backend se `fault_ml.ml_predict` import ho sake
import numpy as np
import joblib
from ml_features import extract
from ml_signals import to_uniform, FS, CH

DEFAULT_MODEL = Path(__file__).resolve().parent / "models" / "fault_model.joblib"


class FaultPredictor:
    def __init__(self, path: str | Path = DEFAULT_MODEL):
        b = joblib.load(path)
        self.model, self.rf_model = b["model"], b["rf_model"]
        self.names, self.classes, self.meta = b["feature_names"], list(b["classes"]), b["meta"]

    def predict_run(self, t, X) -> dict:
        """t: (N,) seconds, X: (N, 9) [va vb vc ia ib ic trip vmag imag] - full-resolution (20 kHz) data."""
        X = np.asarray(X, float)
        if X.ndim != 2 or X.shape[1] < 7:
            raise ValueError("X shape (N, 9) hona chahiye")
        if X.shape[1] < 9:
            X = np.column_stack([X, np.zeros((len(X), 9 - X.shape[1]))])
        t = np.asarray(t, float).ravel()
        if t[-1] < 0.40:
            raise ValueError("Run kam se kam 0.40 s ka hona chahiye (model 0.3 s tak ki window use karta hai)")
        if len(t) < 10 * 0.4 * FS / 10 * 0.5:
            raise ValueError("Data bahut downsampled hai - full 20 kHz waveform do (decimated nahi)")
        _, Xu = to_uniform(t, X)
        f, names, meta = extract(Xu)
        assert names == self.names, "feature list model se match nahi karti"
        proba = self.model.predict_proba(f[None])[0]
        order = np.argsort(proba)[::-1]
        pred = self.classes[order[0]]
        res = {
            "fault_type": pred,
            "confidence": float(proba[order[0]]),
            "top3": [{"class": self.classes[i], "probability": float(proba[i])} for i in order[:3]],
            "probabilities": {c: float(p) for c, p in zip(self.classes, proba)},
            "fault_detected": bool(pred != "NORMAL"),
            "onset_detected": bool(meta["detected"]),
            "onset_time_s": float(meta["onset_time"]) if meta["detected"] else None,
            "relay_tripped": bool(np.any(Xu[:, CH["trip"]] > 0.5)),
            "trained_on": self.meta["trained_on"],
            "model_cv_macro_f1": self.meta["cv_macro_f1"],
        }
        if pred != "NORMAL":
            res["estimated_fault_resistance_ohm"] = float(10 ** self.rf_model.predict(f[None])[0])
        if self.meta["trained_on"] == "synthetic":
            res["warning"] = "Model SYNTHETIC data pe trained hai - sirf pipeline test, asli prediction nahi."
        return res
