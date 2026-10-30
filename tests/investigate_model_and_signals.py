"""
Deep Investigation Script:
- Analyzes main_model.slx topology and measurement block positions
- Inspects Synchronous Machine, Transformer, Inverters, Breaker, PI Line, Fault, Load parameters
- Runs full-resolution NORMAL simulation and saves raw data
- Inspects MATPOWER availability
- Tests additional fault combinations (BG, CG, BC, CA, ABG, BCG, CAG)
"""

import sys
import json
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matlab.engine

def investigate():
    print("=" * 70)
    print("STARTING DEEP SIMULINK MODEL & ELECTRICAL SIGNAL INVESTIGATION")
    print("=" * 70)

    print("Starting MATLAB Engine...")
    eng = matlab.engine.start_matlab()
    print("MATLAB Version:", eng.eval("version", nargout=1))

    matlab_dir = str(PROJECT_ROOT / "matlab").replace('\\', '/')
    eng.eval(f"addpath('{matlab_dir}');", nargout=0)

    model_name = "main_model"
    print(f"Loading system '{model_name}'...")
    eng.load_system(model_name, nargout=0)

    # 1. Investigate Measurement Block Connectivity
    print("\n--- 1. MEASUREMENT BLOCK CONNECTIVITY ---")
    meas_block = f"{model_name}/Three-Phase V-I Measurement"
    ports = eng.get_param(meas_block, "PortConnectivity", nargout=1)
    print(f"Measurement block '{meas_block}' PortConnectivity retrieved.")
    
    # Inspect block parameters of Three-Phase V-I Measurement
    dialog_params = eng.get_param(meas_block, "DialogParameters", nargout=1)
    print("Measurement Block DialogParameters:", list(dialog_params.keys()))
    print("VoltageMeasurement:", eng.get_param(meas_block, "VoltageMeasurement", nargout=1))
    print("CurrentMeasurement:", eng.get_param(meas_block, "CurrentMeasurement", nargout=1))

    # Inspect all lines connected to SID=7 (Three-Phase V-I Measurement)
    lines = eng.eval(f"""
        bh = get_param('{meas_block}', 'Handle');
        pc = get_param(bh, 'PortConnectivity');
        lh = get_param(bh, 'LineHandles');
        r = struct('in_lines', lh.Inport, 'out_lines', lh.Outport, 'lConn', lh.LConn, 'rConn', lh.RConn);
    """, nargout=1)
    print("Measurement LineHandles:", lines)

    # Let's inspect where LConn (left connector) and RConn (right connector) connect
    conn_info = eng.eval(f"""
        bh = get_param('{meas_block}', 'Handle');
        pc = get_param(bh, 'PortConnectivity');
        info = {{}};
        for i = 1:length(pc)
            src_blocks = {{}};
            for j = 1:length(pc(i).SrcBlock)
                if pc(i).SrcBlock(j) > 0
                    src_blocks{{end+1}} = get_param(pc(i).SrcBlock(j), 'Name');
                end
            end
            dst_blocks = {{}};
            for j = 1:length(pc(i).DstBlock)
                if pc(i).DstBlock(j) > 0
                    dst_blocks{{end+1}} = get_param(pc(i).DstBlock(j), 'Name');
                end
            end
            info{{i}} = struct('Type', pc(i).Type, 'Src', {{src_blocks}}, 'Dst', {{dst_blocks}});
        end
        info
    """, nargout=1)
    print("Measurement Port Connectivity Details:")
    for idx, c in enumerate(conn_info):
        print(f"  Port {idx+1} ({c['Type']}): Src={c['Src']}, Dst={c['Dst']}")

    # 2. Inspect Synchronous Machine
    print("\n--- 2. SYNCHRONOUS MACHINE PARAMETERS ---")
    gen_block = f"{model_name}/Synchronous Machine pu Standard"
    gen_params = eng.get_param(gen_block, "DialogParameters", nargout=1)
    print("Gen DialogParameters count:", len(gen_params))
    for p in ['NominalParameters', 'RotorType', 'Stator', 'Field', 'MechanicalLoad', 'Units']:
        if p in gen_params:
            print(f"  {p}: {eng.get_param(gen_block, p, nargout=1)}")
    
    # Check inputs to Synchronous Machine (Mechanical power Pm and Field voltage Vf)
    pm_block = f"{model_name}/Constant"
    vf_block = f"{model_name}/Constant1"
    print(f"  Pm Constant Block Value: {eng.get_param(pm_block, 'Value', nargout=1)}")
    print(f"  Vf Constant Block Value: {eng.get_param(vf_block, 'Value', nargout=1)}")

    # 3. Inspect Three-Phase Transformer
    print("\n--- 3. TRANSFORMER PARAMETERS ---")
    trafo_block = f"{model_name}/Three-Phase Transformer (Two Windings)"
    trafo_params = eng.get_param(trafo_block, "DialogParameters", nargout=1)
    for p in ['NominalPower', 'Winding1Connection', 'Winding1', 'Winding2Connection', 'Winding2']:
        if p in trafo_params:
            print(f"  {p}: {eng.get_param(trafo_block, p, nargout=1)}")

    # 4. Inspect Series RLC Branch
    print("\n--- 4. SERIES RLC BRANCH PARAMETERS ---")
    rlc_block = f"{model_name}/Three-Phase Series RLC Branch"
    rlc_params = eng.get_param(rlc_block, "DialogParameters", nargout=1)
    for p in ['BranchType', 'Resistance', 'Inductance', 'Capacitance']:
        if p in rlc_params:
            print(f"  {p}: {eng.get_param(rlc_block, p, nargout=1)}")

    # 5. Inspect Series VSC Inverters
    print("\n--- 5. SERIES VSC INVERTERS ---")
    vsc1 = f"{model_name}/Series VSC 1"
    vsc2 = f"{model_name}/Series VSC 2"
    for p in ['Device', 'Ron', 'ForwardVoltages', 'SnubberResistance', 'SnubberCapacitance']:
        print(f"  VSC1 {p}: {eng.get_param(vsc1, p, nargout=1)}")

    # 6. Inspect Three-Phase Breaker
    print("\n--- 6. THREE-PHASE BREAKER PARAMETERS ---")
    breaker_block = f"{model_name}/Three-Phase Breaker"
    breaker_params = eng.get_param(breaker_block, "DialogParameters", nargout=1)
    for p in ['InitialState', 'SwitchA', 'SwitchB', 'SwitchC', 'External', 'BreakerResistance', 'SnubberResistance']:
        if p in breaker_params:
            print(f"  {p}: {eng.get_param(breaker_block, p, nargout=1)}")

    # 7. Inspect PI Section Line
    print("\n--- 7. PI SECTION LINE PARAMETERS ---")
    pi_block = f"{model_name}/Three-Phase PI Section Line"
    pi_params = eng.get_param(pi_block, "DialogParameters", nargout=1)
    for p in ['Frequency', 'Resistances', 'Inductances', 'Capacitances', 'Length']:
        if p in pi_params:
            print(f"  {p}: {eng.get_param(pi_block, p, nargout=1)}")

    # 8. Inspect Parallel RLC Load
    print("\n--- 8. PARALLEL RLC LOAD PARAMETERS ---")
    load_block = f"{model_name}/Three-Phase Parallel RLC Load"
    load_params = eng.get_param(load_block, "DialogParameters", nargout=1)
    for p in ['NominalVoltage', 'NominalFrequency', 'ActivePower', 'InductivePower', 'CapacitivePower']:
        if p in load_params:
            print(f"  {p}: {eng.get_param(load_block, p, nargout=1)}")

    # 9. Inspect Three-Phase Fault Block
    print("\n--- 9. THREE-PHASE FAULT BLOCK PARAMETERS ---")
    fault_block = f"{model_name}/Three-Phase Fault"
    fault_params = eng.get_param(fault_block, "DialogParameters", nargout=1)
    for p in ['FaultA', 'FaultB', 'FaultC', 'GroundFault', 'FaultResistance', 'GroundResistance', 'SwitchTimes', 'ExternalControl']:
        if p in fault_params:
            print(f"  {p}: {eng.get_param(fault_block, p, nargout=1)}")

    # 10. Check MATPOWER
    print("\n--- 10. MATPOWER AUDIT ---")
    has_runpf = eng.eval("exist('runpf', 'file')", nargout=1)
    has_case118 = eng.eval("exist('case118', 'file')", nargout=1)
    has_case57 = eng.eval("exist('case57', 'file')", nargout=1)
    print(f"  exist('runpf'): {has_runpf} (2 = M-file / function)")
    print(f"  exist('case118'): {has_case118}")
    print(f"  exist('case57'): {has_case57}")

    # 11. Run Full-Resolution NORMAL Simulation and extract raw ScopeData
    print("\n--- 11. RUNNING FULL-RESOLUTION NORMAL SIMULATION ---")
    eng.set_param(fault_block, "FaultA", "off", nargout=0)
    eng.set_param(fault_block, "FaultB", "off", nargout=0)
    eng.set_param(fault_block, "FaultC", "off", nargout=0)
    eng.set_param(fault_block, "GroundFault", "off", nargout=0)
    eng.eval("clear ScopeData simOut scopeObj;", nargout=0)
    
    print("Executing sim('main_model')...")
    eng.eval("simOut = sim('main_model');", nargout=0)
    print("Sim completed.")

    eng.eval("""
        if exist('ScopeData','var'), scopeObj = ScopeData;
        elseif exist('simOut','var') && isa(simOut,'Simulink.SimulationOutput'), scopeObj = simOut.get('ScopeData');
        else, error('ScopeData not found'); end
    """, nargout=0)

    raw_time = np.array(eng.eval("scopeObj.time")).flatten()
    raw_signals = np.array(eng.eval("scopeObj.signals.values"))
    if raw_signals.ndim == 2 and raw_signals.shape[0] != len(raw_time):
        raw_signals = raw_signals.T

    print(f"Raw Time shape: {raw_time.shape}, Signals shape: {raw_signals.shape}")
    
    # Save raw arrays to scratch/raw_normal_run.npz
    scratch_dir = PROJECT_ROOT / "scratch"
    scratch_dir.mkdir(exist_ok=True)
    np.savez_compressed(
        scratch_dir / "raw_normal_run.npz",
        time=raw_time,
        signals=raw_signals,
    )
    print(f"Saved raw simulation data to {scratch_dir / 'raw_normal_run.npz'}")

    # 12. Test Additional Fault Combinations
    print("\n--- 12. TESTING ADDITIONAL FAULT COMBINATIONS ---")
    extra_faults = {
        "BG": {"FaultA": "off", "FaultB": "on", "FaultC": "off", "GroundFault": "on"},
        "CG": {"FaultA": "off", "FaultB": "off", "FaultC": "on", "GroundFault": "on"},
        "BC": {"FaultA": "off", "FaultB": "on", "FaultC": "on", "GroundFault": "off"},
        "CA": {"FaultA": "on", "FaultB": "off", "FaultC": "on", "GroundFault": "off"},
        "ABG": {"FaultA": "on", "FaultB": "on", "FaultC": "off", "GroundFault": "on"},
        "BCG": {"FaultA": "off", "FaultB": "on", "FaultC": "on", "GroundFault": "on"},
        "CAG": {"FaultA": "on", "FaultB": "off", "FaultC": "on", "GroundFault": "on"},
    }
    for fname, fparams in extra_faults.items():
        try:
            for k, v in fparams.items():
                eng.set_param(fault_block, k, v, nargout=0)
            print(f"  Setting {fname}: SUCCESS")
        except Exception as e:
            print(f"  Setting {fname}: FAILED ({e})")

    # Restore fault block to default
    eng.set_param(fault_block, "FaultA", "off", nargout=0)
    eng.set_param(fault_block, "FaultB", "off", nargout=0)
    eng.set_param(fault_block, "FaultC", "off", nargout=0)
    eng.set_param(fault_block, "GroundFault", "off", nargout=0)

    print("\nClosing MATLAB Engine...")
    eng.quit()
    print("Investigation complete.")

if __name__ == "__main__":
    investigate()
