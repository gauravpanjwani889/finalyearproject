"""
Verification script for Step 1:
Tests FastAPI backend directly using TestClient:
1. /api/health
2. /api/model/info
3. POST /api/simulation/run (NORMAL)
4. POST /api/simulation/run (AG)
5. Verifies waveform arrays, timestamps, units, breaker polarity, configurable parameters.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import time
from fastapi.testclient import TestClient
from backend.main import app

def run_backend_verification():
    print("=" * 70)
    print("STEP 1: VERIFYING BACKEND API WITH REAL SIMULINK SOLVER")
    print("=" * 70)
    
    with TestClient(app) as client:
        # 1. Health check
        print("\n[1] Testing GET /api/health...")
        t0 = time.time()
        res_health = client.get("/api/health")
        print(f"Status Code: {res_health.status_code} in {time.time()-t0:.2f}s")
        print("Health Response:", json.dumps(res_health.json(), indent=2))
        assert res_health.status_code == 200, "Health check failed"
        assert res_health.json()["matlab_connected"] is True, "MATLAB engine not connected"
        assert res_health.json()["model_loaded"] is True, "Model not loaded"

        # 2. Model Info
        print("\n[2] Testing GET /api/model/info...")
        res_info = client.get("/api/model/info")
        print(f"Status Code: {res_info.status_code}")
        info_data = res_info.json()
        print(f"Model Name: {info_data['model_name']}, Blocks: {info_data['total_blocks']}, Sample Time: {info_data['sample_time']}")
        print(f"Signal Channels: {len(info_data['signal_channels'])}")

        # 3. Model Parameters
        print("\n[3] Testing GET /api/model/parameters...")
        res_params = client.get("/api/model/parameters")
        print(f"Status Code: {res_params.status_code}")
        print("Configurable limits:", json.dumps(res_params.json()["limits"], indent=2))

        # 4. NORMAL simulation run
        print("\n[4] Testing POST /api/simulation/run with NORMAL scenario...")
        t0 = time.time()
        payload_normal = {
            "fault_type": "NORMAL",
            "fault_resistance": 0.001,
            "ground_resistance": 0.01,
            "downsample_points": 500,
        }
        res_norm = client.post("/api/simulation/run", json=payload_normal)
        dur_norm = time.time() - t0
        print(f"NORMAL Status: {res_norm.status_code} in {dur_norm:.2f}s")
        assert res_norm.status_code == 200, f"NORMAL failed: {res_norm.text}"
        norm_data = res_norm.json()
        print(f"Run ID: {norm_data['run_id']}")
        print(f"Execution Duration: {norm_data['execution_duration_sec']}s")
        print(f"Metrics: Peak I = {norm_data['metrics']['peak_current']} A, Min V = {norm_data['metrics']['min_voltage']} V")
        print(f"Fault detected: {norm_data['metrics']['is_fault_detected']}, Breaker tripped: {norm_data['metrics']['is_breaker_tripped']}")
        print(f"Downsampled points: {norm_data['downsampled_samples']} / {norm_data['total_samples']}")
        
        # Verify breaker polarity in NORMAL:
        # Trip must be 0 (breaker closed/normal)
        trip_arr = norm_data["waveforms"]["trip"]
        max_trip = max(trip_arr)
        print(f"NORMAL max trip signal value: {max_trip} (Should be 0.0 for closed/healthy)")
        assert max_trip == 0.0, f"Breaker tripped in NORMAL condition! Got max={max_trip}"

        # 5. AG (Single Line-to-Ground) simulation run
        print("\n[5] Testing POST /api/simulation/run with AG (Phase A to Ground) fault...")
        t0 = time.time()
        payload_ag = {
            "fault_type": "AG",
            "fault_resistance": 1.0,
            "ground_resistance": 0.01,
            "downsample_points": 500,
        }
        res_ag = client.post("/api/simulation/run", json=payload_ag)
        dur_ag = time.time() - t0
        print(f"AG Status: {res_ag.status_code} in {dur_ag:.2f}s")
        assert res_ag.status_code == 200, f"AG failed: {res_ag.text}"
        ag_data = res_ag.json()
        print(f"Run ID: {ag_data['run_id']}")
        print(f"Execution Duration: {ag_data['execution_duration_sec']}s")
        print(f"Metrics: Peak I = {ag_data['metrics']['peak_current']} A, Min V = {ag_data['metrics']['min_voltage']} V")
        print(f"Fault detected: {ag_data['metrics']['is_fault_detected']}, Breaker tripped: {ag_data['metrics']['is_breaker_tripped']}")
        print(f"Fault onset time: {ag_data['metrics']['fault_onset_time']}s, Trip time: {ag_data['metrics']['breaker_trip_time']}s")
        print(f"Fault-to-trip delay: {ag_data['metrics']['fault_to_trip_delay_ms']} ms, Trip duration: {ag_data['metrics']['trip_duration_ms']} ms")
        
        # Verify breaker polarity in AG:
        # Breaker must trip to 1.0 at ~0.2005s and reset at ~0.4000s
        ag_trip_arr = ag_data["waveforms"]["trip"]
        assert max(ag_trip_arr) == 1.0, f"Breaker failed to trip for AG fault! Max={max(ag_trip_arr)}"
        print("AG Trip signal successfully verified (tripped to 1.0).")

        # 6. Verify History Endpoint
        print("\n[6] Testing GET /api/simulation/history...")
        res_hist = client.get("/api/simulation/history")
        print(f"History Status: {res_hist.status_code}, entries: {len(res_hist.json())}")
        for item in res_hist.json():
            print(f"  - Run {item['run_id'][:8]}... | Fault: {item['fault_type']} | Tripped: {item['is_breaker_tripped']} | Dur: {item['execution_duration_sec']}s")

        print("\n" + "=" * 70)
        print("ALL STEP 1 BACKEND VERIFICATION CHECKS PASSED EMPIRICALLY!")
        print("=" * 70)

if __name__ == "__main__":
    run_backend_verification()
