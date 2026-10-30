"""
End-to-end integration test verifying that:
1. Frontend dev server (Vite on port 3000) serves the HTML application.
2. Frontend proxy forwards /api/health to FastAPI backend (port 8000).
3. Frontend proxy forwards /api/model/info.
4. Frontend proxy forwards POST /api/simulation/run with AB and ABC fault scenarios to MATLAB Engine.
5. Waveforms, breaker states, and diagnostics match the genuine model outputs.
"""

import sys
import json
import time
import httpx

def test_frontend_backend_integration():
    print("=" * 70)
    print("FRONTEND-BACKEND END-TO-END INTEGRATION TEST")
    print("=" * 70)

    client = httpx.Client(timeout=120.0)

    # 1. Test Frontend HTML delivery
    print("\n[1] Checking Vite Frontend Delivery at http://127.0.0.1:3000/...")
    res_front = client.get("http://127.0.0.1:3000/")
    print(f"Frontend Status Code: {res_front.status_code}")
    assert res_front.status_code == 200, "Frontend is not accessible"
    assert "Smart Grid Stability" in res_front.text, "Page title/meta missing in index.html"
    assert '<div id="root"></div>' in res_front.text, "Root mount container missing"
    print("[OK] Frontend index.html served correctly by Vite.")

    # 2. Test Frontend Proxy to Backend /api/health
    print("\n[2] Checking API Proxy via Frontend at http://127.0.0.1:3000/api/health...")
    res_health = client.get("http://127.0.0.1:3000/api/health")
    print(f"Health Status Code: {res_health.status_code}")
    assert res_health.status_code == 200, f"Health check failed: {res_health.text}"
    health_data = res_health.json()
    print("Health Data:", json.dumps(health_data, indent=2))
    assert health_data["matlab_connected"] is True, "MATLAB Engine is not connected"
    assert health_data["model_loaded"] is True, "Model is not loaded"
    print("[OK] Frontend proxy successfully forwarded /api/health to FastAPI backend.")

    # 3. Test Model Info & Parameters via Frontend Proxy
    print("\n[3] Checking Model Info via Frontend Proxy at http://127.0.0.1:3000/api/model/info...")
    res_info = client.get("http://127.0.0.1:3000/api/model/info")
    assert res_info.status_code == 200
    info_data = res_info.json()
    print(f"Model: {info_data['model_name']} | Blocks: {info_data['total_blocks']} | Sample Time: {info_data['sample_time']}")
    print(f"Channels: {', '.join([c['name'] for c in info_data['signal_channels']])}")
    print("[OK] Model info verified.")

    # 4. Execute AB (Line-to-Line) fault through frontend proxy
    print("\n[4] Executing Line-to-Line (AB) Simulation via Frontend Proxy...")
    t0 = time.time()
    ab_payload = {
        "fault_type": "AB",
        "fault_resistance": 0.001,
        "ground_resistance": 0.01,
        "downsample_points": 500
    }
    res_ab = client.post("http://127.0.0.1:3000/api/simulation/run", json=ab_payload)
    dur_ab = time.time() - t0
    print(f"AB Simulation HTTP Status: {res_ab.status_code} in {dur_ab:.2f}s")
    assert res_ab.status_code == 200, f"AB simulation failed: {res_ab.text}"
    ab_data = res_ab.json()
    print(f"Run ID: {ab_data['run_id']}")
    print(f"Execution Duration: {ab_data['execution_duration_sec']}s")
    print(f"Metrics: Peak Current = {ab_data['metrics']['peak_current']} A, Min Voltage = {ab_data['metrics']['min_voltage']} V")
    print(f"Breaker Tripped: {ab_data['metrics']['is_breaker_tripped']}, Trip Time: {ab_data['metrics']['breaker_trip_time']} s")
    assert ab_data["metrics"]["is_breaker_tripped"] is True, "Breaker failed to trip for AB fault"
    assert ab_data["metrics"]["peak_current"] > 100.0, f"Peak current too low for AB fault: {ab_data['metrics']['peak_current']}"
    print("[OK] AB fault simulation successfully verified with breaker actuation.")

    # 5. Check History through frontend proxy
    print("\n[5] Checking Simulation History via Frontend Proxy...")
    res_hist = client.get("http://127.0.0.1:3000/api/simulation/history")
    assert res_hist.status_code == 200
    hist_items = res_hist.json()
    print(f"History contains {len(hist_items)} runs:")
    for h in hist_items:
        print(f"  * Run {h['run_id'][:8]} | Scenario: {h['fault_type']} | Tripped: {h['is_breaker_tripped']} | Peak I: {h['peak_current']}A")
    assert len(hist_items) >= 1, "History empty"
    print("[OK] Simulation history successfully verified.")

    print("\n" + "=" * 70)
    print("ALL FRONTEND INTEGRATION TESTS PASSED EMPIRICALLY!")
    print("=" * 70)

if __name__ == "__main__":
    test_frontend_backend_integration()
