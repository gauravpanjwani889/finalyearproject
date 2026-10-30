"""
Deep Analysis of Voltage Waveform Distortion:
1. Analyzes raw 20,005-point voltage data from Simulink solver (scratch/raw_normal_v7.mat)
2. Performs FFT spectrum analysis to identify switching harmonics (2 kHz PWM carrier)
3. Evaluates the startup transient window (0.0 to 0.15s) vs steady state (0.15 to 1.0s)
4. Tests and compares Min-Max decimation vs Peak-Preserving decimation
5. Generates high-resolution comparative diagnostic plots saved to scratch/voltage_distortion_analysis.png
"""

import sys
from pathlib import Path
import numpy as np
import scipy.io
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.analytics import decimate_waveforms, compute_true_powers

def analyze():
    mat_path = PROJECT_ROOT / "scratch" / "raw_normal_v7.mat"
    if not mat_path.exists():
        print(f"Error: {mat_path} not found.")
        return

    data = scipy.io.loadmat(str(mat_path))
    t = data['t'].flatten()
    sig = data['sig']
    if sig.shape[0] != len(t):
        sig = sig.T

    va = sig[:, 0]
    vb = sig[:, 1]
    vc = sig[:, 2]
    ia = sig[:, 3]
    ib = sig[:, 4]
    ic = sig[:, 5]
    trip = sig[:, 6]
    vmag = sig[:, 7]
    imag = sig[:, 8]

    fs = 1.0 / (t[1] - t[0])
    print(f"Sampling Frequency Fs: {fs:.1f} Hz (Ts = {(t[1]-t[0])*1e6:.1f} us), Total Points: {len(t)}")

    # 1. Startup Transient vs Steady-State
    mask_startup = (t <= 0.15)
    mask_steady = (t >= 0.20) & (t <= 0.90)

    print("\n--- 1. TEMPORAL AMPLITUDE COMPARISON ---")
    print(f"Startup (0.0s - 0.15s):")
    print(f"  Va Peak: {np.max(np.abs(va[mask_startup])):.2f} V, RMS: {np.sqrt(np.mean(va[mask_startup]**2)):.2f} V")
    print(f"Steady-State (0.20s - 0.90s):")
    print(f"  Va Peak: {np.max(np.abs(va[mask_steady])):.2f} V, RMS: {np.sqrt(np.mean(va[mask_steady]**2)):.2f} V")

    # 2. FFT Spectral Analysis over Steady-State
    va_steady = va[mask_steady]
    t_steady = t[mask_steady]
    n_fft = len(va_steady)
    fft_vals = np.fft.rfft(va_steady)
    fft_freqs = np.fft.rfftfreq(n_fft, d=1.0/fs)
    fft_mag = (2.0 / n_fft) * np.abs(fft_vals)

    # Top harmonic peaks
    top_indices = np.argsort(fft_mag)[::-1][:15]
    print("\n--- 2. SPECTRAL HARMONIC PEAKS (Steady-State) ---")
    print("Rank | Frequency (Hz) | Amplitude (V) | Harmonic Description")
    print("-" * 65)
    for rank, idx in enumerate(top_indices):
        freq = fft_freqs[idx]
        mag = fft_mag[idx]
        desc = ""
        if abs(freq - 50.0) < 5.0:
            desc = "Fundamental (50 Hz Grid Frequency)"
        elif abs(freq - 2000.0) < 60.0:
            desc = "VSC PWM Carrier Sideband (2 kHz)"
        elif abs(freq - 4000.0) < 60.0:
            desc = "2nd PWM Sideband (4 kHz)"
        elif abs(freq - 6000.0) < 60.0:
            desc = "3rd PWM Sideband (6 kHz)"
        print(f"{rank+1:4d} | {freq:14.1f} | {mag:13.2f} | {desc}")

    idx_fund = np.argmin(np.abs(fft_freqs - 50.0))
    fund_amp = fft_mag[idx_fund]

    # 3. Decimation Comparison
    p_inst, q_inst = compute_true_powers(va, vb, vc, ia, ib, ic)
    dec_data = decimate_waveforms(t, sig, p_inst, q_inst, target_points=1000)
    t_dec = np.array(dec_data.time)
    va_dec = np.array(dec_data.va)

    # 4. Generate Diagnostic Plot
    plt.figure(figsize=(14, 10), facecolor='#0c1220')
    plt.rcParams['text.color'] = '#f1f5f9'
    plt.rcParams['axes.labelcolor'] = '#94a3b8'
    plt.rcParams['xtick.color'] = '#64748b'
    plt.rcParams['ytick.color'] = '#64748b'
    plt.rcParams['axes.edgecolor'] = '#213354'

    # Subplot 1: Full Waveform Comparison (Raw vs Decimated)
    ax1 = plt.subplot(3, 1, 1)
    ax1.set_facecolor('#070b12')
    ax1.plot(t, va, color='#06b6d4', alpha=0.5, linewidth=0.8, label='Raw Simulink Output (20,005 samples, Ts=50us)')
    ax1.plot(t_dec, va_dec, color='#f59e0b', linewidth=1.2, label='Min-Max Decimated (1,000 samples)')
    ax1.axvspan(0.0, 0.15, color='#ef4444', alpha=0.15, label='Generator Startup Blanking Window [0.0 - 0.15s]')
    ax1.set_title("Full Simulation Voltage Va(t) (Raw vs Decimated)", color='#ffffff', fontsize=11, fontweight='bold')
    ax1.set_ylabel("Voltage (V)")
    ax1.legend(loc='upper right', facecolor='#0f172a', edgecolor='#213354', fontsize=8)
    ax1.grid(True, color='#16233b', linestyle='--')

    # Subplot 2: Zoomed Waveform Comparison (Steady-State 2-Cycles)
    ax2 = plt.subplot(3, 2, 3)
    ax2.set_facecolor('#070b12')
    zoom_mask = (t >= 0.30) & (t <= 0.34)
    zoom_dec_mask = (t_dec >= 0.30) & (t_dec <= 0.34)
    ax2.plot(t[zoom_mask], va[zoom_mask], color='#06b6d4', linewidth=1.2, label='Raw 20 kHz Waveform')
    ax2.plot(t_dec[zoom_dec_mask], va_dec[zoom_dec_mask], 'o-', color='#f59e0b', markersize=3, linewidth=1.0, label='Decimated Points')
    ax2.set_title("Zoomed Steady-State (0.30s - 0.34s) Showing 2 kHz PWM Ripple", color='#ffffff', fontsize=10, fontweight='bold')
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Voltage (V)")
    ax2.legend(loc='upper right', facecolor='#0f172a', edgecolor='#213354', fontsize=7)
    ax2.grid(True, color='#16233b', linestyle='--')

    # Subplot 3: Zoomed Startup Window (0.0s - 0.15s)
    ax3 = plt.subplot(3, 2, 4)
    ax3.set_facecolor('#070b12')
    start_mask = (t >= 0.0) & (t <= 0.15)
    ax3.plot(t[start_mask], va[start_mask], color='#38bdf8', linewidth=0.8, label='Va Startup Transient')
    ax3.plot(t[start_mask], vmag[start_mask], color='#f43f5e', linewidth=1.5, label='Vmag (Phasor Sequence)')
    ax3.axhline(100.0, color='#ef4444', linestyle='--', label='Relay UV Threshold (100V)')
    ax3.set_title("Startup Region (0.0s - 0.15s): Generator Sync Transient", color='#ffffff', fontsize=10, fontweight='bold')
    ax3.set_xlabel("Time (s)")
    ax3.set_ylabel("Voltage (V)")
    ax3.legend(loc='upper right', facecolor='#0f172a', edgecolor='#213354', fontsize=7)
    ax3.grid(True, color='#16233b', linestyle='--')

    # Subplot 4: FFT Harmonic Spectrum
    ax4 = plt.subplot(3, 1, 3)
    ax4.set_facecolor('#070b12')
    freq_mask = (fft_freqs <= 8000)
    ax4.plot(fft_freqs[freq_mask], fft_mag[freq_mask], color='#a855f7', linewidth=1.0)
    ax4.annotate('50 Hz Fundamental', xy=(50, fund_amp), xytext=(200, fund_amp*0.8),
                 arrowprops=dict(facecolor='#00f0ff', shrink=0.05, width=1, headwidth=4),
                 color='#00f0ff', fontsize=8, fontweight='bold')
    ax4.annotate('2 kHz VSC PWM Carrier Sideband', xy=(1950, 152), xytext=(2200, 140),
                 arrowprops=dict(facecolor='#f59e0b', shrink=0.05, width=1, headwidth=4),
                 color='#f59e0b', fontsize=8, fontweight='bold')
    ax4.annotate('4 kHz 2nd PWM Carrier', xy=(3950, 104), xytext=(4200, 100),
                 arrowprops=dict(facecolor='#f43f5e', shrink=0.05, width=1, headwidth=4),
                 color='#f43f5e', fontsize=8, fontweight='bold')
    ax4.annotate('6 kHz 3rd PWM Carrier', xy=(5950, 105), xytext=(6200, 100),
                 arrowprops=dict(facecolor='#f43f5e', shrink=0.05, width=1, headwidth=4),
                 color='#f43f5e', fontsize=8, fontweight='bold')
    ax4.set_title("FFT Harmonic Spectrum of Va(t) (0 to 8 kHz)", color='#ffffff', fontsize=10, fontweight='bold')
    ax4.set_xlabel("Frequency (Hz)")
    ax4.set_ylabel("Harmonic Amplitude (V)")
    ax4.grid(True, color='#16233b', linestyle='--')

    plt.tight_layout()
    out_img = PROJECT_ROOT / "scratch" / "voltage_distortion_analysis.png"
    plt.savefig(out_img, dpi=180, facecolor='#0c1220')
    plt.close()
    print(f"\nSaved diagnostic plot to: {out_img}")

if __name__ == "__main__":
    analyze()
