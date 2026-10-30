"""Feature extraction: ek simulation run (uniform 20 kHz grid) -> fixed-length feature vector.

Window design (onset = detect_onset() ya DEFAULT_ONSET agar koi disturbance na mile):
    pre  = [k0 - 1 cycle, k0)       fault se pehle ka 1 cycle
    post = [k0, k0 + 2 cycles)      fault ke baad ke 2 cycles (40 ms)
Trip signal ko classifier feature NAHI banaya gaya (taaki ML relay se independent rahe aur leak na ho).

NOTE: Va/Vb/Vc channels *line-to-line* voltages hain (Vab, Vbc, Vca), isliye voltage se zero-sequence
nahi milta; zero-sequence information currents (I0 = (Ia+Ib+Ic)/3) se aati hai.
"""
from __future__ import annotations
import numpy as np
from ml_signals import FS, N0, CH, detect_onset

DEFAULT_ONSET = 0.30      # jab koi fault detect na ho (NORMAL) tab is time ki window li jaati hai
POST_CYCLES = 2
EPS = 1e-9
_A = np.exp(2j * np.pi / 3)
_CHN = ["va", "vb", "vc", "ia", "ib", "ic"]
_IDX = [CH[c] for c in _CHN]


def _phasor(x: np.ndarray, k_start: int) -> complex:
    """50 Hz phasor (peak amplitude) of whole-cycle window; absolute-k reference -> windows comparable."""
    k = np.arange(k_start, k_start + len(x))
    return 2.0 / len(x) * np.sum(x * np.exp(-2j * np.pi * k / N0))


def _seq(pa, pb, pc):
    i0 = (pa + pb + pc) / 3
    i1 = (pa + _A * pb + _A ** 2 * pc) / 3
    i2 = (pa + _A ** 2 * pb + _A * pc) / 3
    return i0, i1, i2


def _rms(x):
    return float(np.sqrt(np.mean(x ** 2)))


def _cos(p, q):
    return float(np.real(p * np.conj(q)) / (abs(p) * abs(q) + EPS))


def window_start(X: np.ndarray):
    """Returns (k0, detected_bool). X uniform-grid array (N, 9)."""
    k = detect_onset(X)
    if k is None:
        return int(DEFAULT_ONSET * FS), False
    return k, True


def extract(X: np.ndarray, k0: int | None = None):
    """X: (N, 9) uniform grid. Returns (feature_vector, names, meta)."""
    detected = True
    if k0 is None:
        k0, detected = window_start(X)
    npost = POST_CYCLES * N0
    if k0 - N0 < 0 or k0 + npost > len(X):
        raise ValueError(f"Window out of range: onset idx {k0}, run length {len(X)}")
    pre = X[k0 - N0:k0][:, _IDX]
    post = X[k0:k0 + npost][:, _IDX]
    early = X[k0:k0 + N0 // 4][:, _IDX]            # pehle 5 ms

    f, names = [], []

    def add(n, v):
        names.append(n); f.append(float(v))

    ph_pre, ph_post = [], []
    for j, c in enumerate(_CHN):
        rp, rq = _rms(pre[:, j]), _rms(post[:, j])
        pp = _phasor(pre[:, j], k0 - N0)
        pq = _phasor(post[:, j], k0)
        ph_pre.append(pp); ph_post.append(pq)
        add(f"{c}_rms_ratio", rq / (rp + EPS))
        add(f"{c}_early_ratio", _rms(early[:, j]) / (rp + EPS))
        add(f"{c}_crest", np.max(np.abs(post[:, j])) / (rq + EPS))
        add(f"{c}_dc", np.mean(post[:, j]) / (rq + EPS))
        add(f"{c}_fund_frac", abs(pq) / (np.sqrt(2) * rq + EPS))      # 1 = pure 50 Hz, kam = harmonics
        add(f"{c}_dphasor", abs(pq - pp) / (abs(pp) + EPS))           # fundamental me badlav (prefault ke relative)

    iv = ph_post[3:]; ip = ph_pre[3:]
    vv = ph_post[:3]; vp = ph_pre[:3]

    # current shares (kaunsi phase dominate kar rahi hai)
    mags = np.array([abs(p) for p in iv])
    for j, c in enumerate("abc"):
        add(f"i{c}_share", mags[j] / (mags.sum() + EPS))
    ratios = np.array([abs(q) / (abs(p) + EPS) for q, p in zip(iv, ip)])
    s = np.sort(ratios)
    add("i_ratio_min", s[0]); add("i_ratio_med", s[1]); add("i_ratio_max", s[2])
    add("i_ratio_maxmin", s[2] / (s[0] + EPS))

    # sequence components of currents (post, and delta vs pre)
    i0, i1, i2 = _seq(*iv)
    p0, p1, p2 = _seq(*ip)
    add("I0_over_I1", abs(i0) / (abs(i1) + EPS))
    add("I2_over_I1", abs(i2) / (abs(i1) + EPS))
    add("I1_ratio", abs(i1) / (abs(p1) + EPS))
    add("I0_over_I1pre", abs(i0) / (abs(p1) + EPS))
    add("I2_over_I1pre", abs(i2) / (abs(p1) + EPS))
    d = [q - p for q, p in zip(iv, ip)]
    for j, c in enumerate("abc"):
        add(f"dI{c}_over_I1pre", abs(d[j]) / (abs(p1) + EPS))
    add("cos_dIa_dIb", _cos(d[0], d[1])); add("cos_dIb_dIc", _cos(d[1], d[2])); add("cos_dIc_dIa", _cos(d[2], d[0]))
    d0, d1_, d2 = _seq(*d)
    add("dI0_over_dI1", abs(d0) / (abs(d1_) + EPS))
    add("dI2_over_dI1", abs(d2) / (abs(d1_) + EPS))

    # instantaneous zero-sequence current rms
    i0_inst = post[:, 3:].sum(axis=1) / 3
    add("i0_inst_rms_over_pre", _rms(i0_inst) / (np.mean([_rms(pre[:, 3 + j]) for j in range(3)]) + EPS))

    # voltages (line-to-line): sequence + sag
    v0, v1, v2 = _seq(*vv)
    q0, q1, q2 = _seq(*vp)
    add("V1_ratio", abs(v1) / (abs(q1) + EPS))
    add("V2_over_V1", abs(v2) / (abs(v1) + EPS))
    add("V2_over_V1pre", abs(v2) / (abs(q1) + EPS))
    vr = np.array([abs(q) / (abs(p) + EPS) for q, p in zip(vv, vp)])
    s = np.sort(vr)
    add("v_ratio_min", s[0]); add("v_ratio_max", s[2]); add("v_ratio_spread", s[2] - s[0])

    meta = {"k0": k0, "onset_time": k0 / FS, "detected": detected}
    return np.array(f), names, meta
