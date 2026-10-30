#!/usr/bin/env python
"""SYNTHETIC (nakli) fault data - sirf pipeline test karne ke liye (train/predict/API chal rahe hain ya nahi).

!!! Isse nikli accuracy ka koi matlab nahi. Asli results sirf generate_dataset.py (Simulink) ke data se aayenge. !!!
Files `synthetic=True` flag ke saath save hoti hain; train.py model ko 'synthetic' mark karta hai aur API warning deti hai.
"""
import argparse, json
from pathlib import Path
import numpy as np
import ml_config as C

FS = 20000.0


def make_run(rng, fault, cond, rf, rg, start, stop=0.40, n=9001):
    t = np.arange(n) / FS
    w = 2 * np.pi * 50
    Vp = np.sqrt(2) * cond["vrms"]; Ip = np.sqrt(2) * cond["irms"]; phi = np.deg2rad(cond["pf_deg"])
    ramp = 1 - np.exp(-t / 0.03)
    # L-L voltages (Vab, Vbc, Vca) aur phase currents
    th_v = np.deg2rad([30, -90, 150]); th_i = np.deg2rad([0, -120, 120])
    V = np.stack([Vp * ramp * np.cos(w * t + th) for th in th_v], 1)
    I = np.stack([Ip * ramp * np.cos(w * t - phi + th) for th in th_i], 1)
    on = ((t >= start) & (t < stop)).astype(float)
    if fault != "NORMAL":
        letters = set(fault.replace("G", "")) if fault != "ABCG" else set("ABC")
        idx = sorted("ABC".index(c) for c in letters)
        s = 0.9 / (1 + rf / 1.5)                               # voltage sag depth
        Ik = 700.0 / (rf + 0.5) * rng.uniform(0.85, 1.15)      # fault current peak
        phif = np.deg2rad(75); dcdec = np.exp(-np.clip(t - start, 0, None) / 0.03)
        gnd = fault.endswith("G")
        if len(idx) == 2 and not gnd:                           # line-to-line: opposite currents
            a, b = idx
            sh = th_i[a]
            core = Ik * 0.87 * (np.cos(w * t - phif + sh) - np.cos(sh - phif) * dcdec)
            I[:, a] += on * core; I[:, b] -= on * core
        else:
            scale = {1: 1.0, 2: 0.85, 3: 0.95}[len(idx)]
            for p in idx:
                core = Ik * scale * (np.cos(w * t - phif + th_i[p] + rng.normal(0, .05)) - np.cos(th_i[p] - phif) * dcdec)
                I[:, p] += on * core
        cnt = np.array([[(p in idx) + (q in idx) for p, q in ((0, 1), (1, 2), (2, 0))]]).ravel()
        sag = 1 - s * cnt / 2
        V = V * (1 - on[:, None] * (1 - sag[None, :]))
    # PWM-ish ripple + noise
    ripple = 0.08 * np.sign(np.sin(2 * np.pi * 2000 * t))[:, None]
    V = V + Vp * ripple * rng.uniform(0.5, 1.0) * np.sin(w * t)[:, None] + rng.normal(0, 3, V.shape)
    I = I + rng.normal(0, 0.15, I.shape)
    trip = ((t >= start + 0.0005) & (t < stop) & (fault != "NORMAL")).astype(float)
    X = np.column_stack([V, I, trip, np.zeros(n), np.zeros(n)])
    return X.astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(C.ROOT / "data" / "synthetic_smoke"))
    ap.add_argument("--n-conditions", type=int, default=20)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    for c in range(a.n_conditions):
        cond = {"vrms": rng.uniform(330, 370), "irms": rng.uniform(8, 14), "pf_deg": rng.uniform(5, 25)}
        for f in C.FAULT_NAMES:
            rf = float(np.exp(rng.uniform(np.log(C.RF_RANGE[0]), np.log(C.RF_RANGE[1]))))
            start = float(rng.uniform(*C.START_RANGE))
            X = make_run(rng, f, cond, rf, 0.1, start)
            p = {"cond_id": c, "fault": f, "rf": rf, "start": start, "cond": cond}
            np.savez_compressed(out / f"run_c{c:03d}_{f}.npz", X=X, label=f, params=json.dumps(p), synthetic=True)
    print("synthetic smoke data ->", out, a.n_conditions * len(C.FAULT_NAMES), "runs")


if __name__ == "__main__":
    main()
