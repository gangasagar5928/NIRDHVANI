"""
NIRDHVANI: Tactical AI/ML Adaptive Noise Cancellation Comms
Noise-Isolated Impulse-Resilient Real-Time Decoupled Hardware Voice Adaptive Network Isolator
"Decoupled Throat-Acoustic Adaptive Noise Cancellation for Extreme Battlefield Environments"

Full Multi-Segment Benchmark Suite:
1. Stationary Noise (120 dB Diesel Engine) -> ERLE, STOI, PESQ
2. Non-Stationary Noise (Caterpillar Track / Cabin Resonance) -> ERLE, STOI, PESQ
3. Impulsive Noise (140 dB Artillery / Firearm Shockwaves) -> Peak Clamping & Recovery
4. TinyML Neural Scene Classifier & Dynamic Step-Size Inference
5. Realistic Hardware SAR ADC DNL & 8-bit DAC Reconstruction Modeling
"""

import os
import sys
from typing import Tuple, Dict, List
import numpy as np
import scipy.signal as signal
from scipy.io import wavfile
import matplotlib.pyplot as plt

# Local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dsp_core import (
    NLMSFilter, AcousticImpulseLimiter,
    calculate_erle, calculate_snr, calculate_stoi_proxy, calculate_pesq_proxy,
    calculate_acoustic_coherence
)
from tinyml_model import TinyMLNoiseClassifierAndStepController


def model_hardware_adc_nonlinearity(audio_norm: np.ndarray, bits: int = 12, dnl_lsb: float = 1.8) -> np.ndarray:
    """Models real ESP32 12-bit SAR ADC DNL errors and rail compression."""
    q_levels = 2 ** bits
    scaled = (audio_norm + 1.0) * 0.5 * (q_levels - 1)
    dnl_error = np.random.normal(0, dnl_lsb, size=scaled.shape)
    distorted = scaled + dnl_error
    norm_mid = (distorted - (q_levels / 2)) / (q_levels / 2)
    s_curved = np.tanh(norm_mid * 1.05)
    quantized = np.round((s_curved + 1.0) * 0.5 * (q_levels - 1))
    quantized = np.clip(quantized, 0, q_levels - 1)
    out_norm = (quantized / (q_levels - 1)) * 2.0 - 1.0
    return out_norm


def model_hardware_dac_quantization(audio_norm: np.ndarray, bits: int = 8) -> np.ndarray:
    """Models ESP32 8-bit DAC quantization."""
    q_levels = 2 ** bits
    scaled = (audio_norm + 1.0) * 0.5 * (q_levels - 1)
    quantized = np.round(np.clip(scaled, 0, q_levels - 1))
    out_norm = (quantized / (q_levels - 1)) * 2.0 - 1.0
    return out_norm


def generate_synthetic_throat_speech(fs: int, duration_sec: float) -> np.ndarray:
    """Generate throat-conducted vocalization."""
    t = np.linspace(0, duration_sec, int(fs * duration_sec), endpoint=False)
    speech_envelope = np.zeros_like(t)
    burst_windows = [(0.5, 1.8), (2.3, 3.5), (4.0, 5.2)]
    for start, end in burst_windows:
        mask = (t >= start) & (t <= end)
        t_win = t[mask] - start
        win_len = end - start
        speech_envelope[mask] = 0.5 * (1.0 - np.cos(2 * np.pi * t_win / win_len))

    f0 = 135.0
    raw_vocal = (
        0.60 * np.sin(2 * np.pi * f0 * t) +
        0.45 * np.sin(2 * np.pi * 2 * f0 * t + 0.3) +
        0.30 * np.sin(2 * np.pi * 3 * f0 * t + 0.8) +
        0.20 * np.sin(2 * np.pi * 4 * f0 * t + 1.2) +
        0.15 * np.sin(2 * np.pi * 5 * f0 * t + 0.5)
    )

    sos_formant = signal.butter(4, [600 / (fs / 2), 2200 / (fs / 2)], btype='bandpass', output='sos')
    formant_voice = signal.sosfilt(sos_formant, raw_vocal)

    sos_tissue = signal.butter(4, 2000 / (fs / 2), btype='lowpass', output='sos')
    throat_speech = signal.sosfilt(sos_tissue, formant_voice)
    throat_speech = throat_speech * speech_envelope
    max_val = np.max(np.abs(throat_speech))
    if max_val > 0:
        throat_speech = 0.5 * throat_speech / max_val
    return throat_speech


def generate_segmented_noises(fs: int, duration_sec: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Generates isolated noise fields:
    1. Stationary Engine Drone
    2. Non-Stationary Track Rattle & Cabin Resonance
    3. Impulsive Blast Shocks
    4. Composite Combat Field
    """
    t = np.linspace(0, duration_sec, int(fs * duration_sec), endpoint=False)
    n_samples = len(t)

    # 1. Stationary Noise: Diesel Engine harmonics (RPM ~ 2200 => 36.6 Hz)
    f_eng = 36.6
    stat_noise = (
        0.8 * np.sin(2 * np.pi * f_eng * t) +
        0.7 * np.sin(2 * np.pi * 2 * f_eng * t + 0.4) +
        0.6 * np.sin(2 * np.pi * 3 * f_eng * t + 0.9) +
        0.5 * np.sin(2 * np.pi * 4 * f_eng * t + 1.5)
    )
    stat_noise = stat_noise / np.max(np.abs(stat_noise))

    # 2. Non-Stationary Noise: Caterpillar track squeal + FM chirp + cabin cavity
    track_mod = 1.0 + 0.5 * np.sin(2 * np.pi * 3.2 * t)
    white = np.random.normal(0, 1, n_samples)
    sos_track = signal.butter(3, [300 / (fs / 2), 2400 / (fs / 2)], btype='bandpass', output='sos')
    track_noise = signal.sosfilt(sos_track, white) * track_mod
    non_stat_noise = track_noise / np.max(np.abs(track_noise))

    # 3. Impulsive Blast Noise: Friedlander shockwaves
    impulse_noise = np.zeros(n_samples)
    blast_len = int(0.08 * fs)
    t_blast = np.linspace(0, 0.08, blast_len, endpoint=False)
    friedlander = 3.5 * (1.0 - t_blast / 0.03) * np.exp(-3.5 * t_blast / 0.03)
    
    for t_sec in [2.0, 4.5]:
        idx = int(t_sec * fs)
        if idx + blast_len < n_samples:
            impulse_noise[idx:idx + blast_len] += friedlander

    # 4. Composite
    composite_noise = 0.6 * stat_noise + 0.5 * non_stat_noise + impulse_noise
    composite_noise = composite_noise / np.max(np.abs(composite_noise) + 1e-6)

    return stat_noise, non_stat_noise, impulse_noise, composite_noise


def evaluate_segment(
    clean_speech: np.ndarray,
    noise: np.ndarray,
    acoustic_path: np.ndarray,
    fs: int,
    name: str,
    tinyml: TinyMLNoiseClassifierAndStepController
) -> Dict[str, float]:
    """Evaluate performance on a specific noise category."""
    leaked_noise = signal.lfilter(acoustic_path, [1.0], noise)
    d_raw = clean_speech + leaked_noise
    x_raw = noise

    # Apply hardware ADC modeling
    d_adc = model_hardware_adc_nonlinearity(d_raw)
    x_adc = model_hardware_adc_nonlinearity(x_raw)

    nlms = NLMSFilter(num_taps=64, mu=0.25, epsilon=1e-4, leakage=1e-5, enable_dtd=True)
    limiter = AcousticImpulseLimiter(threshold=0.75, soft_knee=True)

    # Process block by block with TinyML controller
    block_size = 64
    e_out = np.zeros_like(d_adc)
    prev_energy_x = 0.0
    inferred_classes = []

    for i in range(0, len(d_adc) - block_size, block_size):
        d_blk = d_adc[i:i + block_size]
        x_blk = x_adc[i:i + block_size]

        feat = tinyml.extract_features(d_blk, x_blk, prev_energy_x)
        prev_energy_x = float(np.mean(x_blk ** 2))
        res = tinyml.infer(feat)
        inferred_classes.append(res["noise_class"])

        nlms.mu = res["mu"]
        for k in range(block_size):
            e_s, _ = nlms.step(d_blk[k], x_blk[k])
            e_out[i + k] = limiter.process_sample(e_s)

    # Apply 8-bit DAC quantization
    e_final = model_hardware_dac_quantization(e_out)

    # Metrics Calculation:
    # 1. Noise reduction (ERLE) evaluated during speech-free noise lulls (t = 0.0 to 0.4s and t = 1.8 to 2.2s)
    mask_noise = ((np.linspace(0, 6.0, len(d_adc)) <= 0.4) | 
                  ((np.linspace(0, 6.0, len(d_adc)) >= 1.8) & (np.linspace(0, 6.0, len(d_adc)) <= 2.2)))
    
    if "Impulsive" in name:
        # For impulsive blast: measure peak shock suppression in blast window (t = 2.0 to 2.15s)
        mask_blast = (np.linspace(0, 6.0, len(d_adc)) >= 2.0) & (np.linspace(0, 6.0, len(d_adc)) <= 2.2)
        peak_in = np.max(np.abs(d_adc[mask_blast]))
        peak_out = np.max(np.abs(e_final[mask_blast]))
        erle = float(20.0 * np.log10((peak_in + 1e-6) / (peak_out + 1e-6)))
    else:
        erle = calculate_erle(d_adc[mask_noise], e_final[mask_noise])

    stoi_in = calculate_stoi_proxy(clean_speech, d_raw, fs)
    stoi_out = calculate_stoi_proxy(clean_speech, e_final, fs)
    pesq_in = calculate_pesq_proxy(clean_speech, d_raw, fs)
    pesq_out = calculate_pesq_proxy(clean_speech, e_final, fs)
    snr_in = calculate_snr(clean_speech, d_raw)
    snr_out = calculate_snr(clean_speech, e_final)

    return {
        "name": name,
        "erle_db": erle,
        "stoi_in": stoi_in,
        "stoi_out": stoi_out,
        "pesq_in": pesq_in,
        "pesq_out": pesq_out,
        "snr_in": snr_in,
        "snr_out": snr_out,
        "e_final": e_final,
        "d_raw": d_raw,
        "x_raw": x_raw,
        "inferred_classes": inferred_classes
    }


def run_full_simulation():
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)

    fs = 16000
    duration = 6.0

    print("==========================================================================")
    print("  NIRDHVANI: Tactical AI/ML Multi-Category Benchmark & Validation Suite   ")
    print("  [Stationary, Non-Stationary, Impulsive Noise & Intelligibility Metrics] ")
    print("==========================================================================")

    clean_speech = generate_synthetic_throat_speech(fs, duration)
    stat_n, nonstat_n, imp_n, comp_n = generate_segmented_noises(fs, duration)
    acoustic_path = np.array([0.05, 0.12, -0.25, 0.35, 0.18, -0.09, 0.04, -0.02, 0.01])

    tinyml = TinyMLNoiseClassifierAndStepController()

    # 1. Evaluate All Noise Segments Separately
    res_stat = evaluate_segment(clean_speech, stat_n, acoustic_path, fs, "1. Stationary Noise (Engine)", tinyml)
    res_nonstat = evaluate_segment(clean_speech, nonstat_n, acoustic_path, fs, "2. Non-Stationary Noise (Track)", tinyml)
    res_imp = evaluate_segment(clean_speech, imp_n, acoustic_path, fs, "3. Impulsive Noise (Artillery)", tinyml)
    res_comp = evaluate_segment(clean_speech, comp_n, acoustic_path, fs, "4. Composite Combat Field", tinyml)

    # Print Segmented Results Table
    print("\n------------------- SEGMENTED DEFENCE NOISE BENCHMARK REPORT -------------------")
    print(f"{'Noise Category':<32} | {'ERLE (dB)':<10} | {'STOI (In->Out)':<15} | {'PESQ (In->Out)':<15} | {'SNR Gain'}")
    print("-" * 85)
    for r in [res_stat, res_nonstat, res_imp, res_comp]:
        print(f"{r['name']:<32} | {r['erle_db']:>8.2f} dB | {r['stoi_in']:.2f} -> {r['stoi_out']:.2f}     | {r['pesq_in']:.2f} -> {r['pesq_out']:.2f}     | +{r['snr_out'] - r['snr_in']:>5.2f} dB")
    print("-" * 85)
    print("NOTE: Benchmarks include TinyML Neural Step Controller + 12b ADC DNL + 8b DAC Quantization.")
    print("      Physical chamber verification in progress.")

    # Save Audio Files
    def save_wav(filename, data):
        scaled = np.int16(np.clip(data, -1.0, 1.0) * 32767)
        filepath = os.path.join(output_dir, filename)
        wavfile.write(filepath, fs, scaled)
        return filepath

    save_wav("1_clean_throat_speech.wav", clean_speech)
    save_wav("2_ambient_cockpit_noise.wav", comp_n)
    save_wav("3_raw_throat_mixed_input.wav", res_comp["d_raw"])
    save_wav("4_processed_anc_output.wav", res_comp["e_final"])

    # Coherence Analysis
    freqs, coherence = calculate_acoustic_coherence(res_comp["d_raw"], res_comp["x_raw"], fs)

    # Plot Multi-Segment Waveforms and Intelligibility Metrics
    time_axis = np.linspace(0, duration, len(clean_speech))
    plt.figure(figsize=(14, 12))

    plt.subplot(4, 1, 1)
    plt.plot(time_axis, res_comp["d_raw"], color='orange', alpha=0.8, label='Raw Throat Sensor d(n) [Speech + Leaked 120-140dB Noise]')
    plt.plot(time_axis, clean_speech, color='blue', alpha=0.5, label='Clean Vocal Reference')
    plt.title("NIRDHVANI Tactical ANC Multi-Category Benchmark [TinyML + DTD + Blast Protection]", fontsize=12, fontweight='bold')
    plt.ylabel("Amplitude")
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)

    plt.subplot(4, 1, 2)
    plt.plot(time_axis, res_comp["x_raw"], color='red', alpha=0.7, label='Ambient Reference Mic x(n) [Tank Engine + Track + Gunfire]')
    plt.ylabel("Amplitude")
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)

    plt.subplot(4, 1, 3)
    plt.plot(time_axis, res_comp["e_final"], color='green', label=f"Processed Audio e(n) [STOI: {res_comp['stoi_out']:.2f}, PESQ: {res_comp['pesq_out']:.2f}, ERLE: {res_comp['erle_db']:.1f} dB]")
    plt.ylabel("Amplitude")
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)

    plt.subplot(4, 1, 4)
    plt.plot(freqs, coherence, color='purple', label='Magnitude-Squared Acoustic Coherence gamma^2_dx(f)')
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Coherence [0..1]")
    plt.xlim([0, 4000])
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plot_path = os.path.join(output_dir, "tacanc_waveform_analysis.png")
    plt.savefig(plot_path, dpi=200)
    plt.close()
    print(f"\n[Analysis Plot Saved] -> {plot_path}")

    # Write Benchmark Report Text
    report_path = os.path.join(output_dir, "benchmark_report.txt")
    with open(report_path, "w") as f:
        f.write("NIRDHVANI Tactical ANC Multi-Category Benchmark Report\n")
        f.write("=======================================================\n\n")
        f.write("1. Segmented Defence Noise Performance:\n")
        for r in [res_stat, res_nonstat, res_imp, res_comp]:
            f.write(f"   - {r['name']}:\n")
            f.write(f"       * ERLE Noise Reduction : {r['erle_db']:.2f} dB\n")
            f.write(f"       * STOI Intelligibility : {r['stoi_in']:.2f} (Raw) -> {r['stoi_out']:.2f} (Processed)\n")
            f.write(f"       * PESQ MOS Quality     : {r['pesq_in']:.2f} (Raw) -> {r['pesq_out']:.2f} (Processed)\n")
            f.write(f"       * SNR Gain             : +{r['snr_out'] - r['snr_in']:.2f} dB\n\n")
        f.write("2. TinyML Engine:\n")
        f.write("   - Model Architecture : 2-Layer Quantized Perceptron (8 -> 16 -> 5)\n")
        f.write("   - Dynamic mu Control : Neural Step-Size + Double-Talk Probability Freezing\n")
        f.write("   - Noise Classifier   : Stationary, Non-Stationary, Impulsive Scene Detection\n\n")
        f.write("3. Hardware Status:\n")
        f.write("   - Modeled Constraints: 12-bit ADC DNL + 8-bit DAC Quantization + Clamping Diodes\n")
        f.write("   - Verification Status: Simulation benchmark; physical chamber testing in progress.\n")
    print(f"[Benchmark Report Saved] -> {report_path}")


if __name__ == "__main__":
    run_full_simulation()
