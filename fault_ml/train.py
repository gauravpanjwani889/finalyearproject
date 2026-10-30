#!/usr/bin/env python
"""Dataset directory se fault classifier (+ fault-resistance estimator) train karta hai.

    python train.py --data data/simulink              # asli Simulink data
    python train.py --data data/synthetic_smoke       # sirf pipeline test

Evaluation GroupKFold se hota hai: group = operating condition (cond_id). Yaani test folds me aisi
conditions aati hain jo training me kabhi nahi dikhi -> accuracy inflate nahi hoti.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix, r2_score, mean_absolute_error
from sklearn.model_selection import GroupKFold, cross_val_predict
import ml_config as C
from ml_features import extract
from ml_signals import FS


def build_features(data_dir: Path):
    cache = data_dir / "features_cache.npz"
    files = sorted(data_dir.glob("run_*.npz"))
    if not files:
        raise SystemExit(f"{data_dir} me koi run_*.npz nahi mila")
    if cache.exists():
        z = np.load(cache, allow_pickle=True)
        if int(z["n_files"]) == len(files):
            print(f"features cache use ho raha hai ({len(files)} runs)")
            return {k: z[k] for k in z.files}
    rows = dict(F=[], y=[], g=[], rf=[], start=[], onset=[], detected=[], synthetic=[])
    names, skipped = None, 0
    for i, fp in enumerate(files):
        z = np.load(fp, allow_pickle=True)
        try:
            f, names, m = extract(z["X"].astype(float))
        except Exception as e:
            skipped += 1; print("skip", fp.name, e); continue
        p = json.loads(str(z["params"]))
        rows["F"].append(f); rows["y"].append(str(z["label"])); rows["g"].append(p["cond_id"])
        rows["rf"].append(p.get("rf", np.nan)); rows["start"].append(p.get("start", np.nan))
        rows["onset"].append(m["onset_time"]); rows["detected"].append(m["detected"])
        rows["synthetic"].append(bool(z["synthetic"]))
        if (i + 1) % 100 == 0: print(f"  features {i+1}/{len(files)}")
    out = {k: np.array(v) for k, v in rows.items()}
    out["names"] = np.array(names); out["n_files"] = len(files)
    np.savez_compressed(cache, **out)
    print(f"{len(rows['y'])} runs ok, {skipped} skipped")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(C.ROOT / "data" / "simulink"))
    ap.add_argument("--out", default=str(C.ROOT / "models"))
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    data, out = Path(a.data), Path(a.out); out.mkdir(parents=True, exist_ok=True)

    D = build_features(data)
    F, y, g = D["F"], D["y"], D["g"]
    names = [str(n) for n in D["names"]]
    synthetic = bool(np.all(D["synthetic"]))
    classes = [c for c in C.FAULT_NAMES if c in set(y)]
    n_groups = len(set(g)); folds = min(a.folds, n_groups)
    print(f"{len(y)} runs, {len(classes)} classes, {n_groups} conditions -> GroupKFold({folds})"
          + ("   [SYNTHETIC DATA - sirf pipeline test]" if synthetic else ""))
    if synthetic:
        print("!!! Ye synthetic data hai: accuracy ka koi scientific matlab nahi hai !!!")

    cv = GroupKFold(n_splits=folds)
    cands = {
        "RandomForest": RandomForestClassifier(500, n_jobs=-1, random_state=a.seed, class_weight="balanced"),
        "ExtraTrees": ExtraTreesClassifier(500, n_jobs=-1, random_state=a.seed, class_weight="balanced"),
        "HistGB": HistGradientBoostingClassifier(random_state=a.seed, max_iter=300, learning_rate=0.08),
    }
    scores, preds = {}, {}
    for n, m in cands.items():
        p = cross_val_predict(m, F, y, groups=g, cv=cv)
        scores[n] = {"accuracy": accuracy_score(y, p), "macro_f1": f1_score(y, p, average="macro")}
        preds[n] = p
        print(f"  {n:13s} acc {scores[n]['accuracy']:.3f}  macroF1 {scores[n]['macro_f1']:.3f}")
    best = max(scores, key=lambda k: scores[k]["macro_f1"])
    print("best:", best)
    yp = preds[best]

    # ---- report
    rep = classification_report(y, yp, labels=classes, digits=3)
    cm = confusion_matrix(y, yp, labels=classes)
    lines = [f"Model: {best}   data: {data}   synthetic={synthetic}", rep, "Confusion matrix (rows=true, cols=pred):",
             "       " + " ".join(f"{c:>5s}" for c in classes)]
    lines += [f"{c:>6s} " + " ".join(f"{v:5d}" for v in row) for c, row in zip(classes, cm)]
    rf = D["rf"].astype(float)
    fault = y != "NORMAL"
    bins = [0, 0.1, 1, 3, 10, 1e9]
    lines.append("\nAccuracy by fault resistance (sirf fault runs):")
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = fault & (rf >= lo) & (rf < hi)
        if m.sum(): lines.append(f"  Rf {lo:g}-{hi:g} ohm: n={m.sum():4d}  acc={np.mean(yp[m]==y[m]):.3f}")
    det = D["detected"].astype(bool); st = D["start"].astype(float); on = D["onset"].astype(float)
    lines.append("\nOnset detector (ML, relay se independent):")
    lines.append(f"  missed faults : {int(np.sum(fault & ~det))} / {int(fault.sum())}")
    lines.append(f"  false alarms  : {int(np.sum(~fault & det))} / {int((~fault).sum())} NORMAL runs")
    ok = fault & det
    if ok.sum():
        lat = (on[ok] - st[ok]) * 1000
        lines.append(f"  detection latency: median {np.median(lat):.2f} ms, 95th pct {np.percentile(lat,95):.2f} ms")

    # ---- Rf regressor (fault runs only)
    fm = fault & np.isfinite(rf)
    reg = RandomForestRegressor(400, n_jobs=-1, random_state=a.seed)
    lr = np.log10(rf[fm])
    pr = cross_val_predict(reg, F[fm], lr, groups=g[fm], cv=GroupKFold(n_splits=min(folds, len(set(g[fm])))))
    lines.append(f"\nFault resistance estimator (log10 Rf): R2={r2_score(lr, pr):.3f}  MAE={mean_absolute_error(lr, pr):.3f} decades")
    reg.fit(F[fm], lr)

    final = cands[best].fit(F, y)
    bundle = {"model": final, "rf_model": reg, "feature_names": names, "classes": list(final.classes_),
              "meta": {"trained_on": "synthetic" if synthetic else "simulink", "n_runs": int(len(y)),
                       "n_conditions": int(n_groups), "algorithm": best, "cv": scores,
                       "cv_macro_f1": scores[best]["macro_f1"], "cv_accuracy": scores[best]["accuracy"],
                       "rf_cv_r2": float(r2_score(lr, pr))}}
    joblib.dump(bundle, out / "fault_model.joblib")
    (out / "report.txt").write_text("\n".join(lines))
    print("\n".join(lines))

    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7.5, 6.5))
        cmn = cm / np.maximum(cm.sum(1, keepdims=True), 1)
        im = ax.imshow(cmn, cmap="Blues", vmin=0, vmax=1)
        ax.set_xticks(range(len(classes)), classes, rotation=45); ax.set_yticks(range(len(classes)), classes)
        for i in range(len(classes)):
            for j in range(len(classes)):
                if cm[i, j]: ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=8,
                                     color="white" if cmn[i, j] > .5 else "black")
        ax.set_xlabel("Predicted"); ax.set_ylabel("True")
        ax.set_title(f"{best} - grouped CV" + (" (SYNTHETIC)" if synthetic else ""))
        fig.colorbar(im); fig.tight_layout(); fig.savefig(out / "confusion_matrix.png", dpi=130)
    except Exception as e:
        print("plot skip:", e)
    print(f"\nsaved: {out/'fault_model.joblib'}, report.txt, confusion_matrix.png")


if __name__ == "__main__":
    main()
