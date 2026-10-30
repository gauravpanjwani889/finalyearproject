import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import matlab.engine

print("Connecting to MATLAB...", flush=True)
eng = matlab.engine.start_matlab()
print("Loading main_model...", flush=True)
eng.load_system("matlab/main_model", nargout=0)

fault_block = "main_model/Three-Phase Fault"
dialog_params = eng.get_param(fault_block, "DialogParameters", nargout=1)
print("\n--- DialogParameters of Three-Phase Fault ---", flush=True)
for k in sorted(dialog_params.keys()):
    try:
        val = eng.get_param(fault_block, k, nargout=1)
        print(f"  {k} = {val}", flush=True)
    except Exception as e:
        print(f"  {k} = <error: {e}>", flush=True)

# Also check block input ports to see if external control signal is connected
inports = eng.get_param(fault_block, "PortConnectivity", nargout=1)
print(f"\nPortConnectivity count: {len(inports)}", flush=True)

eng.close()
print("Done.", flush=True)
