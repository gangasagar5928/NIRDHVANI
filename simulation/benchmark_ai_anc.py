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


def run_full_defence_benchmark():
    fs = 16000
    duration_sec = 5.0
    
    noise_gen = DefenceNoiseGenerator(fs=fs)
    speech_gen = CleanSpeechGenerator(fs=fs)
    aug_engine = DataAugmentationEngine(fs=fs)
    
    clean_speech = speech_gen.generate_tactical_speech(duration_sec=duration_sec)
    
    # 7 Comprehensive Evaluation Scenarios
    scenarios = [
        {"name": "1. Stationary Engine (T-90 Tank)", "noise": noise_gen.generate_armored_vehicle_noise(duration_sec), "input_snr": 0.0},
        {"name": "2. Non-Stationary Track Squeal", "noise": noise_gen.get_noise_by_class("ARMORED_VEHICLE", duration_sec), "input_snr": 2.0},
        {"name": "3. Impulsive Artillery (155mm Blast)", "noise": noise_gen.generate_artillery_blast_noise(duration_sec), "input_snr": -5.0},
        {"name": "4. Automatic Gunfire (12.7mm HMG)", "noise": noise_gen.generate_gunshot_noise(duration_sec), "input_snr": -2.0},
        {"name": "5. Drone / UAV Propulsion", "noise": noise_gen.generate_drone_uav_noise(duration_sec), "input_snr": 5.0},
        {"name": "6. Helicopter Rotor Blade-Slap", "noise": noise_gen.generate_helicopter_noise(duration_sec), "input_snr": 3.0},
        {"name": "7. Composite Combat Battlefield", "noise": noise_gen.get_noise_by_class("COMPOSITE", duration_sec), "input_snr": 0.0}
    ]
    
    # Acoustic coupling path modeling neck skin transfer function (9-tap FIR)
    acoustic_path = np.array([0.05, 0.12, -0.22, 0.32, 0.15, -0.08, 0.03, -0.02, 0.01])
    
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out_dir, exist_ok=True)
    
    results = []
    
    print("\n=========================================================================================================")
    print("  NIRDHVANI: Full-Scale Defence AI/ML Multi-Category Speech Enhancement Benchmark                        ")
    print("  [Causal Sub-Band Neural Masking + Leaky-NLMS + Soft-Tanh Limiter on 12b ADC / 8b DAC Model]            ")
    print("=========================================================================================================\n")
    
    for idx, sc in enumerate(scenarios):
        raw_noise = sc["noise"]
        # Ambient mic picks up reference noise x(n)
        x_ambient = raw_noise
        # Leaked noise through neck tissue into throat sensor
        leaked_noise = signal.lfilter(acoustic_path, [1.0], raw_noise)
        # Primary sensor d(n)
        d_throat = clean_speech + leaked_noise
        
        # Process through Causal Edge AI Real-Time Engine (64-sample frames, zero lookahead)
        engine = EdgeAIRealtimeEngine(sample_rate=fs, frame_size=64)
        
        num_frames = len(clean_speech) // 64
        processed_output = np.zeros_like(clean_speech)
        frame_latencies = []
        
        for f in range(num_frames):
            start_i = f * 64
            end_i = start_i + 64
            d_chk = d_throat[start_i:end_i]
            x_chk = x_ambient[start_i:end_i]
            
            out_chk, lat_ms = engine.process_streaming_chunk(d_chk, x_chk)
            processed_output[start_i:end_i] = out_chk
            frame_latencies.append(lat_ms)
            
        # Model Hardware Non-Linearities (ESP32 12-bit SAR ADC DNL + 8-bit DAC Quantization)
        adc_dnl_noise = np.random.normal(0, (3.3 / 4096.0) * 0.10, len(processed_output))
        dac_quantized = np.round((processed_output + adc_dnl_noise + 1.0) * 127.5) / 127.5 - 1.0
        final_audio = np.clip(dac_quantized, -1.0, 1.0)
        
        # Noise-only evaluation mask: Post-convergence noise lulls (t >= 0.5s during speech pauses)
        t_axis = np.linspace(0, duration_sec, len(clean_speech))
        speech_active = np.abs(clean_speech) > 0.05
        converged_noise_lulls = (~speech_active) & (t_axis >= 0.5)
        
        # 1. Noise Reduction / ERLE (dB)
        if "Artillery" in sc["name"] or "Gunfire" in sc["name"]:
            # Peak blast shock impulse suppression
            peak_sample_idx = int(np.argmax(np.abs(leaked_noise)))
            shock_win = slice(max(0, peak_sample_idx - int(0.005 * fs)), min(len(final_audio), peak_sample_idx + int(0.035 * fs)))
            peak_in = float(np.max(np.abs(d_throat[shock_win])))
            peak_out = float(np.max(np.abs(final_audio[shock_win])))
            erle_val = float(20.0 * np.log10((peak_in + 1e-6) / (peak_out + 1e-6)))
        else:
            p_in = np.mean(d_throat[converged_noise_lulls] ** 2) + 1e-12
            p_out = np.mean(final_audio[converged_noise_lulls] ** 2) + 1e-12
            erle_val = float(10.0 * np.log10(p_in / p_out))
            
        # 2. Absolute Output SNR (dB)
        speech_pwr = np.mean(clean_speech[speech_active] ** 2) + 1e-9
        noise_residual_pwr = np.mean((final_audio[converged_noise_lulls]) ** 2) + 1e-12
        out_snr = float(10.0 * np.log10(speech_pwr / noise_residual_pwr))
        
        # 3. Speech Intelligibility & Quality (STOI & PESQ)
        raw_stoi = calculate_stoi_proxy(clean_speech, d_throat, fs)
        out_stoi = calculate_stoi_proxy(clean_speech, final_audio, fs)
        
        raw_pesq = calculate_pesq_proxy(clean_speech, d_throat, fs)
        out_pesq = calculate_pesq_proxy(clean_speech, final_audio, fs)
        
        avg_lat = float(np.mean(frame_latencies))
        
        res = {
            "name": sc["name"],
            "input_snr": sc["input_snr"],
            "output_snr": out_snr,
            "erle_db": erle_val,
            "raw_stoi": raw_stoi,
            "out_stoi": out_stoi,
            "raw_pesq": raw_pesq,
            "out_pesq": out_pesq,
            "latency_ms": avg_lat
        }
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
