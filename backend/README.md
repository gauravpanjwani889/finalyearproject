# Smart Grid Stability Monitoring & Automated Fault Diagnostic Platform
## Python Backend Service (`backend/`)

This directory contains the production-grade Python backend service connecting modern web interfaces to the authoritative **MATLAB R2025a / Simulink** power systems simulation engine (`matlab/main_model.slx`).

---

## 1. System Architecture

```
┌────────────────────────────────┐
│      React Web Frontend        │ (Interactive Controls, Time-series Charts, Alarms)
└───────────────┬────────────────┘
                │ HTTP / WebSocket (JSON)
                ▼
┌────────────────────────────────┐
│      FastAPI Backend Layer     │ (`backend/main.py`, `backend/routes.py`)
│  - Request Validation (Pydantic)│
│  - Run-specific Result Store   │
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│   Simulation Service Layer     │ (`backend/sim_runner.py`)
│  - Dynamic Parameter Mapping   │
│  - Concurrency Lock (asyncio)  │
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│  MATLAB Engine Session Manager │ (`backend/matlab_engine.py`)
│  - Persistent Singleton Session│
│  - Zero Startup Latency        │
└───────────────┬────────────────┘
                │ MATLAB Engine API 25.1
                ▼
┌────────────────────────────────┐
│  Simulink Discrete Solver Engine│ (`matlab/main_model.slx`)
│  - Powergui Discrete Ts=50us   │
│  - Synchronous Machine, RLC,   │
│    VSC Inverters, Breaker, Relays│
└───────────────┬────────────────┘
                │ ScopeData Output Structure
                ▼
┌────────────────────────────────┐
│   Electrical Analytics Engine  │ (`backend/analytics.py`)
│  - Instantaneous Active Power P│
│  - Akagi Clarke Transform Q    │
│  - True RMS & Disturbance Ratio│
│  - Peak-Preserving Decimation  │
└────────────────────────────────┘
```

---

## 2. Prerequisites & Environment Setup

* **Operating System:** Windows 10/11 64-bit
* **MATLAB Release:** MATLAB R2025a Update 1 (25.1.0.2973910)
  * Required Toolboxes: Simulink, Simscape, Simscape Electrical (`sps_lib`)
* **Python Runtime:** Python 3.12.7 (64-bit)
* **Python MATLAB Engine:** `matlabengine==25.1`

### Installation

```bash
# Navigate to project root
cd Smart_Grid_Automation

# Install backend dependencies
python -m pip install -r backend/requirements.txt
```

---

## 3. Verified Fault Configurations

The backend translates UI fault selections directly into verified block parameters on `main_model/Three-Phase Fault`:

| UI Fault Selection | `FaultA` | `FaultB` | `FaultC` | `GroundFault` | Description |
|---|---|---|---|---|---|
| `NORMAL` | `off` | `off` | `off` | `off` | Healthy grid operation (no fault injected) |
| `AG` | `on` | `off` | `off` | `on` | Single Line-to-Ground fault (Phase A to Ground) |
| `AB` | `on` | `on` | `off` | `off` | Line-to-Line fault (Phase A to Phase B) |
| `ABC` | `on` | `on` | `on` | `off` | Symmetrical Three-Phase fault |
| `ABCG` | `on` | `on` | `on` | `on` | Symmetrical Three-Phase-to-Ground fault |

Additionally, fault resistance ($R_f$) and ground resistance ($R_g$) are dynamically applied to the `Three-Phase Fault` block for each run.

---

## 4. Signal Mapping (`ScopeData`)

The Simulink solver logs 20,005 samples across 9 synchronized channels:

| Index | Signal | Description | Units | Normal Behavior | Fault Behavior |
|---|---|---|---|---|---|
| `0` | $V_a$ | Phase A Voltage | V | Sinusoidal ~415 V line-to-line | Sags near 0 V |
| `1` | $V_b$ | Phase B Voltage | V | Sinusoidal ~415 V | Distorts / spikes |
| `2` | $V_c$ | Phase C Voltage | V | Sinusoidal ~415 V | Undergoes transient excursion |
| `3` | $I_a$ | Phase A Current | A | Nominal load current ~10–20 A | Surges to hundreds of Amperes |
| `4` | $I_b$ | Phase B Current | A | Nominal load current | Surges depending on fault type |
| `5` | $I_c$ | Phase C Current | A | Nominal load current | Surges depending on fault type |
| `6` | $Trip$ | Circuit Breaker Status | Binary | `0` (Closed / Healthy) | `1` (Tripped / Open) |
| `7` | $V_{mag}$ | Sequence Voltage Magnitude | V | Steady state ~190–240 V | Collapses below 100 V |
| `8` | $I_{mag}$ | Sequence Current Magnitude | A | Steady state ~1.5 A | Surges above 10 A threshold |

---

## 5. Electrical Analytics & Calculation Methods

1. **Instantaneous 3-Phase Active Power ($p(t)$):**
   $$p(t) = v_a(t) i_a(t) + v_b(t) i_b(t) + v_c(t) i_c(t)\quad [\text{W}]$$
2. **Instantaneous Reactive Power ($q(t)$):**
   Computed via orthogonal Clarke coordinates ($\alpha\beta$ frame per Akagi's theory):
   $$v_\alpha = \sqrt{\frac{2}{3}} \left(v_a - \frac{1}{2} v_b - \frac{1}{2} v_c\right),\quad v_\beta = \sqrt{\frac{2}{3}} \left(\frac{\sqrt{3}}{2} v_b - \frac{\sqrt{3}}{2} v_c\right)$$
   $$i_\alpha = \sqrt{\frac{2}{3}} \left(i_a - \frac{1}{2} i_b - \frac{1}{2} i_c\right),\quad i_\beta = \sqrt{\frac{2}{3}} \left(\frac{\sqrt{3}}{2} i_b - \frac{\sqrt{3}}{2} i_c\right)$$
   $$q(t) = v_\beta(t) i_\alpha(t) - v_\alpha(t) i_\beta(t)\quad [\text{VAR}]$$
3. **Pre-Fault & Fault Window RMS:**
   Pre-fault interval: $t \in [0.05, 0.18]\ \text{s}$; Fault interval: $t \in [0.21, 0.38]\ \text{s}$.
   $$V_{\text{RMS}} = \sqrt{\frac{1}{N} \sum_{k=1}^N v(k)^2}$$
4. **Protection Dynamics:**
   - Fault onset: First timestamp where $I_{mag} > 10\ \text{A}$ or $V_{mag} < 100\ \text{V}$ after $t > 0.15\ \text{s}$.
   - Breaker trip time: Timestamp where $Trip \ge 0.5$.
   - Fault-to-trip delay: $(t_{\text{trip}} - t_{\text{fault}}) \times 1000\ \text{ms}$.
   - Trip duration: $(t_{\text{reset}} - t_{\text{trip}}) \times 1000\ \text{ms}$.
5. **Peak-Preserving Decimation:**
   Min-Max envelope downsampling algorithm converts 20,005 raw points to ~1,000 points while guaranteeing that sharp transient current spikes and voltage collapses are 100% preserved for web visualization.

---

## 6. API Reference

### `GET /api/health`
Checks server health and persistent MATLAB engine session state.

### `GET /api/model/info`
Returns technical model specifications, sample rate, solver parameters, and signal channels.

### `GET /api/model/parameters`
Returns parameter limits and nominal defaults for transmission line impedance and fault injection.

### `POST /api/simulation/run`
Executes an authoritative Simulink simulation.
**Request Body:**
```json
{
  "fault_type": "AG",
  "fault_resistance": 0.001,
  "ground_resistance": 0.01,
  "line_resistance": 0.001,
  "line_inductance": 0.001,
  "line_capacitance": 0.000001,
  "downsample_points": 1000,
  "include_full_waveform": false
}
```

### `GET /api/simulation/results/{run_id}`
Retrieves cached telemetry and waveform data from a previous simulation run.

---

## 7. Starting the Backend Server

```bash
# From workspace root:
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
Open interactive OpenAPI documentation in browser: `http://localhost:8000/docs`
