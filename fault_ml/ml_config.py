"""Central config: fault classes, Simulink block paths, parameter sampling ranges."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = ROOT.parent / "matlab" / "main_model.slx"   # fault_ml/ ko Smart_Grid_Automation/ ke andar rakho
MODEL = "main_model"

# 12 classes. (phases, ground) -> FaultA/B/C/GroundFault
# NOTE: letters se programmatically bana hai (PARAMETER_MAPPING.md me BCG row copy-paste galti hai: A on dikhaya hai).
FAULT_NAMES = ["NORMAL", "AG", "BG", "CG", "AB", "BC", "CA", "ABG", "BCG", "CAG", "ABC", "ABCG"]


def fault_flags(name: str) -> dict:
    if name == "NORMAL":
        return {"FaultA": "off", "FaultB": "off", "FaultC": "off", "GroundFault": "off"}
    letters = set(name.replace("G", "")) if name != "ABCG" else set("ABC")
    return {
        "FaultA": "on" if "A" in letters else "off",
        "FaultB": "on" if "B" in letters else "off",
        "FaultC": "on" if "C" in letters else "off",
        "GroundFault": "on" if name.endswith("G") else "off",
    }


# Simulink block paths (PARAMETER_MAPPING.md / TECHNICAL_AUDIT.md se)
BLK_FAULT = f"{MODEL}/Three-Phase Fault"
BLK_SERIES = f"{MODEL}/Three-Phase Series RLC Branch"
BLK_PM = f"{MODEL}/Constant"       # turbine mechanical power (pu)
BLK_VF = f"{MODEL}/Constant1"      # field excitation (pu)

# --- Sampling ranges ---------------------------------------------------------
RF_RANGE = (0.01, 10.0)            # ohm, log-uniform. >~20 ohm pe fault current load current jitna ho jata hai
RG_RANGE = (0.01, 5.0)             # ohm, log-uniform
START_RANGE = (0.17, 0.30)         # s. >=0.15 (relay blanking) aur window 0.4 s reset se pehle khatam ho
FAULT_STOP = 0.40                  # s. Protection Logic ka reset Step 0.4 s pe hardcoded hai
STOP_TIME = 0.45                   # s. Simulation chhota rakho (1.0 ki jagah) -> ~2x fast

# Operating-condition variation (har condition pe saare 12 classes chalte hain). Narrow rakha hai kyunki
# bina test ke bade swing se solver diverge kar sakta hai; --check/--dry-run ke baad badha sakte ho.
COND_RANGES = {
    "line_r": (0.001, 0.02),       # ohm   (Series RLC branch)
    "line_l": (0.5e-3, 2.0e-3),    # H
    "vf":     (0.95, 1.05),        # pu    (Constant1)
    "pm":     (0.85, 1.00),        # pu    (Constant)
}
