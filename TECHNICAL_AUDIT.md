# Technical Audit Report: Smart Grid Stability Monitoring & Automated Fault Diagnostic Platform

**Date:** 2026-10-10  
**Status:** Audit Complete & Empirically Verified  
**Author:** Lead MATLAB/Simulink Integration Engineer  
**Target System:** `matlab/main_model.slx`, `existing_python/app.py`, `existing_python/run_sim.py`

---

## Executive Summary

A comprehensive technical audit and live programmatic inspection of the **Smart Grid Stability Monitoring & Automated Fault Diagnostic Platform** was executed. The audit established:
1. **Model Integrity:** `matlab/main_model.slx` is a high-fidelity Simscape Specialized Power Systems model constructed in MATLAB R2025a Update 1. Its 73 blocks, electrical network, multi-stage protection logic, and circuit breaker actuation were fully mapped.
2. **Empirical Simulation Verification:** A live simulation was successfully executed via the Python MATLAB Engine API (`matlabengine 25.1`). The discrete solver completed the 1.0-second transient in **24.25 seconds**, generating **20,005 time-series points** across all **9 expected signal channels**.
3. **Flaws in Existing Scripts:** Major structural and logical discrepancies were identified in `existing_python/app.py` and `existing_python/run_sim.py`. Crucially:
   - In both scripts, `simOut.get('ScopeData')` is invalid because `ReturnWorkspaceOutputs = off` causes Simulink to export `ScopeData` directly into the base MATLAB workspace.
   - Breaker trip logic is inverted in Python.
   - The fault type selector in `app.py` is completely disconnected from Simulink.
   - Target voltage parameter names point to non-existent blocks.
4. **Integration Readiness:** Python 3.12, MATLAB R2025a, and required toolboxes (Simulink, Simscape, Simscape Electrical) are verified and operational. An asynchronous FastAPI + React architecture is recommended to decouple the heavy MATLAB solver from web clients.

---

## 1. MATLAB/Simulink Model Inventory (`matlab/main_model.slx`)

### 1.1 Model & Solver Configuration
* **Simulink Format:** MathWorks R2025a Update 1 (Version 25.1.0.2973910).
* **Simulink Solver Configuration (`simulink/configSet0.xml`):**
  * `SolverName`: `VariableStepAuto`
  * `StartTime`: `0.0 s`, `StopTime`: `1.0 s`
  * `RelTol`: `1e-3`, `AbsTol`: `auto`
  * `ReturnWorkspaceOutputs`: `off` *(Outputs from To Workspace blocks are placed directly in the MATLAB base workspace)*
* **Specialized Power Systems Solver (`powergui`, SID=8):**
  * `SimulationMode`: `Discrete`
  * `SampleTime` ($T_s$): `5e-5 s` ($50\ \mu\text{s}$, giving a $20\ \text{kHz}$ sampling rate and 20,005 simulation steps)
  * `SolverType`: `Tustin/Backward Euler (TBE)`
  * `Fundamental Frequency`: `60 Hz` (Individual grid components set to `50 Hz`)

---

### 1.2 Core Physical & Power Components

| Component | Block Path / SID | Library Source | Configuration & Parameters |
|---|---|---|---|
| **Synchronous Machine** | `main_model/Synchronous Machine pu Standard` (SID=100) | `spsSynchronousMachinepuStandardLib/Synchronous Machine pu Standard` | Nominal: $[10\ \text{MVA},\ 11\ \text{kV},\ 50\ \text{Hz}]$; Rotor: Salient-pole; Units: pu standard; $R_s = 0.037875\ \text{pu}$; Pole Pairs: 20; Mechanical power $P_m$ input driven by `Constant` (SID=102, value 1.0), Field voltage $V_f$ driven by `Constant1` (SID=103, value 1.0). |
| **Three-Phase Transformer** | `main_model/Three-Phase Transformer (Two Windings)` (SID=101) | `spsThreePhaseTransformerTwoWindingsLib/Three-Phase Transformer (Two Windings)` | Nominal Power: $5\ \text{MVA}$, $50\ \text{Hz}$; Primary Winding: $11\ \text{kV}$, $R_1=0.002\ \text{pu}$, $L_1=0.08\ \text{pu}$, Yg; Secondary Winding: $415\ \text{V}$, $R_2=0.002\ \text{pu}$, $L_2=0.08\ \text{pu}$, Yg. |
| **Series RLC Branch** | `main_model/Three-Phase Series RLC Branch` (SID=2) | `spsThreePhaseSeriesRLCBranchLib/Three-Phase Series RLC Branch` | Type: `RL`; Resistance: $0.001\ \Omega$; Inductance: $1\ \text{mH}$; Capacitance: $1\ \mu\text{F}$. |
| **Three-Phase V-I Measurement** | `main_model/Three-Phase V-I Measurement` (SID=7) | `spsThreePhaseVIMeasurementLib/Three-Phase V-I Measurement` | Voltage Measurement: `phase-to-phase`; Current Measurement: `yes`; Output Port 1: $V_{abc}$ (3-phase); Output Port 2: $I_{abc}$ (3-phase). |
| **Three-Phase Fault** | `main_model/Three-Phase Fault` (SID=6) | `spsThreePhaseFaultLib/Three-Phase Fault` | Initial state: `0`; Fault Phases: `FaultA = on`, `FaultB = on`, `FaultC = on`, `GroundFault = on`; Switching Times: `[0.2 0.4]` seconds; External Control: `off`; $R_f = 0.001\ \Omega$, $R_g = 0.01\ \Omega$. |
| **Series VSC Inverters** | `main_model/Series VSC 1` (SID=179) & `Series VSC 2` (SID=180) | `spsUniversalBridgeLib/Universal Bridge` | 3 Arms, Device: IGBT / Diodes, $R_{on} = 10^{-3}\ \Omega$, Snubber: $R=10^5\ \Omega, C=\infty$. Connected back-to-back via DC-link capacitor `Three-Phase Parallel RLC Branch` (SID=181, $C=1\ \mu\text{F}$); Driven by PWM Generators (SID=189, 196) with carrier period $T_{per} = 500\ \mu\text{s}$ ($2\ \text{kHz}$). |
| **Three-Phase Breaker** | `main_model/Three-Phase Breaker` (SID=3) | `spsThreePhaseBreakerLib/Three-Phase Breaker` | Initial State: `closed`; External Control: `on` (Governed dynamically by external logic via input port 1); $R_{on} = 0.001\ \Omega$, Snubber: $1\ \text{M}\Omega$. |
| **PI Section Line** | `main_model/Three-Phase PI Section Line` (SID=4) | `spsThreePhasePISectionLineLib/Three-Phase PI Section Line` | Frequency: $50\ \text{Hz}$, Length: $100\ \text{km}$; $R = [0.01273, 0.3864]\ \Omega/\text{km}$; $L = [0.9337, 4.1264]\ \text{mH}/\text{km}$; $C = [12.74, 7.751]\ \text{nF}/\text{km}$. |
| **Parallel RLC Load** | `main_model/Three-Phase Parallel RLC Load` (SID=114) | `spsThreePhaseParallelRLCLoadLib/Three-Phase Parallel RLC Load` | Nominal Voltage: $11\ \text{kV}$, $50\ \text{Hz}$, Active Power: $500\ \text{MW}$ (Constant Z). |

---

### 1.3 Subsystem Pipeline & Protection Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 Simulink Signal Pipeline                               │
│                                                                                        │
│  [Three-Phase V-I Measurement] (SID=7)                                                 │
│     ├── Vabc (Channels 1..3) ─────────────────────────────────┐                        │
│     └── Iabc (Channels 4..6) ────────────────────┐            │                        │
│                                                  │            │                        │
│  [Signal Processing] (SID=79, Subsystem 89)      │            │                        │
│     ├── Sequence Analyzer (V) ──> Vmag, Vang     │            │                        │
│     └── Sequence Analyzer (I) ──> Imag, Iang     │            │                        │
│                                                  │            │                        │
│  [Fault Detection] (SID=29, Subsystem 40)        │            │                        │
│     ├── OverCurrent: Imag > 10 A                 │            │                        │
│     ├── UnderVoltage: Vmag < 100 V               │            │                        │
│     ├── Startup Blanking: Step(t=0.15s)          │            │                        │
│     └── Output: Fault = (UV & t>0.15) OR         │            │                        │
│                         (OC & t>0.15)            │            │                        │
│                                                  │            │                        │
│  [Protection Logic] (SID=45, Subsystem 51)       │            │                        │
│     ├── S-R Flip-Flop (S=Fault, R=Step t=0.4s)   │            │                        │
│     └── Output: Trip (1 = Trip Active)           │            │                        │
│                                                  │            │                        │
│  [Trip Signal Generator] (SID=55, Subsystem 59)  │            │                        │
│     └── Direct pass-through: Trip_CB             │            │                        │
│                                                  │            │                        │
│  [Data Type Conversion] (SID=71)                 │            │                        │
│     ├── Actuates Three-Phase Breaker (SID=3)     │            │                        │
│     └── Bus Creator (SID=72) Inputs:             │            │                        │
│            Ch 1..3: Vabc                         │            │                        │
│            Ch 4..6: Iabc                         │            │                        │
│            Ch 7:    Trip_CB                      │            │                        │
│            Ch 8:    Vmag                         │            │                        │
│            Ch 9:    Imag                         │            │                        │
│            └──> [To Workspace: ScopeData] (SID=69)            │                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

1. **Signal Processing Subsystem (`main_model/Signal Processing`, SID=79):**
   - Implements two `Sequence Analyzer` blocks (SID=97 for $V_{abc}$, SID=98 for $I_{abc}$) operating at $50\ \text{Hz}$ with $T_s = 50\ \mu\text{s}$.
   - Extracts instantaneous positive-sequence phasor magnitude ($V_{mag}$, $I_{mag}$) and phase angles ($V_{ang}$, $I_{ang}$).
2. **Fault Detection Subsystem (`main_model/Fault Detection`, SID=29):**
   - Compares positive-sequence voltage $V_{mag}$ against `V_thresh` ($100\ \text{V}$, SID=38) via relational operator `<`.
   - Compares positive-sequence current $I_{mag}$ against `I_thresh` ($10\ \text{A}$, SID=39) via relational operator `>`.
   - Gating: A `Step` block (SID=65, $t=0.15\ \text{s}$) suppresses tripping during generator synchronization startup.
   - Generates a high boolean signal `Fault` if either undervoltage or overcurrent persists after $0.15\ \text{s}$.
3. **Protection Logic Subsystem (`main_model/Protection Logic`, SID=45):**
   - Incorporates an `S-R Flip-Flop` (SID=48, initial state = 0).
   - Set ($S$) input is triggered by `Fault`. Latches `Trip = 1` immediately upon fault detection.
   - Reset ($R$) input is driven by a `Step` block (SID=112) at $t = 0.4\ \text{s}$, clearing the trip latch.
4. **Trip Signal Generator Subsystem (`main_model/Trip Signal Generator`, SID=55):**
   - Passes the trip command directly to `Trip_CB`.
5. **Circuit Breaker Actuation & ScopeData Logging:**
   - `Trip_CB` passes through `Data Type Conversion` (boolean to double, SID=71) and commands `Three-Phase Breaker` (SID=3) external control input.
   - Fed into input 3 of `Bus Creator` (SID=72).
   - Output from `Bus Creator` feeds into `To Workspace` (SID=69), configured with `VariableName = ScopeData` and `SaveFormat = Structure With Time`.

---

## 2. Python Integration Findings

### 2.1 Critical Bug: ScopeData Retrieval Failure
Both `existing_python/app.py` (line 77) and `existing_python/run_sim.py` (line 19) contain the following command:
```python
eng.eval("scopeObj = simOut.get('ScopeData');", nargout=0)
```
**Root Cause Identified:**  
In `main_model.slx`, the model configuration parameter `ReturnWorkspaceOutputs` is explicitly set to `'off'`. When this setting is off, MATLAB's `sim('main_model')` returns only a numerical time array (`tout`), **not** a `Simulink.SimulationOutput` object. Consequently, `simOut` is a double vector, causing `simOut.get('ScopeData')` to crash with:
```
matlab.engine.MatlabExecutionError: Dot indexing is not supported for variables of this type.
```
**Fix:** `ScopeData` is written directly into the MATLAB base workspace. In Python, it must be accessed via:
```python
eng.eval("scopeObj = ScopeData;", nargout=0)
# or directly via the workspace dictionary:
scope_obj = eng.workspace['ScopeData']
```

---

### 2.2 Analysis of `existing_python/app.py` (Streamlit Prototype)
* **Disconnected Fault Type Selector:**  
  The UI offers a dropdown with `["Single Line-to-Ground (AG)", "Line-to-Line (AB)", "Three-Phase Fault (ABC)"]`. However, the execution loop only updates `FaultResistance` and **never modifies** `FaultA`, `FaultB`, `FaultC`, or `GroundFault`. The simulation runs as an ABCG fault regardless of user selection.
* **Non-Existent Voltage Block Name:**  
  The script attempts to set parameters on `Three-Phase Programmable Voltage Source`. This block does not exist in `main_model.slx` (which utilizes `Synchronous Machine pu Standard` and a transformer). The error is swallowed by a bare `try...except`, leaving voltage controls completely ineffective.
* **Open-Loop Synthetic Power Estimates:**  
  Real power ($P$) and reactive power ($Q$) are calculated using Python arithmetic ($P = S \times \text{pf}$, $Q = S \times \sin(\arccos(\text{pf}))$) rather than physical integration of measured voltage and current signals.
* **Inverted Breaker Condition:**  
  The script evaluates `is_faulted = np.any(trip_signal < 0.5)`. In Simulink, `0` is the normal closed state and `1` is the tripped state. As a result, `trip_signal < 0.5` is always true under healthy conditions, causing persistent false alarms.

---

### 2.3 Analysis of `existing_python/run_sim.py` (Standalone Runner)
* **Cold-Start Performance Penalty:**  
  Spawns and closes a new MATLAB engine instance on every run, requiring ~100–120 seconds of initialization overhead.
* **Inverted Y-Axis Breaker Labels:**  
  Labels $y$-axis ticks as `0 (Trip/Open)` and `1 (Closed)`. The model's actual output is $0 = \text{Closed}$ and $1 = \text{Tripped/Open}$.
* **Hardcoded Overlay Annotations:**  
  Highlights the region `0.2s - 0.6s` with `ax.axvspan` without inspecting actual simulation switching parameters.

---

## 3. Compatibility Report

| Environment Element | Detected Specification | Compatibility Status | Notes |
|---|---|---|---|
| **Operating System** | Windows 11 (64-bit) | Verified | Host platform. |
| **MATLAB Version** | R2025a Update 1 (25.1.0.2973910) | Compatible | Installed at `C:\Program Files\MATLAB\R2025a`. |
| **Python Version** | Python 3.12.7 (64-bit) | Compatible | Fully supported by MATLAB Engine for R2025a. |
| **MATLAB Engine Package** | `matlabengine==25.1` | Verified & Operational | Successfully imported and communicating with MATLAB. |
| **Installed Toolboxes** | 112 Toolboxes Detected | Verified | Includes Simulink, Simscape, and Simscape Electrical (`sps_lib`). |
| **Existing Python Libraries** | `numpy 2.5.2`, `matplotlib 3.11.1`, `scipy 1.18.1`, `streamlit 1.62.0` | Verified | Operational in Python 3.12 environment. |
| **Backend API Framework** | `fastapi` | **MISSING** | Required for modern production API. Not yet installed. |

---

## 4. Signal Mapping & Empirical Simulation Verification

A complete end-to-end simulation of `main_model.slx` was executed programmatically from Python. The results below reflect **actual numerical outputs** computed by the Simulink solver:

* **Simulation Execution Time:** `24.25 seconds`
* **Time Vector Length:** `20,005 samples` ($0.0000\ \text{s}$ to $1.0000\ \text{s}$, step $50\ \mu\text{s}$)
* **Signals Matrix Dimensions:** `20,005 rows × 9 columns`

### 4.1 Channel Data Audit

| Ch # | Signal Designation | Source Block & Port | Min Measured | Max Measured | Mean Measured | Behavior During Fault |
|---|---|---|---|---|---|---|
| `0` | Phase A Voltage ($V_a$) | `Three-Phase V-I Measurement` [Port 1] | $-1532.18\ \text{V}$ | $+1529.09\ \text{V}$ | $+0.47\ \text{V}$ | Collapses near 0 V at $t=0.2\ \text{s}$ |
| `1` | Phase B Voltage ($V_b$) | `Three-Phase V-I Measurement` [Port 1] | $-2081.17\ \text{V}$ | $+5013.73\ \text{V}$ | $-0.66\ \text{V}$ | Distorts with severe harmonic spikes |
| `2` | Phase C Voltage ($V_c$) | `Three-Phase V-I Measurement` [Port 1] | $-4597.62\ \text{V}$ | $+1529.17\ \text{V}$ | $+0.19\ \text{V}$ | Undergoes transient negative excursion |
| `3` | Phase A Current ($I_a$) | `Three-Phase V-I Measurement` [Port 2] | $-351.06\ \text{A}$ | $+622.32\ \text{A}$ | $+29.41\ \text{A}$ | Fault surge reaches $622\ \text{A}$ peak |
| `4` | Phase B Current ($I_b$) | `Three-Phase V-I Measurement` [Port 2] | $-269.39\ \text{A}$ | $+743.84\ \text{A}$ | $+49.45\ \text{A}$ | Fault surge reaches $743\ \text{A}$ peak |
| `5` | Phase C Current ($I_c$) | `Three-Phase V-I Measurement` [Port 2] | $-908.31\ \text{A}$ | $+163.18\ \text{A}$ | $-77.21\ \text{A}$ | Peak inrush surge reaches $-908\ \text{A}$ |
| `6` | Breaker Trip ($Trip\_CB$) | `Trip Signal Generator` [Port 1] | $0.00$ | $1.00$ | $0.20$ | Latches to `1.0` at $t=0.2005\ \text{s}$, resets at $t=0.4000\ \text{s}$ |
| `7` | Voltage Magnitude ($V_{mag}$) | `Signal Processing` [Port 1] | $0.52\ \text{V}$ | $264.65\ \text{V}$ | $190.28\ \text{V}$ | Steady state $\approx 240\ \text{V}$, drops to $0.52\ \text{V}$ |
| `8` | Current Magnitude ($I_{mag}$) | `Signal Processing` [Port 3] | $0.25\ \text{A}$ | $461.88\ \text{A}$ | $103.77\ \text{A}$ | Steady state $\approx 1.5\ \text{A}$, surges to $461.88\ \text{A}$ |

### 4.2 Verified Protection Timing Dynamics
* **Fault Inception:** $t = 0.2000\ \text{s}$ (Simulink fault block active).
* **Trip Latch Trigger:** $t = 0.2005\ \text{s}$ (Protection logic trips within **$0.5\ \text{ms}$** of fault onset once $I_{mag} > 10\ \text{A}$).
* **Trip Clearing & Reset:** $t = 0.4000\ \text{s}$ (Reset step input activates, clearing breaker latch).
* **Total Trip Interval:** **$0.1995\ \text{seconds}$** ($199.5\ \text{ms}$).

---

## 5. Audit of Previously Identified Issues

| # | Investigation Item | Detailed Finding | Verdict |
|---|---|---|---|
| **1** | Does changing the fault type actually change the Simulink fault configuration? | `app.py` has UI options for AG, AB, and ABC faults, but never issues `set_param` commands for `FaultA`, `FaultB`, `FaultC`, or `GroundFault`. The model always simulates an ABCG fault. | **ISSUE FOUND** |
| **2** | Are the voltage and power-factor controls connected to the simulation? | The script attempts to modify `Three-Phase Programmable Voltage Source`, which does not exist in `main_model.slx`. The call fails silently inside `try...except`. The power factor slider is purely a post-processing arithmetic scalar in Python. | **ISSUE FOUND** |
| **3** | Are P and Q measured or merely estimated? | Real and reactive powers are synthetic numbers computed via $P = S \times \text{pf}$ and $Q = S \times \sin(\arccos(\text{pf}))$ in Python, rather than derived from solver waveforms. | **ISSUE FOUND** |
| **4** | Is the breaker status correctly interpreted? | Both scripts invert breaker logic: `run_sim.py` marks `0` as Trip/Open and `1` as Closed; `app.py` treats `trip_signal < 0.5` as a fault. In the model, `0` is Closed (healthy) and `1` is Tripped (latched open). | **ISSUE FOUND** |
| **5** | Are fault times hard-coded? | Fault switching times are hardcoded to `[0.2 0.4]` in `Three-Phase Fault` and latch reset is hardcoded to $0.4\ \text{s}$ in `Protection Logic`. Plot spans are hardcoded to `0.2 - 0.6 s`. | **ISSUE FOUND** |
| **6** | Are all nine expected `ScopeData` signals present? | Verified empirically: `Bus Creator` combines 3 voltage phases, 3 current phases, 1 breaker status, and 2 sequence magnitudes. All 9 channels exist in `ScopeData` across 20,005 samples. | **VERIFIED** |
| **7** | Are any simulation errors being silently ignored? | In `app.py`, block parameter errors are caught by bare `except:` blocks that print warnings to stdout and continue. Simulation solver calls lack structured exception handling. | **ISSUE FOUND** |

---

## 6. Recommended Fixes

1. **Fix ScopeData Extraction:**  
   Retrieve `ScopeData` directly from the MATLAB base workspace:
   ```python
   scope_data = eng.workspace['ScopeData']
   time = np.array(scope_data['time']).flatten()
   values = np.array(scope_data['signals']['values'])
   ```
2. **Dynamic Fault Type Mapping:**  
   Implement a clean translation function in Python:
   ```python
   fault_config = {
       "AG":  {"FaultA": "on",  "FaultB": "off", "FaultC": "off", "GroundFault": "on"},
       "AB":  {"FaultA": "on",  "FaultB": "on",  "FaultC": "off", "GroundFault": "off"},
       "ABC": {"FaultA": "on",  "FaultB": "on",  "FaultC": "on",  "GroundFault": "off"},
       "ABCG":{"FaultA": "on",  "FaultB": "on",  "FaultC": "on",  "GroundFault": "on"},
   }
   for param, val in fault_config[selected_fault].items():
       eng.set_param("main_model/Three-Phase Fault", param, val, nargout=0)
   ```
3. **Correct Voltage Source Parameterization:**  
   Bind primary voltage to the transformer primary winding (`Winding1`) or the Synchronous Machine nominal parameters:
   ```python
   eng.set_param("main_model/Three-Phase Transformer (Two Windings)", "Winding1", f"[{v_primary}, 0.002, 0.08]", nargout=0)
   ```
4. **Instantaneous Physical Power Calculations:**  
   Compute active and reactive powers directly from simulation arrays in Python:
   $$p(t) = v_a(t) i_a(t) + v_b(t) i_b(t) + v_c(t) i_c(t)$$
   $$q(t) = \frac{1}{\sqrt{3}} \left[(v_b(t) - v_c(t)) i_a(t) + (v_c(t) - v_a(t)) i_b(t) + (v_a(t) - v_b(t)) i_c(t)\right]$$
5. **Standardized Breaker State Interpretation:**  
   Standardize logic across the backend and frontend:
   - `trip_signal == 0`: Breaker CLOSED / Normal Operation.
   - `trip_signal == 1`: Breaker OPEN / Fault Isolated / Trigger Alarm.

---

## 7. Recommended Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 React Frontend (Vite / Next.js)             │
│   - Parameter Input Panel (R, L, C, Fault Type, Rf, Times)  │
│   - Interactive Canvas Waveform Plots (Plotly / Chart.js)   │
│   - Telemetry KPIs (RMS V/I, True P/Q, Frequency, PF)       │
│   - Live Circuit Breaker Status & Audio Alarm System        │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / WebSocket (JSON)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Asynchronous Backend Layer          │
│   - Input Validation & Boundary Enforcement (Pydantic)      │
│   - Singleton MATLAB Engine Session Manager                 │
│   - Signal Post-Processing (Symmetrical components, FFT)    │
│   - Downsampling / Decimation for Fast Browser Streaming    │
└──────────────────────────────┬──────────────────────────────┘
                               │ Python MATLAB Engine API
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               Persistent MATLAB Engine Session              │
│   - Pre-loaded 'main_model.slx'                             │
│   - Zero startup latency per request                        │
│   - set_param parameter manipulation                        │
│   - Solver execution: sim('main_model')                     │
│   - Direct workspace ScopeData extraction                   │
└─────────────────────────────────────────────────────────────┘
```

### MATLAB Engine Session Management
Starting a fresh MATLAB engine requires ~20–30 seconds. To deliver responsive web performance:
- Maintain a **persistent singleton MATLAB Engine** in the FastAPI backend lifecycle (`@asynccontextmanager lifespan`).
- Pre-load `main_model.slx` during backend startup.
- In-memory simulation runs take ~24 seconds without engine restart overhead.

---

## 8. Step-by-Step Phase 3 Implementation Plan

### Step 1: Python Backend Infrastructure (`backend/`)
1. Create `backend/requirements.txt` containing `fastapi`, `uvicorn`, `pydantic`, `numpy`, `scipy`.
2. Implement `backend/matlab_session.py`:
   - Singleton class managing the persistent MATLAB engine.
   - Lifespan startup: starts MATLAB, adds `matlab/` to path, preloads `main_model.slx`.
   - Lifespan shutdown: cleanly closes model and quits engine.

### Step 2: Parameter Mapper & Simulation Runner
1. Create `backend/sim_runner.py`:
   - Validates input parameters (line resistance $R$, inductance $L$, capacitance $C$, fault type, fault resistance $R_f$).
   - Dynamically updates Simulink block parameters via `eng.set_param`.
   - Executes `eng.eval("sim('main_model');", nargout=0)`.
   - Extracts `ScopeData` from MATLAB base workspace.
   - Returns structured NumPy arrays.

### Step 3: Analytics & Signal Processing Engine
1. Create `backend/analytics.py`:
   - Calculates instantaneous and average active power $P$ and reactive power $Q$.
   - Calculates power factor $\text{pf} = P / S$.
   - Detects fault inception timestamp, breaker tripping timestamp, and clearing duration.
   - Downsamples 20,005 waveform samples to ~1,000 points using Min-Max decimation for lightweight browser transmission.

### Step 4: FastAPI REST & WebSocket Endpoints
1. Create `backend/main.py`:
   - `POST /api/simulate`: Accepts grid parameters, runs model, returns waveforms and metrics.
   - `GET /api/status`: Returns MATLAB Engine health and model status.
   - `GET /api/default-params`: Returns nominal grid parameters.

### Step 5: Modern React Frontend Application (`frontend/`)
1. Initialize Vite React application with modern styling (dark mode, glassmorphism dashboard).
2. Build interactive control sidebar for transmission line parameters and fault injection.
3. Build multi-panel interactive waveform viewer for $V_{abc}$, $I_{abc}$, $Trip$, $V_{mag}$, $I_{mag}$, and True Power $P/Q$.
4. Implement breaker status indicator with automatic audio and visual trip alerts.
