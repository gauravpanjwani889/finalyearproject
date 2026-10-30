"""
Backend Configuration for Smart Grid Stability Monitoring & Automated Fault Diagnostic Platform.
"""

from pathlib import Path

# Base Paths
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
MATLAB_DIR = PROJECT_ROOT / "matlab"
MODEL_PATH = MATLAB_DIR / "main_model.slx"
MODEL_NAME = "main_model"

# Verify model path exists
if not MODEL_PATH.exists():
    raise FileNotFoundError(f"Simulink model not found at resolved path: {MODEL_PATH}")

# Simulation Solver Constants (Derived from Simulink configSet and powergui audit)
SIMULATION_STOP_TIME = 1.0  # seconds
POWERGUI_SAMPLE_TIME = 5e-5  # 50 microseconds (20 kHz sampling rate)
TOTAL_EXPECTED_SAMPLES = 20005
DEFAULT_DOWNSAMPLE_POINTS = 1000

# Verified Block Paths in main_model.slx
BLOCK_SERIES_RLC = f"{MODEL_NAME}/Three-Phase Series RLC Branch"
BLOCK_FAULT = f"{MODEL_NAME}/Three-Phase Fault"
BLOCK_BREAKER = f"{MODEL_NAME}/Three-Phase Breaker"
BLOCK_TRANSFORMER = f"{MODEL_NAME}/Three-Phase Transformer (Two Windings)"
BLOCK_SYNCHRONOUS_MACHINE = f"{MODEL_NAME}/Synchronous Machine pu Standard"
BLOCK_LOAD = f"{MODEL_NAME}/Three-Phase Parallel RLC Load"
BLOCK_PI_LINE = f"{MODEL_NAME}/Three-Phase PI Section Line"
BLOCK_GEN_PM = f"{MODEL_NAME}/Constant"
BLOCK_GEN_VF = f"{MODEL_NAME}/Constant1"
BLOCK_MEASUREMENT = f"{MODEL_NAME}/Three-Phase V-I Measurement"

# Server Settings
API_HOST = "0.0.0.0"
API_PORT = 8000
CORS_ORIGINS = ["*"]
