"""
NIRDHVANI: Tactical AI/ML Adaptive Noise Cancellation Comms
Noise-Isolated Impulse-Resilient Real-Time Decoupled Hardware Voice Adaptive Network Isolator
"Decoupled Throat-Acoustic Adaptive Noise Cancellation for Extreme Battlefield Environments"

End-to-End Simulation & Verification Suite
Simulates 120-140 dB SPL Tank Cockpit Noise, Throat Contact Sensor, NLMS ANC, Blast Limiting,
and Real-World Hardware Non-Linear ADC / 8-bit DAC Quantization Effects.
"""

import os
import sys
import numpy as np
import scipy.signal as signal
from scipy.io import wavfile
import matplotlib.pyplot as plt

# Ensure local module import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dsp_core import NLMSFilter, AcousticImpulseLimiter, calculate_erle, calculate_snr


def model_hardware_adc_nonlinearity(audio_norm: np.ndarray, bits: int = 12, dnl_lsb: float = 1.8) -> np.ndarray:
    """
    Models real-world ESP32 SAR ADC non-linearities:
    - Finite quantization bit depth (12-bit)
    - Differential Non-Linearity (DNL) error distribution
    - Sub-100mV lower dead zone and saturation compression
    """
    q_levels = 2 ** bits
    scaled = (audio_norm + 1.0) * 0.5 * (q_levels - 1)
    
    # Add random DNL step distortion
    dnl_error = np.random.normal(0, dnl_lsb, size=scaled.shape)
    distorted = scaled + dnl_error
    
    # Non-linear S-curve compression near rails (ESP32 ADC behavior)
    norm_mid = (distorted - (q_levels / 2)) / (q_levels / 2)
    s_curved = np.tanh(norm_mid * 1.05)
    
    # Quantize
    quantized = np.round((s_curved + 1.0) * 0.5 * (q_levels - 1))
    quantized = np.clip(quantized, 0, q_levels - 1)
    
    # Reconvert to normalized [-1.0, +1.0]
    out_norm = (quantized / (q_levels - 1)) * 2.0 - 1.0
    return out_norm


def model_hardware_dac_quantization(audio_norm: np.ndarray, bits: int = 8) -> np.ndarray:
    """Models 8-bit DAC output quantization and reconstruction."""
    q_levels = 2 ** bits
    scaled = (audio_norm + 1.0) * 0.5 * (q_levels - 1)
    quantized = np.round(np.clip(scaled, 0, q_levels - 1))
    out_norm = (quantized / (q_levels - 1)) * 2.0 - 1.0
    return out_norm


def generate_synthetic_throat_speech(fs: int, duration_sec: float) -> np.ndarray:
    """
    Generate synthetic throat-conducted speech.
    Throat microphone captures vocal cord fundamental (120-160 Hz) and formants,
    with tissue-filtered high frequencies (cutoff ~ 2.5 kHz).
    """
    t = np.linspace(0, duration_sec, int(fs * duration_sec), endpoint=False)
    
    # Syllabic envelope modulation (speaking bursts)
    speech_envelope = np.zeros_like(t)
    burst_windows = [(0.5, 1.8), (2.3, 3.5), (4.0, 5.2)]
    for start, end in burst_windows:
        mask = (t >= start) & (t <= end)
        t_win = t[mask] - start
        win_len = end - start
        speech_envelope[mask] = 0.5 * (1.0 - np.cos(2 * np.pi * t_win / win_len))

    # Vocal fundamental frequency + harmonics (vowel-like /a/, /o/)
    f0 = 135.0  # Fundamental frequency (Hz)
    raw_vocal = (
        0.60 * np.sin(2 * np.pi * f0 * t) +
        0.45 * np.sin(2 * np.pi * 2 * f0 * t + 0.3) +
        0.30 * np.sin(2 * np.pi * 3 * f0 * t + 0.8) +
        0.20 * np.sin(2 * np.pi * 4 * f0 * t + 1.2) +
        0.15 * np.sin(2 * np.pi * 5 * f0 * t + 0.5)
    )

    # Formant filter (vocal tract resonance at ~800 Hz and 1800 Hz)
    sos_formant = signal.butter(4, [600 / (fs / 2), 2200 / (fs / 2)], btype='bandpass', output='sos')
    formant_voice = signal.sosfilt(sos_formant, raw_vocal)

    # Low-pass filter for throat tissue acoustic attenuation (<2.2 kHz)
    sos_tissue = signal.butter(4, 2000 / (fs / 2), btype='lowpass', output='sos')
    throat_speech = signal.sosfilt(sos_tissue, formant_voice)

    # Apply envelope and normalize
    throat_speech = throat_speech * speech_envelope
    max_val = np.max(np.abs(throat_speech))
    if max_val > 0:
        throat_speech = 0.5 * throat_speech / max_val

    return throat_speech


def generate_tank_cockpit_noise(fs: int, duration_sec: float) -> np.ndarray:
    """
    Simulates extreme 120-140 dB SPL main battle tank diesel engine,
    caterpillar track vibration, and cabin acoustic cavity resonances.
    """
    t = np.linspace(0, duration_sec, int(fs * duration_sec), endpoint=False)
    n_samples = len(t)

    # 1. Engine cylinder firing harmonics (Diesel RPM ~ 2200 => ~36.6 Hz fundamental)
    f_engine = 36.6
    engine_rumble = (
        0.8 * np.sin(2 * np.pi * f_engine * t) +
        0.7 * np.sin(2 * np.pi * 2 * f_engine * t + 0.4) +
        0.6 * np.sin(2 * np.pi * 3 * f_engine * t + 0.9) +
        0.5 * np.sin(2 * np.pi * 4 * f_engine * t + 1.5) +
        0.4 * np.sin(2 * np.pi * 6 * f_engine * t + 2.1) +
        0.3 * np.sin(2 * np.pi * 8 * f_engine * t + 0.7)
    )

    # 2. Track clatter and broadband cabin acoustics (colored noise)
    white = np.random.normal(0, 1, n_samples)
    sos_cabin = signal.butter(3, [80 / (fs / 2), 1200 / (fs / 2)], btype='bandpass', output='sos')
    cabin_noise = signal.sosfilt(sos_cabin, white)

    # Combined ambient noise field (high power)
    total_noise = engine_rumble + 1.2 * cabin_noise
    total_noise = total_noise / np.max(np.abs(total_noise))
    return total_noise


def inject_artillery_blast_impulses(
    ambient_noise: np.ndarray,
    fs: int,
    impulse_times: list
) -> np.ndarray:
    """
    Injects high-SPL acoustic shockwaves (artillery blast / 12.7mm machinegun).
    Sharp rise-time (~1ms) followed by exponential Friedlander decay.
    """
    noise_with_blast = np.copy(ambient_noise)
    blast_len = int(0.08 * fs)  # 80 ms blast duration
    t_blast = np.linspace(0, 0.08, blast_len, endpoint=False)
    
    # Friedlander waveform: P(t) = P0 * (1 - t/t_pos) * exp(-alpha * t/t_pos)
    friedlander = (1.0 - t_blast / 0.03) * np.exp(-3.5 * t_blast / 0.03)
    friedlander = 3.5 * friedlander  # High peak blast shock

    for t_sec in impulse_times:
        idx = int(t_sec * fs)
        if idx + blast_len < len(noise_with_blast):
            noise_with_blast[idx:idx + blast_len] += friedlander

    return noise_with_blast


def run_simulation():
    """Run full NIRDHVANI verification pipeline."""
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)

    fs = 16000  # 16 kHz tactical sampling rate
    duration = 6.0  # 6 seconds

    print("================================================================")
    print("  NIRDHVANI: Tactical Acoustic DSP Simulation & Benchmark Suite ")
    print("  [Simulated 120-140 dB SPL Tank Cockpit + Hardware ADC Modeling]")
    print("================================================================")
    print(f"Sampling Frequency : {fs} Hz")
    print(f"Duration           : {duration} s ({int(fs * duration)} samples)")

    # 1. Generate clean throat speech
    clean_speech = generate_synthetic_throat_speech(fs, duration)

    # 2. Generate ambient noise field (Reference mic: MAX4466)
    ambient_noise_ref = generate_tank_cockpit_noise(fs, duration)
    # Inject blast spikes at t = 2.0s (artillery) and t = 4.5s (gunshot)
    ambient_noise_ref = inject_artillery_blast_impulses(ambient_noise_ref, fs, [2.0, 4.5])

    # 3. Model acoustic leakage path H(z) from ambient cockpit into throat neckband
    acoustic_path = np.array([0.05, 0.12, -0.25, 0.35, 0.18, -0.09, 0.04, -0.02, 0.01])
    leaked_noise_into_piezo = signal.lfilter(acoustic_path, [1.0], ambient_noise_ref)

    # 4. Composite throat sensor signal d(n) = speech + leaked chassis noise
    d_throat_raw = clean_speech + leaked_noise_into_piezo
    x_ambient_raw = ambient_noise_ref

    # 5. Apply Hardware ADC Non-Linearity & Quantization Modeling (12-bit SAR ADC with DNL)
    d_throat_adc = model_hardware_adc_nonlinearity(d_throat_raw, bits=12, dnl_lsb=1.8)
    x_ambient_adc = model_hardware_adc_nonlinearity(x_ambient_raw, bits=12, dnl_lsb=1.8)

    # 6. Initialize Adaptive NLMS Filter & Limiter
    num_taps = 64
    mu = 0.30
    epsilon = 1e-4
    nlms_ideal = NLMSFilter(num_taps=num_taps, mu=mu, epsilon=epsilon, leakage=1e-5)
    nlms_hw = NLMSFilter(num_taps=num_taps, mu=mu, epsilon=epsilon, leakage=1e-5)
    limiter = AcousticImpulseLimiter(threshold=0.75, soft_knee=True)

    # Process Ideal Floating Point Path
    e_nlms_ideal, _, _ = nlms_ideal.filter_stream(d_throat_raw, x_ambient_raw)
    e_ideal_final = limiter.process_stream(e_nlms_ideal)

    # Process Real-World Hardware Path (ADC Non-Linearity + 8-bit DAC Quantization)
    e_nlms_hw, _, weight_norms = nlms_hw.filter_stream(d_throat_adc, x_ambient_adc)
    e_hw_limited = limiter.process_stream(e_nlms_hw)
    e_hw_final = model_hardware_dac_quantization(e_hw_limited, bits=8)

    # 7. Metrics & Analysis
    erle_ideal = calculate_erle(d_throat_raw[0:int(0.5 * fs)], e_ideal_final[0:int(0.5 * fs)])
    erle_hw = calculate_erle(d_throat_adc[0:int(0.5 * fs)], e_hw_final[0:int(0.5 * fs)])
    
    snr_in_raw = calculate_snr(clean_speech, d_throat_raw)
    snr_out_ideal = calculate_snr(clean_speech, e_ideal_final)
    snr_out_hw = calculate_snr(clean_speech, e_hw_final)

    print("\n---------------- Performance Summary ----------------")
    print(f"Raw Throat Input SNR               : {snr_in_raw:.2f} dB")
    print(f"Ideal Simulation Output SNR        : {snr_out_ideal:.2f} dB (Gain: +{snr_out_ideal - snr_in_raw:.2f} dB)")
    print(f"Ideal Simulation ERLE (Noise Red.) : {erle_ideal:.2f} dB")
    print(f"Hardware-Modeled Output SNR (8-bit): {snr_out_hw:.2f} dB (Gain: +{snr_out_hw - snr_in_raw:.2f} dB)")
    print(f"Hardware-Modeled ERLE (12b ADC/8b) : {erle_hw:.2f} dB")
    print("-----------------------------------------------------")
    print("NOTE: Figures are simulation benchmarks (with hardware non-linearity modeling).")
    print("      Physical chamber validation on hardware prototype currently in progress.")

    # 8. Save Audio Files
    def save_wav(filename, data):
        scaled = np.int16(np.clip(data, -1.0, 1.0) * 32767)
        filepath = os.path.join(output_dir, filename)
        wavfile.write(filepath, fs, scaled)
        return filepath

    f_clean = save_wav("1_clean_throat_speech.wav", clean_speech)
    f_ambient = save_wav("2_ambient_cockpit_noise.wav", x_ambient_raw)
    f_raw = save_wav("3_raw_throat_mixed_input.wav", d_throat_raw)
    f_filtered = save_wav("4_processed_anc_output.wav", e_hw_final)

    print(f"\n[Audio Files Saved]")
    print(f"  - Clean Speech : {f_clean}")
    print(f"  - Ambient Noise: {f_ambient}")
    print(f"  - Raw Input    : {f_raw}")
    print(f"  - Processed Out: {f_filtered}")

    # 9. Plot Results & Spectrograms
    time_axis = np.linspace(0, duration, len(clean_speech))
    plt.figure(figsize=(14, 10))

    # Waveform comparisons
    plt.subplot(4, 1, 1)
    plt.plot(time_axis, d_throat_raw, color='orange', alpha=0.8, label='Raw Throat Sensor d(n) [Speech + Leaked 120dB Noise]')
    plt.plot(time_axis, clean_speech, color='blue', alpha=0.5, label='Clean Vocal Cord Reference')
    plt.title("NIRDHVANI Signal Processing Pipeline [Simulation Benchmark]", fontsize=13, fontweight='bold')
    plt.ylabel("Amplitude")
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)

    plt.subplot(4, 1, 2)
    plt.plot(time_axis, x_ambient_raw, color='red', alpha=0.7, label='Ambient Reference Mic x(n) [Tank Engine + Blast Spikes]')
    plt.ylabel("Amplitude")
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)

    plt.subplot(4, 1, 3)
    plt.plot(time_axis, e_hw_final, color='green', label=f'Processed Audio e(n) [NLMS + Limiter + HW Quantization] (ERLE: {erle_hw:.1f} dB)')
    plt.ylabel("Amplitude")
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)

    plt.subplot(4, 1, 4)
    plt.plot(time_axis, weight_norms, color='purple', label='NLMS Filter Weight Vector Norm ||w(n)|| (Convergence Trajectory)')
    plt.xlabel("Time (seconds)")
    plt.ylabel("Weight Norm")
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plot_path = os.path.join(output_dir, "tacanc_waveform_analysis.png")
    plt.savefig(plot_path, dpi=200)
    plt.close()
    print(f"\n[Analysis Plot Saved] -> {plot_path}")

    # Save benchmark report summary
    report_path = os.path.join(output_dir, "benchmark_report.txt")
    with open(report_path, "w") as rf:
        rf.write("NIRDHVANI Tactical ANC Comms Benchmark Report\n")
        rf.write("==============================================\n")
        rf.write(f"Sampling Rate: {fs} Hz\n")
        rf.write(f"NLMS Taps: {num_taps}\n")
        rf.write(f"Learning Rate (mu): {mu}\n")
        rf.write(f"Regularizer (epsilon): {epsilon}\n")
        rf.write(f"Raw Input SNR: {snr_in_raw:.2f} dB\n")
        rf.write(f"Ideal Simulation Output SNR: {snr_out_ideal:.2f} dB\n")
        rf.write(f"Ideal Simulation ERLE: {erle_ideal:.2f} dB\n")
        rf.write(f"Hardware-Modeled Output SNR: {snr_out_hw:.2f} dB\n")
        rf.write(f"Hardware-Modeled ERLE: {erle_hw:.2f} dB\n")
        rf.write("\nStatus: Simulation benchmark verified with non-linear ADC modeling.\n")
        rf.write("Physical hardware acoustic chamber testing in progress.\n")
    print(f"[Benchmark Report Saved] -> {report_path}")


if __name__ == "__main__":
    run_simulation()
