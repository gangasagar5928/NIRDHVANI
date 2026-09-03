"""
NIRDHVANI: Full-Scale Defence AI/ML Multi-Category Speech Enhancement Benchmark Suite
Noise-Isolated Impulse-Resilient Real-Time Decoupled Hardware Voice Adaptive Network Isolator

Comprehensive evaluation of Causal Hybrid Neural Masking + Leaky-NLMS + Limiter across:
1. Stationary Engine Noise (T-90 / Arjun Tank Diesel 120 dB)
2. Non-Stationary Track Squeal (Caterpillar Track Resonance)
3. Impulsive Artillery Blast (155mm Friedlander Shockwave)
4. Gunshots & Automatic Fire (12.7mm HMG / 7.62mm Rifle)
5. Low-Altitude Drone / UAV (Quadcopter Propulsion)
6. Helicopter Rotor Noise (Blade-Vortex Interaction)
7. Composite Combat Battlefield (Multi-Threat Combined)
"""

import os
import sys
import time
import numpy as np
import scipy.signal as signal
from scipy.io import wavfile
import matplotlib.pyplot as plt

# Local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dsp_core import (
    NLMSFilter, AcousticImpulseLimiter,
    calculate_erle, calculate_snr, calculate_stoi_proxy, calculate_pesq_proxy
)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ai"))
from dataset_pipeline import DefenceNoiseGenerator, CleanSpeechGenerator, DataAugmentationEngine
from edge_inference_engine import EdgeAIRealtimeEngine


# Acoustic coupling path modeling neck skin transfer function (9-tap FIR)
ACOUSTIC_PATH = np.array([0.05, 0.12, -0.22, 0.32, 0.15, -0.08, 0.03, -0.02, 0.01])


def build_scenarios(fs, duration_sec):
    """Builds the 7 defence-noise evaluation scenarios (reusable by DSP & DPCRN benchmarks)."""
    noise_gen = DefenceNoiseGenerator(fs=fs)

    def get_tank_engine_noise():
        t = np.linspace(0, duration_sec, int(fs * duration_sec), endpoint=False)
        f_eng = 36.6
        n = (
            0.40 * np.sin(2 * np.pi * f_eng * t) +
            0.35 * np.sin(2 * np.pi * 2 * f_eng * t) +
            0.25 * np.sin(2 * np.pi * 3 * f_eng * t) +
            0.20 * np.sin(2 * np.pi * 4 * f_eng * t) +
            0.15 * np.sin(2 * np.pi * 5 * f_eng * t) +
            0.10 * np.sin(2 * np.pi * 6 * f_eng * t) +
            0.15 * np.sin(2 * np.pi * 25 * t)
        )
        return n / np.max(np.abs(n)) * 0.65

    return [
        {"name": "1. Stationary Engine (T-90 Tank)", "noise": get_tank_engine_noise(), "input_snr": 0.0},
        {"name": "2. Non-Stationary Track Squeal", "noise": noise_gen.get_noise_by_class("ARMORED_VEHICLE", duration_sec), "input_snr": 2.0},
        {"name": "3. Impulsive Artillery (155mm Blast)", "noise": noise_gen.generate_artillery_blast_noise(duration_sec), "input_snr": -5.0},
        {"name": "4. Automatic Gunfire (12.7mm HMG)", "noise": noise_gen.generate_gunshot_noise(duration_sec), "input_snr": -2.0},
        {"name": "5. Drone / UAV Propulsion", "noise": noise_gen.generate_drone_uav_noise(duration_sec), "input_snr": 5.0},
        {"name": "6. Helicopter Rotor Blade-Slap", "noise": noise_gen.generate_helicopter_noise(duration_sec), "input_snr": 3.0},
        {"name": "7. Composite Combat Battlefield", "noise": noise_gen.get_noise_by_class("COMPOSITE", duration_sec), "input_snr": 0.0}
    ]


def build_clean_speech(fs, duration_sec):
    """
    Generates rich synthetic tactical speech (formant synthesis) with PTT lead-in (0.5 s pre-calibration).

    NOTE: This is SYNTHETIC speech (formant-synthesized), not a recording. The DPCRN training
    pipeline (`ai/dataset_pipeline.py` -> `RealSpeechSource`) can substitute the real `waves_yesno`
    corpus for training; this benchmark stimulus generator keeps the input signal identical across
    the DSP and DPCRN benchmark paths for a fair head-to-head comparison.
    """
    t_axis = np.linspace(0, duration_sec, int(fs * duration_sec), endpoint=False)
    clean_speech = np.zeros_like(t_axis)
    utterances = [(0.6, 2.3), (2.8, 4.6)]
    for s_t, e_t in utterances:
        idx_u = (t_axis >= s_t) & (t_axis <= e_t)
        t_w = t_axis[idx_u] - s_t
        f0 = 128 + 14 * np.sin(2 * np.pi * 2.2 * t_w)
        phi = 2 * np.pi * np.cumsum(f0) / fs
        vocal = (np.sin(phi) + 0.60 * np.sin(2*phi) + 0.40 * np.sin(3*phi) + 0.25 * np.sin(4*phi) + 0.15 * np.sin(5*phi))
        b1, a1 = signal.butter(2, [550 / (fs/2), 850 / (fs/2)], btype='band')
        b2, a2 = signal.butter(2, [1050 / (fs/2), 1400 / (fs/2)], btype='band')
        b3, a3 = signal.butter(2, [2300 / (fs/2), 2900 / (fs/2)], btype='band')
        f1 = signal.lfilter(b1, a1, vocal)
        f2 = signal.lfilter(b2, a2, vocal)
        f3 = signal.lfilter(b3, a3, vocal)
        fric = signal.lfilter(*signal.butter(2, [3500/(fs/2), 6500/(fs/2)], btype='band'), np.random.normal(0, 0.08, len(t_w)))
        env = np.sin(np.pi * (t_w / (e_t - s_t)))
        clean_speech[idx_u] = (0.50 * f1 + 0.35 * f2 + 0.20 * f3 + 0.15 * fric) * env
    clean_speech = clean_speech / np.max(np.abs(clean_speech)) * 0.75
    return t_axis, clean_speech, utterances


def build_mixed_signals(scenarios, fs, duration_sec, clean_speech):
    """
    Builds the throat-primary d(n) and ambient-reference x(n) signals for every scenario,
    applying the 9-tap acoustic coupling path to the leaked noise.
    """
    coupled = []
    for sc in scenarios:
        raw_noise = sc["noise"]
        x_ambient = raw_noise
        leaked_noise = signal.lfilter(ACOUSTIC_PATH, [1.0], raw_noise)
        d_throat = clean_speech + leaked_noise
        coupled.append({"x_ambient": x_ambient, "leaked_noise": leaked_noise, "d_throat": d_throat})
    return coupled


def model_hardware_nonlinearities(signal_in, seed=None):
    """Models ESP32 12-bit SAR ADC DNL noise + 8-bit DAC quantization."""
    rng = np.random.default_rng(seed)
    adc_dnl_noise = rng.normal(0, (3.3 / 4096.0) * 0.05, len(signal_in))
    dac_quantized = np.round((signal_in + adc_dnl_noise + 1.0) * 127.5) / 127.5 - 1.0
    return np.clip(dac_quantized, -1.0, 1.0)


def score_result(clean_speech, d_throat, leaked_noise, processed_output, sc, t_axis, fs, is_impulsive=False):
    """Scores one processed output against the clean reference (shared by DSP & DPCRN benchmarks)."""
    speech_active = np.abs(clean_speech) > 0.02
    converged_noise_lulls = (~speech_active) & (t_axis >= 0.5) & (t_axis <= 4.8)

    # 1. Noise Reduction / ERLE (dB)
    if is_impulsive:
        peak_sample_idx = int(np.argmax(np.abs(leaked_noise)))
        shock_win = slice(max(0, peak_sample_idx - int(0.005 * fs)), min(len(processed_output), peak_sample_idx + int(0.035 * fs)))
        peak_in = float(np.max(np.abs(d_throat[shock_win])))
        peak_out = float(np.max(np.abs(processed_output[shock_win])))
        erle_val = float(20.0 * np.log10((peak_in + 1e-6) / (peak_out + 1e-6)))
    else:
        p_in = np.mean(d_throat[converged_noise_lulls] ** 2) + 1e-12
        p_out = np.mean(processed_output[converged_noise_lulls] ** 2) + 1e-12
        erle_val = float(10.0 * np.log10(p_in / p_out))

    # 2. Absolute Output SNR (dB)
    speech_pwr = np.mean(clean_speech[speech_active] ** 2) + 1e-9
    noise_residual_pwr = np.mean(processed_output[converged_noise_lulls] ** 2) + 1e-12
    out_snr = float(10.0 * np.log10(speech_pwr / noise_residual_pwr))

    # 3. Speech Intelligibility & Quality (STOI & PESQ on continuous active communication)
    spk_seg = (t_axis >= 0.6) & (t_axis <= 2.3)
    raw_stoi = calculate_stoi_proxy(clean_speech[spk_seg], d_throat[spk_seg], fs)
    out_stoi = calculate_stoi_proxy(clean_speech[spk_seg], processed_output[spk_seg], fs)

    raw_pesq = calculate_pesq_proxy(clean_speech[spk_seg], d_throat[spk_seg], fs)
    out_pesq = calculate_pesq_proxy(clean_speech[spk_seg], processed_output[spk_seg], fs)

    return {
        "output_snr": out_snr,
        "erle_db": erle_val,
        "raw_stoi": raw_stoi,
        "out_stoi": out_stoi,
        "raw_pesq": raw_pesq,
        "out_pesq": out_pesq,
    }


def run_full_defence_benchmark():
    fs = 16000
    duration_sec = 5.0

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out_dir, exist_ok=True)

    scenarios = build_scenarios(fs, duration_sec)
    t_axis, clean_speech, utterances = build_clean_speech(fs, duration_sec)

    results = []

    print("\n=========================================================================================================")
    print("  NIRDHVANI: Full-Scale Defence AI/ML Multi-Category Speech Enhancement Benchmark                        ")
    print("  [Tier-1 Causal Block-Wiener DSP + Spectral Gate + Limiter + AGC on 12b ADC / 8b DAC Model]             ")
    print("=========================================================================================================\n")

    for idx, sc in enumerate(scenarios):
        # Create fresh engine per scenario to guarantee zero cross-contamination
        # of adaptive weights, PSD trackers, and limiter state.
        engine = EdgeAIRealtimeEngine(sample_rate=fs, frame_size=64)

        raw_noise = sc["noise"]
        # Ambient mic picks up reference noise x(n)
        x_ambient = raw_noise
        # Leaked noise through neck tissue into throat sensor
        leaked_noise = signal.lfilter(ACOUSTIC_PATH, [1.0], raw_noise)
        # Primary sensor d(n)
        d_throat = clean_speech + leaked_noise

        # Process through Tier-1 Causal Edge DSP Engine (Block-Wiener + Gate + Limiter + AGC)
        start_eval_t = time.perf_counter()
        processed_output = engine.enhance_hybrid_pipeline(d_throat, x_ambient)
        eval_dur_ms = (time.perf_counter() - start_eval_t) * 1000.0
        avg_lat = eval_dur_ms / (len(clean_speech) / 64.0) # per 4.0ms frame

        # Model Hardware Non-Linearities (ESP32 12-bit SAR ADC DNL + 8-bit DAC Quantization)
        final_audio = model_hardware_nonlinearities(processed_output)

        is_impulsive = "Artillery" in sc["name"] or "Gunfire" in sc["name"]
        res = score_result(clean_speech, d_throat, leaked_noise, final_audio, sc, t_axis, fs, is_impulsive=is_impulsive)
        res["name"] = sc["name"]
        res["input_snr"] = sc["input_snr"]
        res["latency_ms"] = avg_lat
        results.append(res)

        clean_out_path = os.path.join(out_dir, f"ai_anc_case_{idx+1}_processed.wav")
        wavfile.write(clean_out_path, fs, (final_audio * 32767).astype(np.int16))

    # Print Formatted Results Table
    header = f"{'Scenario / Defence Noise Class':<35} | {'ERLE (dB)':<10} | {'Abs SNR (dB)':<12} | {'STOI (In->Out)':<18} | {'PESQ (In->Out)':<18} | {'Compute Latency'}"
    print(header)
    print("-" * 122)
    
    report_lines = [header, "-" * 122]
    
    for r in results:
        snr_pass = "PASS" if r['output_snr'] >= 15.0 else "WARN"
        stoi_pass = "PASS" if r['out_stoi'] >= 0.85 else "WARN"
        pesq_pass = "PASS" if r['out_pesq'] >= 2.5 else "WARN"
        
        line = (f"{r['name']:<35} | {r['erle_db']:>7.2f} dB | {r['output_snr']:>9.2f} dB | "
                f"{r['raw_stoi']:.2f} -> {r['out_stoi']:.2f} ({stoi_pass}) | "
                f"{r['raw_pesq']:.2f} -> {r['out_pesq']:.2f} ({pesq_pass}) | {r['latency_ms']:.2f} ms")
        print(line)
        report_lines.append(line)
        
    print("-" * 122)
    
    # Save Report
    report_path = os.path.join(out_dir, "ai_anc_benchmark_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"\n[Benchmark Report Saved] -> {report_path}")
    
    # Generate Plots
    plot_path = os.path.join(out_dir, "ai_anc_spectral_analysis.png")
    generate_benchmark_plots(clean_speech, d_throat, final_audio, fs, plot_path)
    print(f"[Analysis Plot Saved] -> {plot_path}\n")
    
    return results


def generate_benchmark_plots(clean, noisy, enhanced, fs, save_path):
    t = np.linspace(0, len(clean) / fs, len(clean))
    fig, axs = plt.subplots(3, 2, figsize=(14, 10))
    fig.suptitle("NIRDHVANI: Full-Scale Causal AI/ML Speech Enhancement Analysis", fontsize=14, fontweight='bold')
    
    axs[0, 0].plot(t, clean, color='#0066cc', lw=1.0)
    axs[0, 0].set_title("1. Clean Reference Speech s(n)")
    axs[0, 0].set_ylabel("Amplitude")
    axs[0, 0].grid(True, alpha=0.3)
    
    axs[1, 0].plot(t, noisy, color='#cc3300', lw=0.8)
    axs[1, 0].set_title("2. Noisy Input d(n) (Speech + 120 dB Tank Noise)")
    axs[1, 0].set_ylabel("Amplitude")
    axs[1, 0].grid(True, alpha=0.3)
    
    axs[2, 0].plot(t, enhanced, color='#009933', lw=1.0)
    axs[2, 0].set_title("3. Enhanced Output (Causal Neural Mask + NLMS + Limiter)")
    axs[2, 0].set_xlabel("Time (seconds)")
    axs[2, 0].set_ylabel("Amplitude")
    axs[2, 0].grid(True, alpha=0.3)
    
    f_c, t_c, Sxx_c = signal.spectrogram(clean, fs, nperseg=256)
    axs[0, 1].pcolormesh(t_c, f_c, 10 * np.log10(Sxx_c + 1e-6), shading='gouraud', cmap='magma')
    axs[0, 1].set_title("Clean Speech Spectrogram")
    axs[0, 1].set_ylabel("Freq (Hz)")
    
    f_n, t_n, Sxx_n = signal.spectrogram(noisy, fs, nperseg=256)
    axs[1, 1].pcolormesh(t_n, f_n, 10 * np.log10(Sxx_n + 1e-6), shading='gouraud', cmap='magma')
    axs[1, 1].set_title("Noisy Input Spectrogram")
    axs[1, 1].set_ylabel("Freq (Hz)")
    
    f_e, t_e, Sxx_e = signal.spectrogram(enhanced, fs, nperseg=256)
    axs[2, 1].pcolormesh(t_e, f_e, 10 * np.log10(Sxx_e + 1e-6), shading='gouraud', cmap='magma')
    axs[2, 1].set_title("Enhanced Speech Spectrogram")
    axs[2, 1].set_xlabel("Time (seconds)")
    axs[2, 1].set_ylabel("Freq (Hz)")
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=200)
    plt.close()


if __name__ == "__main__":
    run_full_defence_benchmark()
