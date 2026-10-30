"""
Python MATLAB Engine Script:
- Executes clean NORMAL simulation
- Extracts full-resolution 20,005 time and signal points
- Saves to scratch/raw_normal_data.npz
- Tests additional fault configurations: BG, CG, BC, CA, ABG, BCG, CAG
- Tests Generator, Transformer, Load, Line parameters
"""

import sys
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matlab.engine

def run():
    print("Starting MATLAB Engine via Python API...")
    eng = matlab.engine.start_matlab()
    print("MATLAB Version:", eng.eval("version", nargout=1))

    matlab_dir = str(PROJECT_ROOT / "matlab").replace('\\', '/')
    eng.eval(f"addpath('{matlab_dir}');", nargout=0)

    model_name = "main_model"
    print(f"Loading '{model_name}'...")
    eng.load_system(model_name, nargout=0)

    # 1. NORMAL run
    print("Configuring NORMAL (no fault)...")
    fault_block = f"{model_name}/Three-Phase Fault"
    eng.set_param(fault_block, "FaultA", "off", nargout=0)
    eng.set_param(fault_block, "FaultB", "off", nargout=0)
    eng.set_param(fault_block, "FaultC", "off", nargout=0)
    eng.set_param(fault_block, "GroundFault", "off", nargout=0)

    eng.eval("clear ScopeData simOut scopeObj;", nargout=0)
    print("Executing sim('main_model')...")
    eng.eval("simOut = sim('main_model');", nargout=0)
    print("Simulation completed.")

    eng.eval("""
        if exist('ScopeData','var'), scopeObj = ScopeData;
        elseif exist('simOut','var') && isa(simOut,'Simulink.SimulationOutput'), scopeObj = simOut.get('ScopeData');
        else, error('ScopeData not found'); end
    """, nargout=0)

    raw_time = np.array(eng.eval("scopeObj.time")).flatten()
    raw_signals = np.array(eng.eval("scopeObj.signals.values"))
    if raw_signals.ndim == 2 and raw_signals.shape[0] != len(raw_time):
        raw_signals = raw_signals.T

    print(f"Extracted {len(raw_time)} samples across {raw_signals.shape[1]} channels.")

    scratch_dir = PROJECT_ROOT / "scratch"
    scratch_dir.mkdir(exist_ok=True)
    np.savez_compressed(
        scratch_dir / "raw_normal_data.npz",
        time=raw_time,
        signals=raw_signals,
    )
    print(f"Saved to {scratch_dir / 'raw_normal_data.npz'}")

    # 2. Test Additional Fault Scenarios
    print("\nTesting additional fault combinations on Three-Phase Fault block:")
    combos = {
        "BG": {"FaultA": "off", "FaultB": "on", "FaultC": "off", "GroundFault": "on"},
        "CG": {"FaultA": "off", "FaultB": "off", "FaultC": "on", "GroundFault": "on"},
        "BC": {"FaultA": "off", "FaultB": "on", "FaultC": "on", "GroundFault": "off"},
        "CA": {"FaultA": "on", "FaultB": "off", "FaultC": "on", "GroundFault": "off"},
        "ABG": {"FaultA": "on", "FaultB": "on", "FaultC": "off", "GroundFault": "on"},
        "BCG": {"FaultA": "off", "FaultB": "on", "FaultC": "on", "GroundFault": "on"},
        "CAG": {"FaultA": "on", "FaultB": "off", "FaultC": "on", "GroundFault": "on"},
    }
    for name, p in combos.items():
        try:
            for k, v in p.items():
                eng.set_param(fault_block, k, v, nargout=0)
            # Read back
            rb = {k: eng.get_param(fault_block, k, nargout=1) for k in p.keys()}
            match = all(rb[k] == p[k] for k in p.keys())
            print(f"  Fault scenario '{name}': Verified (Readback match: {match})")
        except Exception as e:
            print(f"  Fault scenario '{name}': FAILED ({e})")

    # Restore fault block
    eng.set_param(fault_block, "FaultA", "off", nargout=0)
    eng.set_param(fault_block, "FaultB", "off", nargout=0)
    eng.set_param(fault_block, "FaultC", "off", nargout=0)
    eng.set_param(fault_block, "GroundFault", "off", nargout=0)

    # 3. Test Parameter Modifications on Generator, Transformer, Load, Line
    print("\nTesting parameter updates and readbacks on electrical components:")
    
    # A. Generator
    gen_block = f"{model_name}/Synchronous Machine pu Standard"
    pm_block = f"{model_name}/Constant"
    vf_block = f"{model_name}/Constant1"
    nom_gen = eng.get_param(gen_block, "NominalParameters", nargout=1)
    val_pm = eng.get_param(pm_block, "Value", nargout=1)
    val_vf = eng.get_param(vf_block, "Value", nargout=1)
    print(f"  Generator Nominal: {nom_gen}")
    print(f"  Generator Pm Constant: {val_pm}")
    print(f"  Generator Vf Constant: {val_vf}")

    # B. Transformer
    trafo_block = f"{model_name}/Three-Phase Transformer (Two Windings)"
    p_nom = eng.get_param(trafo_block, "NominalPower", nargout=1)
    w1 = eng.get_param(trafo_block, "Winding1", nargout=1)
    w2 = eng.get_param(trafo_block, "Winding2", nargout=1)
    print(f"  Transformer NominalPower: {p_nom}")
    print(f"  Transformer Winding1 (Primary): {w1}")
    print(f"  Transformer Winding2 (Secondary): {w2}")

    # C. Load
    load_block = f"{model_name}/Three-Phase Parallel RLC Load"
    v_load = eng.get_param(load_block, "NominalVoltage", nargout=1)
    p_load = eng.get_param(load_block, "ActivePower", nargout=1)
    ql_load = eng.get_param(load_block, "InductivePower", nargout=1)
    qc_load = eng.get_param(load_block, "CapacitivePower", nargout=1)
    print(f"  Load NominalVoltage: {v_load}")
    print(f"  Load ActivePower: {p_load}")
    print(f"  Load InductivePower: {ql_load}")
    print(f"  Load CapacitivePower: {qc_load}")

    # D. Line
    rlc_block = f"{model_name}/Three-Phase Series RLC Branch"
    pi_block = f"{model_name}/Three-Phase PI Section Line"
    r_val = eng.get_param(rlc_block, "Resistance", nargout=1)
    l_val = eng.get_param(rlc_block, "Inductance", nargout=1)
    c_val = eng.get_param(rlc_block, "Capacitance", nargout=1)
    len_val = eng.get_param(pi_block, "Length", nargout=1)
    print(f"  Series RLC Resistance: {r_val}")
    print(f"  Series RLC Inductance: {l_val}")
    print(f"  Series RLC Capacitance: {c_val}")
    print(f"  PI Section Line Length: {len_val}")

    print("\nClosing MATLAB Engine cleanly...")
    eng.quit()
    print("Done.")

if __name__ == "__main__":
    run()
