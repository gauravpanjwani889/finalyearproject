"""Simulink `out.mat` (v7.3 / HDF5) se ScopeData nikalne ki utility.

Simulink.SimulationOutput object MCOS format me hota hai, isliye scipy.io.loadmat kaam nahi karta.
Logged signals `#sigstream#` me raw float64 bytes ki tarah stored hote hain. ScopeData wala stream
wo hai jiska sampleSize = 9 channels * 8 bytes = 72 bytes.
"""
from __future__ import annotations
import numpy as np

CHANNELS = ["va", "vb", "vc", "ia", "ib", "ic", "trip", "vmag", "imag"]


def load_out_mat(path: str):
    """Returns (t, X): t shape (N,), X shape (N, 9) in CHANNELS order."""
    import h5py
    with h5py.File(path, "r") as f:
        streams = f["#sigstream#"]
        keys = [k for k in streams.keys() if k.isdigit()]
        data = time = None
        for k in sorted(keys, key=int):
            g = streams[k]
            ss = int(g["#sampleSize#"][0])
            n = int(g["#length#"][0])
            raw = np.frombuffer(g["#data#"][()].tobytes(), dtype="<f8")
            if ss == 8 * len(CHANNELS) and data is None:
                data = raw[: n * len(CHANNELS)].reshape(n, len(CHANNELS))
            elif ss == 8 and time is None:
                x = raw[:n]
                if x[0] == 0.0 and np.all(np.diff(x) >= 0) and x[-1] > 0.05:
                    time = x
        if data is None or time is None:
            raise ValueError("ScopeData (9-channel stream) ya time vector nahi mila")
        return time, data


if __name__ == "__main__":
    import sys
    t, X = load_out_mat(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else "reference/run.npz"
    np.savez_compressed(out, t=t, X=X, channels=np.array(CHANNELS))
    print("saved", out, t.shape, X.shape)
