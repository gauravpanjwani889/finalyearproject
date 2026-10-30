# Smart Grid Stability Monitoring & Automated Fault Diagnostic Platform

## 1. Project Objective

The **Smart Grid Stability Monitoring & Automated Fault Diagnostic Platform** is an intelligent industrial engineering platform designed for real-time grid stability assessment, transmission line parameter analysis, and automated fault detection, classification, and isolation.

The platform bridges power systems physics and modern web technologies by coupling high-fidelity electrical dynamics modeled in **MATLAB/Simulink** with an interactive web dashboard via an asynchronous Python backend.

---

## 2. Core Architectural Pipeline

> **Core Requirement:** MATLAB/Simulink serves as the core simulation engine. All analytics, waveform graphs, alarms, and diagnostics presented on the web dashboard reflect genuine numerical outputs computed by the Simulink solver.

```
┌────────────────────────┐
│  Modern Web Frontend   │ (Browser UI: Parameters, Controls, Charts, Alarms)
└───────────┬────────────┘
            │ HTTP / WebSocket (JSON)
            ▼
┌────────────────────────┐
│     Python Backend     │ (FastAPI / Server Layer)
└───────────┬────────────┘
            │ Python MATLAB Engine API (`matlab.engine`)
            ▼
┌────────────────────────┐
│   Simulink Simulation  │ (`main_model.slx` Solver Engine)
│        Engine          │ (Programmable Sources, R-L-C Lines, Fault Blocks)
└───────────┬────────────┘
            │ Simulation Output Structures (`ScopeData`, Signals)
            ▼
┌────────────────────────┐
│  Python Data Pipeline  │ (NumPy / SciPy Signal Processing & Fault Classifier)
└───────────┬────────────┘
            │ Serialized Simulation Results & Telemetry
            ▼
┌────────────────────────┐
│ Web Visualizations &   │ (Phase Waveforms, RMS Trends, Trip Logic, Metrics)
│ Live Fault Diagnostics │
└────────────────────────┘
```

### Execution Flow Details
1. **Website (Frontend)**: Operators configure physical grid parameters (primary/secondary voltages, line impedance $R, L, C$, fault types like AG, AB, ABC, fault resistances $R_f$) and trigger simulations or fault injections.
2. **Python Backend**: Receives operator inputs, validates parameter boundaries, and orchestrates calls to the MATLAB session via `matlab.engine`.
3. **MATLAB Engine API**: Dynamically updates Simulink block parameters (`set_param`) and executes the simulation run (`sim('main_model')`).
4. **Simulink Model (`main_model.slx`)**: Solves differential equations for multi-phase electrical networks, protective relay logic, and circuit breaker trip dynamics.
5. **Simulation Results Extraction**: Time-series telemetry ($V_{abc}$, $I_{abc}$, trip status, $V_{mag}$, $I_{mag}$, etc.) are extracted from the MATLAB workspace into Python NumPy arrays.
6. **Backend Processing & Diagnostics**: Computes symmetrical components, fault inception times, clearing intervals, and health indices.
7. **Website Visualizations**: High-framerate interactive plots, status indicators, and trip alarms render live simulation results for the operator.

---

## 3. Directory Structure

```text
Smart_Grid_Automation/
│
├── matlab/
│   └── main_model.slx                    # [PRESERVED UNTOUCHED] Core Simulink power system model
│
├── backend/                              # [COMPLETED - Phase 3] Production Python FastAPI backend
│   ├── config.py                         # Paths, solver constants, and server settings
│   ├── models.py                         # Pydantic schemas (requests, responses, waveforms)
│   ├── matlab_engine.py                  # Singleton persistent MATLAB Engine session manager
│   ├── sim_runner.py                     # Parameter mapper & Simulink execution runner
│   ├── analytics.py                      # Clarke p-q theory, true RMS, timing, decimation
│   ├── routes.py                         # REST API routes (/health, /model/*, /simulation/*)
│   ├── main.py                           # FastAPI entrypoint with lifespan manager
│   └── requirements.txt                  # Backend Python dependencies
│
├── frontend/                             # [COMPLETED - Phase 4A] Production React TypeScript dashboard
│   ├── src/
│   │   ├── components/                   # Navbar, KpiCard, NetworkSchematic, WaveformChart
│   │   ├── views/                        # OverviewView, ControlsView, WaveformsView, DiagnosticsView, HistoryView
│   │   ├── services/api.ts               # Typed REST API service connecting to backend proxy
│   │   ├── types/index.ts                # TypeScript interfaces matching backend models
│   │   ├── App.tsx                       # Main application shell with tab state
│   │   └── index.css                     # Dark industrial grid styling with Tailwind CSS
│   ├── package.json                      # React 18, Vite 5, Tailwind 3, ECharts 5
│   └── vite.config.ts                    # Vite config with /api proxy to FastAPI backend
│
├── tests/                                # Automated verification test suites
│   ├── test_integration.py               # 12-point backend integration test suite
│   ├── verify_backend_api.py             # Phase 1 backend verification test script
│   └── test_frontend_integration.py      # End-to-end frontend proxy and simulation test
│
├── existing_python/                      # [PRESERVED UNTOUCHED] Original prototype scripts
│   ├── app.py
│   └── run_sim.py
│
├── reference/                            # Foundational academic documentation
│   ├── Smart_Grid_Project_Report.docx
│   └── IEEE_Research_Paper.pdf
│
├── TECHNICAL_AUDIT.md                    # Phase 2 audit report
├── INTEGRATION_STATUS.md                 # Phase 3 integration report
├── FRONTEND_STATUS.md                    # Phase 4A frontend delivery report
└── README.md                             # Master repository documentation
```

---

## 4. Quickstart: Running the Web Platform

### Prerequisites
* **Operating System:** Windows 10/11 64-bit
* **MATLAB Release:** MATLAB R2025a Update 1 with Simulink & Simscape Electrical
* **Python Runtime:** Python 3.12 (with `fastapi`, `uvicorn`, `matlabengine==25.1`, `httpx`, `numpy`, `scipy`)
* **Node.js:** Node.js v20+ with `npm`

### Step 1: Start the Python FastAPI Backend
Open a terminal in the project root:
```powershell
cd c:\Users\smadh\.gemini\antigravity-ide\scratch\Smart_Grid_Automation
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
*(On boot, the backend initializes the persistent MATLAB Engine and preloads `main_model.slx`)*

### Step 2: Start the React Frontend Dashboard
Open a second terminal:
```powershell
cd c:\Users\smadh\.gemini\antigravity-ide\scratch\Smart_Grid_Automation\frontend
npm run dev -- --host 127.0.0.1 --port 3000
```

### Step 3: Open in Browser
Navigate to **`http://127.0.0.1:3000`** to access the dashboard.

