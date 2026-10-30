import streamlit as st
import matlab.engine
import numpy as np
import matplotlib.pyplot as plt

# Page Configuration
st.set_page_config(
    page_title="Smart Grid Protection & Alarm System", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

st.title("⚡ Smart Grid Protection, Parameter Analyzer & Fault Alarm")
st.write("Dynamically modify physical grid parameters, observe live Simulink solver responses, and trigger real-time fault alarms.")

# ---------------------------------------------------------
# MATLAB Engine Persistent Cache
# ---------------------------------------------------------
@st.cache_resource
def get_matlab_engine():
    print("Starting MATLAB Engine Session...")
    eng = matlab.engine.start_matlab()
    return eng

eng = get_matlab_engine()
model_name = "main_model"

if "model_loaded" not in st.session_state:
    eng.load_system(model_name, nargout=0)
    st.session_state["model_loaded"] = True

# ---------------------------------------------------------
# Sidebar Controls
# ---------------------------------------------------------
st.sidebar.header("1. Voltage & Power Factor")
v_primary = st.sidebar.number_input("Primary Voltage (V)", min_value=1000.0, max_value=132000.0, value=11000.0, step=1000.0)
v_secondary = st.sidebar.number_input("Secondary Voltage (V)", min_value=100.0, max_value=11000.0, value=415.0, step=50.0)
power_factor = st.sidebar.slider("Target Power Factor (cos φ)", min_value=0.50, max_value=1.00, value=0.85, step=0.01)

st.sidebar.header("2. Transmission Line (R, L, C)")
res_val = st.sidebar.number_input("Line Resistance R (Ohms)", min_value=0.01, max_value=100.0, value=1.0, step=0.1)
ind_val = st.sidebar.number_input("Line Inductance L (mH)", min_value=0.1, max_value=1000.0, value=10.0, step=1.0)
cap_val = st.sidebar.number_input("Line Capacitance C (uF)", min_value=0.01, max_value=100.0, value=1.0, step=0.1)

st.sidebar.header("3. Fault Condition")
fault_type = st.sidebar.selectbox("Fault Type", options=["Single Line-to-Ground (AG)", "Line-to-Line (AB)", "Three-Phase Fault (ABC)"])
fault_resistance = st.sidebar.slider("Fault Resistance Rf (Ohms)", min_value=0.001, max_value=50.0, value=5.0, step=0.5)

run_button = st.sidebar.button("Run Fast Simulation & Analyze", type="primary")

# ---------------------------------------------------------
# Simulation & Analysis Pipeline
# ---------------------------------------------------------
if run_button:
    with st.spinner("Updating Simulink block parameters & running model..."):
        # 1. Update Source Voltage (Phase Peak = Vrms * sqrt(2) / sqrt(3))
        v_peak_phase = (v_primary * np.sqrt(2)) / np.sqrt(3)
        
        try:
            eng.set_param(f"{model_name}/Three-Phase Programmable Voltage Source", "PositiveSequence", f"[{v_peak_phase} 0 50]", nargout=0)
        except:
            try:
                eng.set_param(f"{model_name}/Three-Phase Programmable Voltage Source", "Amplitude", str(v_peak_phase), nargout=0)
            except Exception as e:
                print(f"Voltage parameter update notice: {e}")

        # 2. Update Line RLC Parameters
        eng.set_param(f"{model_name}/Three-Phase Series RLC Branch", "Resistance", str(res_val), nargout=0)
        eng.set_param(f"{model_name}/Three-Phase Series RLC Branch", "Inductance", str(ind_val * 1e-3), nargout=0)
        eng.set_param(f"{model_name}/Three-Phase Series RLC Branch", "Capacitance", str(cap_val * 1e-6), nargout=0)

        # 3. Update Fault Resistance
        eng.set_param(f"{model_name}/Three-Phase Fault", "FaultResistance", str(fault_resistance), nargout=0)

        # 4. Execute Simulation
        eng.eval(f"simOut = sim('{model_name}');", nargout=0)
        eng.eval("scopeObj = simOut.get('ScopeData');", nargout=0)

        # 5. Extract Data Arrays
        time = np.array(eng.eval("scopeObj.time")).flatten()
        data = np.array(eng.eval("scopeObj.signals.values"))
        if data.ndim == 2 and data.shape[0] != len(time):
            data = data.T

    st.success("Simulation Complete!")

    # Dynamic Power System Calculations
    peak_current = np.max(data[:, 8])
    min_voltage = np.min(data[:, 7])
    
    apparent_power_kva = (np.sqrt(3) * v_primary * peak_current) / 1000.0
    real_power_kw = apparent_power_kva * power_factor
    reactive_power_kvar = apparent_power_kva * np.sin(np.arccos(power_factor))

    # Evaluate Fault Breaker State & Trigger Web Audio Alarm
    trip_signal = data[:, 6]
    is_faulted = np.any(trip_signal < 0.5)

    if is_faulted:
        st.error("🚨 FAULT DETECTED! BREAKER TRIPPED - ALARM ACTIVE")
        alarm_js = """
            <script>
                var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                var osc = audioCtx.createOscillator();
                var gain = audioCtx.createGain();
                
                osc.type = 'sawtooth';
                osc.frequency.setValueAtTime(1000, audioCtx.currentTime); // 1000Hz Buzzer Tone
                
                gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
                
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                
                osc.start();
                setTimeout(function() { osc.stop(); }, 3000); // Plays tone for 3 seconds
            </script>
        """
        st.components.v1.html(alarm_js, height=0)

    # Protection & Mitigation Strategy Logic
    if "Three-Phase" in fault_type or peak_current > 10000:
        severity = "CRITICAL (Symmetrical Fault)"
        solutions = [
            "**Zone 1 Distance Relay:** High-speed trip activated within 15 ms; inhibit auto-reclose.",
            "**Reactive Power Support:** Inject STATCOM / FACTS compensation to avoid grid voltage collapse.",
            f"**Capacitive Surge Check:** Verify surge arresters against peak current $I = {peak_current:.1f}\\text{{ A}}$ with $C = {cap_val}\\ \\mu\\text{{F}}$."
        ]
    elif "Line-to-Line" in fault_type or peak_current > 5000:
        severity = "HIGH (Asymmetrical Fault)"
        solutions = [
            "**Zone 2 Delayed Trip:** Coordinate clearance time (~300 ms) with downstream backup fuses.",
            "**Negative-Sequence Current Filtering:** Engage ANSI 46 element to protect generator rotors.",
            f"**Inductive Reactance Tuning:** Line inductance $L = {ind_val}\\text{{ mH}}$ configured to suppress current magnitude."
        ]
    else:
        severity = "MODERATE (Ground Fault)"
        solutions = [
            "**Single-Pole Auto-Reclosure:** Initiate 1-phase auto-reclose attempt after 500 ms de-energization.",
            "**Neutral Grounding Adjustment:** Tune Peterson Coil / Grounding Reactor to restrict ground current below 10 A.",
            f"**Arc Resistance Compensation:** Distance element calibrated for $R_f = {fault_resistance}\\ \\Omega$."
        ]

    # Metrics Layout
    st.markdown("---")
    st.subheader("📊 Dynamic Power System Metrics")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Grid Step Down", f"{v_primary/1000:.1f} kV → {v_secondary:.0f} V")
    m2.metric("Power Factor", f"{power_factor:.2f}")
    m3.metric("Peak Current ($I_{mag}$)", f"{peak_current:.2f} A")
    m4.metric("Real Power (P)", f"{real_power_kw:.1f} kW")
    m5.metric("Reactive Power (Q)", f"{reactive_power_kvar:.1f} kVAR")

    # Protection Solutions Layout
    st.markdown("---")
    st.subheader("🛡️ AI Protection & Mitigation Solutions")
    st.info(f"**Severity Level:** {severity} | **Fault Type:** {fault_type}")
    for sol in solutions:
        st.markdown(f"* {sol}")

    # Waveform Dashboard
    st.markdown("---")
    st.subheader("📈 Live Waveform Diagnostics")
    fig, axs = plt.subplots(3, 1, figsize=(10, 6), sharex=True)

    axs[0].plot(time, data[:, 0:3])
    axs[0].set_ylabel("Voltage (V)", fontweight="bold")
    axs[0].grid(True, linestyle="--", alpha=0.6)

    axs[1].plot(time, data[:, 3:6])
    axs[1].set_ylabel("Current (A)", fontweight="bold")
    axs[1].grid(True, linestyle="--", alpha=0.6)

    axs[2].plot(time, data[:, 6], color="red", linewidth=1.5)
    axs[2].set_ylabel("Breaker Logic", fontweight="bold")
    axs[2].set_xlabel("Time (s)", fontweight="bold")
    axs[2].grid(True, linestyle="--", alpha=0.6)

    for ax in axs:
        ax.axvspan(0.2, 0.6, color="red", alpha=0.08)

    plt.tight_layout()
    st.pyplot(fig)