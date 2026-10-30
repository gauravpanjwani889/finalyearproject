# Comprehensive Electrical Parameter Mapping & Verification Specification

**Project:** Smart Grid Stability Monitoring & Automated Fault Diagnostic Platform  
**Target Simulink Model:** `matlab/main_model.slx`  
**Execution Environment:** MATLAB R2025a Update 1 Engine API for Python / FastAPI Backend  

---

## 1. Overview & Verification Principle

To guarantee electrical authenticity, parameter controls on the React website must map to genuine physical components in the Simulink model and must be confirmed through programmatic readback (`get_param`).

A parameter is **never** considered functional merely because the API accepts it or because a cosmetic multiplier was applied in Python. The workflow enforced in this platform is:

```
[Web User / React UI]
        │
        ▼ (HTTP POST /api/simulation/run)
[FastAPI Backend / SimulationRunner]
        │
        ├── 1. Validate physical ranges & dimensions
        ├── 2. eng.set_param(BLOCK_PATH, PARAM_NAME, STR_VALUE)
        ├── 3. READBACK: eng.get_param(BLOCK_PATH, PARAM_NAME)
        ├── 4. Verify Readback matches Written configuration
        ├── 5. Execute sim('main_model')
        ├── 6. Extract ScopeData from MATLAB workspace
        └── 7. Restore baseline default parameters via _restore_defaults_sync()
```

---

## 2. Complete Component-to-Simulink Block Mapping

### A. Synchronous Machine (Generator) & Excitation Controls

| Parameter Name | Electrical Unit | Supported Range | Default Nominal | Simulink Block Path | Simulink Parameter Name | Format / Internal Conversion |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Rated Apparent Power ($S_n$)** | MVA | $1.0\ \text{to}\ 100.0$ | $10.0$ | `main_model/Synchronous Machine pu Standard` (SID=100) | `NominalParameters` | Vector: `[Sn*1e6 Vn*1e3 50]` |
| **Rated Voltage ($V_n$)** | kV (L-L RMS) | $1.0\ \text{to}\ 33.0$ | $11.0$ | `main_model/Synchronous Machine pu Standard` (SID=100) | `NominalParameters` | Second element of `NominalParameters` |
| **Field Excitation Setpoint ($V_f$)** | per-unit (pu) | $0.5\ \text{to}\ 1.5$ | $1.0$ | `main_model/Constant1` (SID=105) | `Value` | String scalar: `"1.0"` |
| **Turbine Mechanical Power ($P_m$)** | per-unit (pu) | $0.1\ \text{to}\ 1.5$ | $1.0$ | `main_model/Constant` (SID=104) | `Value` | String scalar: `"1.0"` |
| **Nominal Frequency ($f_n$)** | Hz | $50.0$ (fixed) | $50.0$ | `main_model/Synchronous Machine pu Standard` | `NominalParameters` | Third element: `50` (system-wide base) |

#### Physical Significance
- **Rating vs Terminal Voltage:** $S_n$ sets the internal per-unit impedance base ($Z_{\text{base}} = V_n^2 / S_n$). Terminal voltage dynamic swing is governed by excitation field voltage $V_f$ and stator armature reaction.
- **Excitation Control ($V_f$):** Modifying $V_f$ shifts the machine open-circuit excitation EMF ($E_f$), increasing or decreasing reactive power export capability into the 11 kV grid.

---

### B. Substation Step-Down Transformer Controls

| Parameter Name | Electrical Unit | Supported Range | Default Nominal | Simulink Block Path | Simulink Parameter Name | Format / Internal Conversion |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Transformer Rated Power ($S_{\text{trafo}}$)** | MVA | $0.5\ \text{to}\ 50.0$ | $5.0$ | `main_model/Three-Phase Transformer (Two Windings)` (SID=101) | `NominalPower` | Vector: `[S_trafo*1e6 50]` |
| **Primary Nominal Voltage ($V_1$)** | kV (L-L RMS) | $1.0\ \text{to}\ 33.0$ | $11.0$ | `main_model/Three-Phase Transformer (Two Windings)` | `Winding1` | Vector: `[V1*1e3 0.002 0.08]` |
| **Secondary Nominal Voltage ($V_2$)** | V (L-L RMS) | $100.0\ \text{to}\ 11000.0$ | $415.0$ | `main_model/Three-Phase Transformer (Two Windings)` | `Winding2` | Vector: `[V2 0.002 0.08]` |
| **Winding Resistances ($R_1, R_2$)** | per-unit (pu) | Fixed base | $0.002$ | `main_model/Three-Phase Transformer (Two Windings)` | `Winding1`, `Winding2` | Inherent per-unit copper loss base |
| **Winding Inductances ($L_1, L_2$)** | per-unit (pu) | Fixed base | $0.08$ | `main_model/Three-Phase Transformer (Two Windings)` | `Winding1`, `Winding2` | Inherent per-unit leakage reactance base |

#### Physical Significance
- **Turns Ratio:** The winding voltage configuration establishes the ideal voltage transformation ratio $a = V_1 / V_2 = 11000 / 415 = 26.5$.
- Modifying $V_2$ alters the secondary open-circuit voltage driving the downstream series branch and VSC bus.

---

### C. Parallel RLC Load & Power Factor Controls

| Parameter Name | Electrical Unit | Supported Range | Default Nominal | Simulink Block Path | Simulink Parameter Name | Format / Internal Conversion |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Active Load Demand ($P$)** | MW | $0.1\ \text{to}\ 2000.0$ | $500.0$ | `main_model/Three-Phase Parallel RLC Load` (SID=114) | `ActivePower` | String: `str(P * 1e6)` (Watts) |
| **Operational Power Factor ($\cos \phi$)** | scalar (lagging) | $0.50\ \text{to}\ 1.00$ | $1.00$ | Derived UI Control | N/A | Drives $Q = P \times \tan(\arccos(\text{pf}))$ |
| **Reactive Load Demand ($Q$)** | MVAR | $0.0\ \text{to}\ 1500.0$ | $0.0$ | `main_model/Three-Phase Parallel RLC Load` | `InductivePower` | String: `str(Q * 1e6)` (VAR) |
| **Nominal Voltage Rating** | V | Fixed nominal | $11000$ | `main_model/Three-Phase Parallel RLC Load` | `NominalVoltage` | Fixed at $11000\ \text{V}$ |

#### Physical Significance
- **Authentic Power Factor Formulation:** Power factor changes are **not** simulated via arbitrary Python multipliers. When the user selects a lagging power factor (e.g., $0.85$), the system mathematically evaluates:
  $$\phi = \arccos(0.85) = 31.79^\circ$$
  $$Q = P \times \tan(\phi) = 500\ \text{MW} \times 0.6197 = 309.87\ \text{MVAR}$$
  and sets `InductivePower` directly in the Simscape load block, creating genuine inductive current lag and reactive voltage drop.

---

### D. Transmission Line Feeder Controls

The platform clearly distinguishes the physical roles of the lumped series branch and the distributed transmission line:

| Component Role | Simulink Block Path | Parameter Name | Electrical Unit | Supported Range | Default Nominal |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Lumped Series Branch (Substation Feeder)** | `main_model/Three-Phase Series RLC Branch` (SID=2) | `Resistance` | Ohms ($\Omega$) | $0.0001\ \text{to}\ 10.0$ | $0.001$ |
| **Lumped Series Branch (Substation Feeder)** | `main_model/Three-Phase Series RLC Branch` (SID=2) | `Inductance` | Henrys (H) | $10^{-5}\ \text{to}\ 0.1$ | $0.001$ |
| **Lumped Series Branch (Substation Feeder)** | `main_model/Three-Phase Series RLC Branch` (SID=2) | `Capacitance` | Farads (F) | $10^{-9}\ \text{to}\ 10^{-3}$ | $10^{-6}$ |
| **Distributed Transmission Feeder** | `main_model/Three-Phase PI Section Line` (SID=4) | `Length` | km | $1.0\ \text{to}\ 500.0$ | $100.0$ |
| Distributed Resistance ($r_1, r_0$) | `main_model/Three-Phase PI Section Line` (SID=4) | `Resistances` | $\Omega / \text{km}$ | Per-unit-length | `[0.01273 0.3864]` |
| Distributed Inductance ($l_1, l_0$) | `main_model/Three-Phase PI Section Line` (SID=4) | `Inductances` | $\text{H} / \text{km}$ | Per-unit-length | `[0.9337e-3 4.1264e-3]` |
| Distributed Capacitance ($c_1, c_0$) | `main_model/Three-Phase PI Section Line` (SID=4) | `Capacitances` | $\text{F} / \text{km}$ | Per-unit-length | `[12.74e-9 7.751e-9]` |

---

### E. Three-Phase Fault Block Controls (All 12 Scenarios)

Block Path: `main_model/Three-Phase Fault` (SID=6)

| Scenario Code | Full Scenario Description | FaultA | FaultB | FaultC | GroundFault | Physical Consequence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NORMAL** | Healthy Transmission Line | `off` | `off` | `off` | `off` | Normal balanced 3-phase flow. Trip remains 0. |
| **AG** | Single Line-to-Ground (Phase A) | `on` | `off` | `off` | `on` | Phase A voltage collapse, zero-sequence current surge, breaker trips. |
| **BG** | Single Line-to-Ground (Phase B) | `off` | `on` | `off` | `on` | Phase B voltage collapse, zero-sequence current surge, breaker trips. |
| **CG** | Single Line-to-Ground (Phase C) | `off` | `off` | `on` | `on` | Phase C voltage collapse, zero-sequence current surge, breaker trips. |
| **AB** | Line-to-Line (Phases A & B) | `on` | `on` | `off` | `off` | Severe current surge in A and B in 180° opposition; no ground current. |
| **BC** | Line-to-Line (Phases B & C) | `off` | `on` | `on` | `off` | Severe current surge in B and C in 180° opposition; no ground current. |
| **CA** | Line-to-Line (Phases C & A) | `on` | `off` | `on` | `off` | Severe current surge in C and A in 180° opposition; no ground current. |
| **ABG** | Double Line-to-Ground (Phases A, B) | `on` | `on` | `off` | `on` | Combined phase and ground surge; breaker trips. |
| **BCG** | Double Line-to-Ground (Phases B, C) | `on` | `on` | `off` | `on` | Combined phase and ground surge; breaker trips. |
| **CAG** | Double Line-to-Ground (Phases C, A) | `on` | `off` | `on` | `on` | Combined phase and ground surge; breaker trips. |
| **ABC** | Symmetrical Three-Phase | `on` | `on` | `on` | `off` | Complete positive-sequence voltage collapse; maximum symmetrical surge. |
| **ABCG** | Three-Phase-to-Ground | `on` | `on` | `on` | `on` | Maximum short-circuit fault severity with earth return path. |

#### Timing & Impedance Parameters
- `FaultResistance` ($R_f$): $0.0001\ \text{to}\ 100.0\ \Omega$ (default: $0.001\ \Omega$).
- `GroundResistance` ($R_g$): $0.0001\ \text{to}\ 100.0\ \Omega$ (default: $0.01\ \Omega$).
- `TransitionTimes`: `[fault_start_time fault_stop_time]` (default: `[0.2 0.4]`). Inception time is restricted to $\ge 0.15\ \text{s}$ to safeguard against startup dynamic interference.

---

## 3. Parameter Safety, Clean Restoration & Workspace Hygiene

To prevent test cross-contamination or unintended persistence of altered parameters:
1. `_restore_defaults_sync(eng)` executes automatically in a `finally` block after every simulation run.
2. The base MATLAB workspace is purged using `clear ScopeData simOut scopeObj;` before and after each run.
3. Every altered parameter is read back using `eng.get_param(...)` immediately after setting and returned in the HTTP response under `readback_parameters`.
