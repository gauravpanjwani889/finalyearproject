#!/usr/bin/env python
"""Simulink (main_model.slx) se labelled fault dataset generate karta hai.

Chalane ke liye MATLAB R2025a + `matlabengine` chahiye (Shreeya ke setup wala hi environment).

    python generate_dataset.py --dry-run                 # plan dekho, MATLAB nahi chalega
    python generate_dataset.py --check                   # 2 run: reference AG run se compare (pehle ye chalao!)
    python generate_dataset.py --n-conditions 40         # full dataset (12*40 = 480 runs)
    python generate_dataset.py --shard 0/3  (aur 1/3, 2/3 alag terminals me)   # parallel MATLAB sessions

Safe: model file kabhi save nahi hoti; har run ke baad saare parameters original values pe restore hote hain.
Resumable: jo run file pehle se hai wo skip hoti hai.
"""
from __future__ import annotations
import argparse, json, sys, time, traceback
from pathlib import Path
import numpy as np
import ml_config as C
from ml_signals import to_uniform, TS, CH


# ------------------------------------------------------------------ plan
def loguniform(rng, lo, hi):
    return float(np.exp(rng.uniform(np.log(lo), np.log(hi))))


def make_plan(n_conditions: int, seed: int, vary: bool, stop_time: float):
    rng = np.random.default_rng(seed)
    plan = []
    for c in range(n_conditions):
        if c == 0 or not vary:
            cond = {"line_r": 0.001, "line_l": 1e-3, "vf": 1.0, "pm": 1.0}      # nominal model values
        else:
            cond = {k: float(rng.uniform(*v)) for k, v in C.COND_RANGES.items()}
        for fault in C.FAULT_NAMES:
            start = float(rng.uniform(*C.START_RANGE))
            plan.append({
                "cond_id": c, "fault": fault, "cond": cond,
                "rf": loguniform(rng, *C.RF_RANGE), "rg": loguniform(rng, *C.RG_RANGE),
                "start": round(start, 5), "stop": C.FAULT_STOP, "stop_time": stop_time,
            })
    return plan


def run_name(p):
    return f"run_c{p['cond_id']:03d}_{p['fault']}.npz"


# ------------------------------------------------------------------ MATLAB helpers
class Sim:
    def __init__(self, model_path: Path):
        import matlab.engine
        print("MATLAB engine start ho raha hai (~30 s)...", flush=True)
        self.eng = matlab.engine.start_matlab()
        self.eng.addpath(str(model_path.parent), nargout=0)
        self.eng.load_system(str(model_path), nargout=0)
        self.switch_param = self._find_switch_param()
        self.params = self._param_list()
        self.originals = {(b, n): self.eng.get_param(b, n) for b, n in self.params}
        print("Original params snapshot:", {f"{b.split('/')[-1]}.{n}": v for (b, n), v in self.originals.items()})

    def _find_switch_param(self):
        names = list(self.eng.eval(f"fieldnames(get_param('{C.BLK_FAULT}','DialogParameters'))", nargout=1))
        for cand in ("SwitchTimes", "TransitionTimes", "SwitchingTimes"):
            if cand in names:
                return cand
        raise RuntimeError(f"Fault block me switching-time parameter nahi mila. Available: {names}")

    def _param_list(self):
        fb = C.BLK_FAULT
        return [(fb, n) for n in ("FaultA", "FaultB", "FaultC", "GroundFault", "FaultResistance",
                                  "GroundResistance", self.switch_param)] + [
            (C.BLK_SERIES, "Resistance"), (C.BLK_SERIES, "Inductance"),
            (C.BLK_PM, "Value"), (C.BLK_VF, "Value"), (C.MODEL, "StopTime")]

    def set(self, blk, name, val):
        self.eng.set_param(blk, name, str(val), nargout=0)

    def apply(self, p):
        for k, v in C.fault_flags(p["fault"]).items():
            self.set(C.BLK_FAULT, k, v)
        self.set(C.BLK_FAULT, "FaultResistance", f"{p['rf']:.6g}")
        self.set(C.BLK_FAULT, "GroundResistance", f"{p['rg']:.6g}")
        self.set(C.BLK_FAULT, self.switch_param, f"[{p['start']:.6f} {p['stop']:.6f}]")
        self.set(C.BLK_SERIES, "Resistance", f"{p['cond']['line_r']:.6g}")
        self.set(C.BLK_SERIES, "Inductance", f"{p['cond']['line_l']:.6g}")
        self.set(C.BLK_PM, "Value", f"{p['cond']['pm']:.6g}")
        self.set(C.BLK_VF, "Value", f"{p['cond']['vf']:.6g}")
        self.set(C.MODEL, "StopTime", f"{p['stop_time']:.6g}")
        # readback verify
        rb = self.eng.get_param(C.BLK_FAULT, "FaultA"), self.eng.get_param(C.BLK_FAULT, "GroundFault")
        exp = C.fault_flags(p["fault"])
        if (rb[0], rb[1]) != (exp["FaultA"], exp["GroundFault"]):
            raise RuntimeError(f"Readback mismatch: {rb} != {exp}")

    def restore(self):
        for (b, n), v in self.originals.items():
            self.eng.set_param(b, n, v, nargout=0)

    def run(self):
        e = self.eng
        e.eval("clear ScopeData ml_t ml_v;", nargout=0)
        e.eval(f"sim('{C.MODEL}');", nargout=0)
        e.eval("ml_t = ScopeData.time; ml_v = ScopeData.signals.values;", nargout=0)
        t = np.array(e.workspace["ml_t"], dtype=float).ravel()
        X = np.array(e.workspace["ml_v"], dtype=float)
        e.eval("clear ScopeData ml_t ml_v;", nargout=0)
        if X.ndim != 2 or X.shape[1] != 9 or len(t) != len(X):
            raise RuntimeError(f"Unexpected ScopeData shape {X.shape}, t {t.shape}")
        if not np.all(np.isfinite(X)):
            raise RuntimeError("ScopeData me NaN/Inf")
        return t, X

    def close(self):
        try:
            self.restore()
        finally:
            self.eng.bdclose(C.MODEL, nargout=0)   # bina save kiye close
            self.eng.quit()


# ------------------------------------------------------------------ check
def reference_stats(X, t):
    ia = X[:, CH["ia"]]
    def rms(a, b):
        m = (t >= a) & (t < b); return float(np.sqrt(np.mean(ia[m] ** 2)))
    trip = X[:, CH["trip"]]
    return {"peak_ia": float(np.abs(ia).max()), "rms_pre": rms(0.10, 0.15), "rms_fault": rms(0.25, 0.35),
            "t_trip": float(t[np.argmax(trip > 0.5)])}


def do_check(sim: Sim):
    ref = np.load(C.ROOT / "reference" / "AG_reference_run.npz")
    rs = reference_stats(ref["X"], ref["t"])
    print("Reference (Shreeya ka out.mat, AG):", rs)
    best = None
    for rf in (1.0, 0.001):
        p = {"cond_id": 0, "fault": "AG", "cond": {"line_r": 0.001, "line_l": 1e-3, "vf": 1.0, "pm": 1.0},
             "rf": rf, "rg": 0.01, "start": 0.2, "stop": 0.4, "stop_time": 0.45}
        try:
            sim.apply(p); t, X = sim.run()
        finally:
            sim.restore()
        s = reference_stats(X, t)
        err = max(abs(s[k] / rs[k] - 1) for k in ("peak_ia", "rms_pre", "rms_fault"))
        print(f"  AG Rf={rf}: {s}  max rel err {err:.1%}")
        if best is None or err < best[1]:
            best = (rf, err)
    ok = best[1] < 0.05
    print(("PASS" if ok else "FAIL"), f"- closest Rf={best[0]} (err {best[1]:.1%}).",
          "Model Shreeya ke reference jaisa behave kar raha hai." if ok else
          "Model/params reference se match nahi kar rahe - batch chalane se pehle Shreeya se confirm karo.")
    return ok


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(C.ROOT / "data" / "simulink"))
    ap.add_argument("--model", default=str(C.DEFAULT_MODEL))
    ap.add_argument("--n-conditions", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--stop-time", type=float, default=C.STOP_TIME)
    ap.add_argument("--fixed-conditions", action="store_true", help="line/generator params vary na karo")
    ap.add_argument("--shard", default="0/1", help="i/N: plan ka i-th hissa (parallel terminals)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    plan = make_plan(a.n_conditions, a.seed, not a.fixed_conditions, a.stop_time)
    (out / "plan.json").write_text(json.dumps(plan, indent=1))
    i, n = map(int, a.shard.split("/"))
    todo = [p for j, p in enumerate(plan) if j % n == i and not (out / run_name(p)).exists()]
    print(f"Plan: {len(plan)} runs total, is shard me {sum(1 for j in range(len(plan)) if j % n == i)}, baaki {len(todo)}")
    if a.dry_run:
        rf = np.array([p["rf"] for p in plan]); print(f"Rf range {rf.min():.3g}-{rf.max():.3g} ohm; classes {len(C.FAULT_NAMES)}; "
              f"conditions {a.n_conditions}; stop_time {a.stop_time}s. Plan saved to {out/'plan.json'}")
        return
    model = Path(a.model)
    if not model.exists():
        sys.exit(f"Model nahi mila: {model}  (--model se path do)")
    sim = Sim(model)
    try:
        if a.check:
            sys.exit(0 if do_check(sim) else 1)
        fails = 0; t0 = time.time()
        for r, p in enumerate(todo, 1):
            try:
                sim.apply(p); t, X = sim.run()
                tu, Xu = to_uniform(t, X, t_end=p["stop_time"])
                np.savez_compressed(out / run_name(p), X=Xu.astype(np.float32), label=p["fault"],
                                    params=json.dumps(p), synthetic=False)
                status = "ok"
            except Exception as e:                      # ek run fail ho to baaki chalte rahein
                fails += 1; status = f"FAIL {e}"
                with open(out / "failures.log", "a") as fh:
                    fh.write(json.dumps(p) + "\n" + traceback.format_exc() + "\n")
            finally:
                sim.restore()
            el = time.time() - t0
            print(f"[{r}/{len(todo)}] c{p['cond_id']:03d} {p['fault']:6s} Rf={p['rf']:.3g} start={p['start']} -> {status}  "
                  f"(ETA {el/r*(len(todo)-r)/60:.0f} min)", flush=True)
        print(f"Done. failures: {fails}. Files in {out}")
    finally:
        sim.close()


if __name__ == "__main__":
    main()
