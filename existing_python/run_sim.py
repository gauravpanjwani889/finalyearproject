import matlab.engine
import matplotlib.pyplot as plt
import numpy as np

# 1. Start MATLAB Engine
print("Starting MATLAB Engine...")
eng = matlab.engine.start_matlab()

model_name = "main_model"
print(f"Loading {model_name}.slx...")
eng.load_system(model_name)

# 2. Run simulation and capture output structure in MATLAB workspace
print("Running simulation...")
eng.eval(f"simOut = sim('{model_name}');", nargout=0)

# 3. Extract time and signal data from To Workspace structure
print("Extracting signals...")
eng.eval("scopeObj = simOut.get('ScopeData');", nargout=0)

time = np.array(eng.eval("scopeObj.time")).flatten()
data = np.array(eng.eval("scopeObj.signals.values"))

# Handle array orientation (ensure rows match time steps)
if data.ndim == 2 and data.shape[0] != len(time):
    data = data.T

# 4. Create Publication-Quality 5-Panel Waveform Plot
fig, axs = plt.subplots(5, 1, figsize=(11, 10), sharex=True)

# Plot 1: Vabc with Phase Legends
axs[0].plot(time, data[:, 0], label="Phase A", linewidth=1.2)
axs[0].plot(time, data[:, 1], label="Phase B", linewidth=1.2)
axs[0].plot(time, data[:, 2], label="Phase C", linewidth=1.2)
axs[0].set_ylabel("Vabc (V)", fontweight="bold")
axs[0].legend(loc="upper right", fontsize=8, framealpha=0.9)
axs[0].grid(True, linestyle="--", alpha=0.6)

# Plot 2: Iabc with Phase Legends
axs[1].plot(time, data[:, 3], label="Phase A", linewidth=1.2)
axs[1].plot(time, data[:, 4], label="Phase B", linewidth=1.2)
axs[1].plot(time, data[:, 5], label="Phase C", linewidth=1.2)
axs[1].set_ylabel("Iabc (A)", fontweight="bold")
axs[1].legend(loc="upper right", fontsize=8, framealpha=0.9)
axs[1].grid(True, linestyle="--", alpha=0.6)

# Plot 3: Digital Trip Logic Output
axs[2].plot(time, data[:, 6], color="crimson", linewidth=1.8, label="Trip Signal")
axs[2].set_ylabel("Trip Status", fontweight="bold")
axs[2].set_ylim(-0.2, 1.2)
axs[2].set_yticks([0, 1])
axs[2].set_yticklabels(["0 (Trip/Open)", "1 (Closed)"])
axs[2].grid(True, linestyle="--", alpha=0.6)

# Plot 4: Voltage Magnitude (Vmag)
axs[3].plot(time, data[:, 7], color="darkmagenta", linewidth=1.5)
axs[3].set_ylabel("Vmag (V)", fontweight="bold")
axs[3].grid(True, linestyle="--", alpha=0.6)

# Plot 5: Current Magnitude (Imag)
axs[4].plot(time, data[:, 8], color="darkorange", linewidth=1.5)
axs[4].set_ylabel("Imag (A)", fontweight="bold")
axs[4].set_xlabel("Time (s)", fontweight="bold")
axs[4].grid(True, linestyle="--", alpha=0.6)

# Highlight Fault Clearance / Isolation Period Across All Subplots (0.2s - 0.6s)
for ax in axs:
    ax.axvspan(0.2, 0.6, color="red", alpha=0.08)

# Title & Formatting
plt.suptitle("FYP Transmission Line Protection & Isolation Analysis", fontsize=14, fontweight="bold")
plt.tight_layout()

# Save High-Resolution Image directly for LaTeX/Word report
plt.savefig("simulation_results.png", dpi=300)
print("Plot saved as 'simulation_results.png' in project folder.")

# Display Figure
plt.show()

# 5. Quit MATLAB Session safely
eng.quit()