"""Common helpers: uniform resampling aur fault onset detection."""
from __future__ import annotations
import numpy as np

FS = 20000.0          # 50 us solver step
TS = 1.0 / FS
N0 = 400              # samples per 50 Hz cycle
CH = {"va": 0, "vb": 1, "vc": 2, "ia": 3, "ib": 4, "ic": 5, "trip": 6, "vmag": 7, "imag": 8}


def to_uniform(t: np.ndarray, X: np.ndarray, t_end: float | None = None):
    """Discrete solver kabhi kabhi duplicate timestamps deta hai (zero-step events).
    Duplicates me last value rakh ke 50 us uniform grid pe interpolate karta hai.
    Trip channel (binary) ko previous-sample (zero-order hold) se resample karta hai."""
    t = np.asarray(t, float).ravel()
    X = np.asarray(X, float)
    # last occurrence of each timestamp
    rev_t = t[::-1]
    _, idx_rev = np.unique(rev_t, return_index=True)
    keep = np.sort(len(t) - 1 - idx_rev)
    t, X = t[keep], X[keep]
    t_end = t[-1] if t_end is None else t_end
    n = int(round(t_end / TS)) + 1
    tu = np.arange(n) * TS
    Xu = np.empty((n, X.shape[1]))
    for c in range(X.shape[1]):
        if c == CH["trip"]:
            j = np.clip(np.searchsorted(t, tu + 1e-12, side="right") - 1, 0, len(t) - 1)
            Xu[:, c] = X[j, c]
        else:
            Xu[:, c] = np.interp(tu, t, X[:, c])
    return tu, Xu


def detect_onset(X: np.ndarray, scan_from: float = 0.16, k_sigma: float = 6.0,
                 min_abs: float = 3.0):
    """Relay se independent fault-onset detector (one-cycle-difference method).

    d[k] = max_phase |i[k] - i[k-N0]|.  Steady periodic signal (PWM ripple dahil, kyunki 20 ms = 40 carrier
    periods) me d ~ 0 rehta hai; fault aate hi d achanak badhta hai.
    Returns sample index of onset, ya None agar koi disturbance nahi mila (NORMAL).
    """
    I = X[:, [CH["ia"], CH["ib"], CH["ic"]]]
    n = len(I)
    d = np.zeros(n)
    d[N0:] = np.max(np.abs(I[N0:] - I[:-N0]), axis=1)
    k0 = int(scan_from * FS)
    base_lo, base_hi = max(N0, k0 - 3 * N0 // 4), k0       # 15 ms pehle ka quiet window
    base = d[base_lo:base_hi]
    thr = max(min_abs, k_sigma * (base.max() if len(base) else 0.0))
    # fault current peak load peak se kaafi upar hona chahiye
    hit = np.where(d[k0:] > thr)[0]
    return None if len(hit) == 0 else int(k0 + hit[0])
