import json, urllib.request

BASE = "http://127.0.0.1:8000/api"

def post(path, body, timeout=600):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

for ft, rf in [("AG", 0.5), ("AB", 0.5), ("NORMAL", 1.0)]:
    print(f"\n=== Simulation: {ft}, Rf={rf} (30-60 sec lagega) ===")
    sim = post("/simulation/run", {"fault_type": ft, "fault_resistance": rf,
                                   "include_full_waveform": True})
    w = sim.get("waveforms", sim)
    print("samples:", len(w["time"]))
    body = {k: w[k] for k in ("time", "va", "vb", "vc", "ia", "ib", "ic")}
    body["trip"] = w.get("trip")
    pred = post("/ml/predict", body)
    print("TRUE     :", ft, "| Rf =", rf)
    print("ML SAYS  :", json.dumps(pred)[:600])
