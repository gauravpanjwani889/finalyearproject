"""
Comprehensive Integration Test Suite for MATLAB/Simulink Backend Integration.
Executes all 12 mandatory integration tests against authentic Simulink solver runs.
"""

import asyncio
import pytest
import numpy as np
from fastapi.testclient import TestClient

from backend.config import MODEL_NAME, MODEL_PATH, TOTAL_EXPECTED_SAMPLES
from backend.models import SimulationParams, FaultType
from backend.matlab_engine import MatlabSessionManager
from backend.sim_runner import SimulationRunner, FAULT_MAPPING
from backend.analytics import compute_true_powers, calculate_electrical_metrics, decimate_waveforms
from backend.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Ensure a single event loop runs for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def session_manager(event_loop):
    """Session-scoped fixture ensuring MATLAB is started once and reused."""
    manager = event_loop.run_until_complete(MatlabSessionManager.get_instance())
    yield manager
    event_loop.run_until_complete(manager.close())


@pytest.fixture(scope="session")
def client(session_manager):
    """FastAPI TestClient sharing the active MATLAB session."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def runner(session_manager):
    return SimulationRunner(session_manager)


# Caching fixtures to run solver once per fault type and share across assertions
@pytest.fixture(scope="session")
def sim_result_abc(runner, event_loop):
    return event_loop.run_until_complete(runner.run_simulation(SimulationParams(fault_type=FaultType.ABC)))


@pytest.fixture(scope="session")
def sim_result_normal(runner, event_loop):
    return event_loop.run_until_complete(runner.run_simulation(SimulationParams(fault_type=FaultType.NORMAL)))


@pytest.fixture(scope="session")
def sim_result_ag(runner, event_loop):
    return event_loop.run_until_complete(runner.run_simulation(SimulationParams(fault_type=FaultType.AG)))


@pytest.fixture(scope="session")
def sim_result_ab(runner, event_loop):
    return event_loop.run_until_complete(runner.run_simulation(SimulationParams(fault_type=FaultType.AB)))


# =====================================================================
# TEST 1: Python connects to MATLAB successfully
# =====================================================================
def test_01_matlab_connection(session_manager):
    assert session_manager.is_connected, "MATLAB Engine is not connected"
    assert "25.1" in session_manager.matlab_version or "R2025" in session_manager.matlab_version
    print(f"\n[TEST 1 PASSED] MATLAB connected: Version {session_manager.matlab_version}")


# =====================================================================
# TEST 2: Python loads the original Simulink model
# =====================================================================
def test_02_model_loading(session_manager):
    assert session_manager.is_model_loaded, "Model is not loaded"
    eng = session_manager.engine
    loaded_models = eng.eval("find_system('type', 'block_diagram');", nargout=1)
    assert MODEL_NAME in loaded_models, f"'{MODEL_NAME}' was not found in loaded models: {loaded_models}"
    print(f"\n[TEST 2 PASSED] Original model '{MODEL_NAME}.slx' confirmed loaded in Simulink.")


# =====================================================================
# TEST 3: Python executes an actual simulation
# =====================================================================
def test_03_actual_simulation_execution(sim_result_abc):
    assert "time" in sim_result_abc
    assert "signals" in sim_result_abc
    assert sim_result_abc["sim_duration"] > 0.0
    print(f"\n[TEST 3 PASSED] Solver executed authentic simulation in {sim_result_abc['sim_duration']:.2f}s.")


# =====================================================================
# TEST 4: ScopeData is retrieved successfully
# =====================================================================
def test_04_scopedata_retrieval(sim_result_abc):
    time_vec = sim_result_abc["time"]
    assert len(time_vec) >= 20000, f"Expected ~20005 time samples, got {len(time_vec)}"
    assert abs(time_vec[0] - 0.0) < 1e-4, "Start time must be 0.0s"
    assert abs(time_vec[-1] - 1.0) < 1e-4, "Stop time must be 1.0s"
    print(f"\n[TEST 4 PASSED] ScopeData retrieved: {len(time_vec)} time steps spanning [0.0s, 1.0s].")


# =====================================================================
# TEST 5: All nine signal channels are correctly extracted
# =====================================================================
def test_05_nine_signal_channels_extracted(sim_result_abc):
    signals = sim_result_abc["signals"]
    assert signals.shape[1] == 9, f"Expected 9 channels, got {signals.shape[1]}"
    
    # Check that channels have non-zero variance (active physical data)
    for ch in range(9):
        var_ch = np.var(signals[:, ch])
        assert var_ch > 0.0, f"Channel {ch} has zero variance (flatline)"
    
    print("\n[TEST 5 PASSED] All 9 channels verified with active dynamic variation.")


# =====================================================================
# TEST 6: The normal operating scenario runs successfully (no fault)
# =====================================================================
def test_06_normal_operating_scenario(sim_result_normal):
    signals = sim_result_normal["signals"]
    trip_signal = signals[:, 6]
    imag = signals[:, 8]
    
    # In normal healthy operation, the trip signal must never latch to 1
    assert np.all(trip_signal < 0.5), "Circuit breaker tripped during normal healthy operation"
    # Current magnitude should remain low (no short circuit)
    assert np.max(imag) < 50.0, f"Unexpected high current magnitude in normal run: {np.max(imag):.2f} A"
    
    print(f"\n[TEST 6 PASSED] Normal operation verified: Trip signal = 0 throughout, max Imag = {np.max(imag):.2f} A.")


# =====================================================================
# TEST 7: AG fault configuration changes the model and its results
# =====================================================================
def test_07_ag_fault_scenario(sim_result_normal, sim_result_ag):
    ia_normal = sim_result_normal["signals"][:, 3]
    ia_ag = sim_result_ag["signals"][:, 3]
    
    # AG fault must produce significantly higher Phase A current than normal
    max_ia_normal = np.max(np.abs(ia_normal))
    max_ia_ag = np.max(np.abs(ia_ag))
    
    assert max_ia_ag > 2.0 * max_ia_normal, f"AG fault current ({max_ia_ag:.2f}A) not significantly higher than normal ({max_ia_normal:.2f}A)"
    
    ib_ag = sim_result_ag["signals"][:, 4]
    max_ib_ag = np.max(np.abs(ib_ag))
    print(f"\n[TEST 7 PASSED] AG Fault verified: Ia surge = {max_ia_ag:.2f} A (vs normal {max_ia_normal:.2f} A, Ib = {max_ib_ag:.2f} A).")


# =====================================================================
# TEST 8: AB fault configuration changes the model and its results
# =====================================================================
def test_08_ab_fault_scenario(sim_result_ab):
    ia_ab = sim_result_ab["signals"][:, 3]
    ib_ab = sim_result_ab["signals"][:, 4]
    ic_ab = sim_result_ab["signals"][:, 5]
    
    max_ia = np.max(np.abs(ia_ab))
    max_ib = np.max(np.abs(ib_ab))
    max_ic = np.max(np.abs(ic_ab))
    
    # In AB fault, Phase A and Phase B experience severe short circuit currents
    assert max_ia > 100.0, f"Expected Phase A surge in AB fault, got {max_ia:.2f} A"
    assert max_ib > 100.0, f"Expected Phase B surge in AB fault, got {max_ib:.2f} A"
    
    print(f"\n[TEST 8 PASSED] AB Fault verified: Ia surge = {max_ia:.2f} A, Ib surge = {max_ib:.2f} A, Ic = {max_ic:.2f} A.")


# =====================================================================
# TEST 9: ABC fault configuration changes the model and its results
# =====================================================================
def test_09_abc_fault_scenario(sim_result_abc):
    ia = sim_result_abc["signals"][:, 3]
    ib = sim_result_abc["signals"][:, 4]
    ic = sim_result_abc["signals"][:, 5]
    
    # Symmetrical 3-phase fault surges all 3 phases
    assert np.max(np.abs(ia)) > 200.0
    assert np.max(np.abs(ib)) > 200.0
    assert np.max(np.abs(ic)) > 200.0
    
    print(f"\n[TEST 9 PASSED] ABC Fault verified: All 3 phases surged (Ia={np.max(np.abs(ia)):.2f}A, Ib={np.max(np.abs(ib)):.2f}A, Ic={np.max(np.abs(ic)):.2f}A).")


# =====================================================================
# TEST 10: Breaker status is interpreted correctly
# =====================================================================
def test_10_breaker_status_interpretation(sim_result_normal, sim_result_abc):
    # 1. Normal run: Breaker must stay closed (0)
    trip_normal = sim_result_normal["signals"][:, 6]
    assert np.all(trip_normal == 0.0), "Breaker tripped in normal run"
    
    # 2. ABC fault run: Breaker must trip (1) during fault window
    time_vec = sim_result_abc["time"]
    trip_fault = sim_result_abc["signals"][:, 6]
    
    trip_indices = np.where(trip_fault > 0.5)[0]
    assert len(trip_indices) > 0, "Breaker failed to trip during ABC fault"
    t_trip_start = time_vec[trip_indices[0]]
    t_trip_end = time_vec[trip_indices[-1]]
    
    assert abs(t_trip_start - 0.2005) < 0.01, f"Unexpected trip onset time: {t_trip_start:.4f}s"
    assert abs(t_trip_end - 0.4000) < 0.01, f"Unexpected trip reset time: {t_trip_end:.4f}s"
    
    print(f"\n[TEST 10 PASSED] Breaker logic verified: 0=Closed (Normal), 1=Tripped at t={t_trip_start:.4f}s, cleared at t={t_trip_end:.4f}s.")


# =====================================================================
# TEST 11: FastAPI returns valid simulation data
# =====================================================================
def test_11_fastapi_endpoints(client):
    # Test GET /api/health
    resp_health = client.get("/api/health")
    assert resp_health.status_code == 200
    health_data = resp_health.json()
    assert health_data["status"] == "ONLINE"
    assert health_data["matlab_connected"] is True
    assert health_data["model_loaded"] is True
    
    # Test GET /api/model/info
    resp_info = client.get("/api/model/info")
    assert resp_info.status_code == 200
    info_data = resp_info.json()
    assert info_data["model_name"] == MODEL_NAME
    assert info_data["total_blocks"] == 73
    
    # Test POST /api/simulation/run
    sim_payload = {
        "fault_type": "AG",
        "fault_resistance": 1.0,
        "downsample_points": 500
    }
    resp_sim = client.post("/api/simulation/run", json=sim_payload)
    assert resp_sim.status_code == 200
    sim_data = resp_sim.json()
    
    assert sim_data["status"] == "SUCCESS"
    assert "metrics" in sim_data
    assert "waveforms" in sim_data
    assert sim_data["downsampled_samples"] <= 600
    assert len(sim_data["waveforms"]["time"]) == sim_data["downsampled_samples"]
    
    # Test GET /api/simulation/results/{run_id}
    run_id = sim_data["run_id"]
    resp_get = client.get(f"/api/simulation/results/{run_id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["run_id"] == run_id
    
    print(f"\n[TEST 11 PASSED] FastAPI endpoints verified: Health, Info, Run (ID: {run_id[:8]}), and Result Retrieval.")


# =====================================================================
# TEST 12: Consecutive simulation runs operate reliably without contamination
# =====================================================================
def test_12_consecutive_runs_hygiene(runner, event_loop):
    # Run 1: NORMAL
    r1 = event_loop.run_until_complete(runner.run_simulation(SimulationParams(fault_type=FaultType.NORMAL)))
    assert np.all(r1["signals"][:, 6] == 0.0), "Run 1 failed"
    
    # Run 2: ABC Fault
    r2 = event_loop.run_until_complete(runner.run_simulation(SimulationParams(fault_type=FaultType.ABC)))
    assert np.any(r2["signals"][:, 6] == 1.0), "Run 2 failed"
    
    # Run 3: NORMAL again (must NOT have lingering fault from Run 2)
    r3 = event_loop.run_until_complete(runner.run_simulation(SimulationParams(fault_type=FaultType.NORMAL)))
    assert np.all(r3["signals"][:, 6] == 0.0), "Run 3 was contaminated by Run 2 fault state"
    assert np.max(r3["signals"][:, 8]) < 50.0, "Run 3 had lingering current surge"
    
    print("\n[TEST 12 PASSED] Consecutive runs verified: NORMAL -> ABC -> NORMAL executed cleanly without contamination.")
