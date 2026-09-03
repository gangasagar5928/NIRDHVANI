"""
NIRDHVANI: Real-World Validation Subset — Synthetic vs Real Noise Benchmark
Noise-Isolated Impulse-Resilient Real-Time Decoupled Hardware Voice Adaptive Network Isolator

PURPOSE (dataset authenticity):
  The primary benchmark (§5.1) uses fully SYNTHETIC noise and SYNTHETIC speech. This script
  re-runs a subset of the 7 scenarios with the maximum real content available in-repo:
    - REAL speech from the `waves_yesno` open speech corpus (ai/corpus/waves_yesno, 62 files).
    - REAL noise (if present in ai/real_noise/<CLASS>/ after `--download` or manual drop),
      otherwise SYNTHETIC noise CLEARLY LABELLED "SYNTHETIC FALLBACK" — we never pretend.

  Output: a "Synthetic Benchmark" vs "Real-World Validation" comparison table so the defence
  jury can see the synthetic numbers are not the only evidence.

  Run:
    python simulation/benchmark_real_world.py
    python simulation/benchmark_real_world.py --download-real --token TOKEN   # fetch CC noise first
"""

import os
import sys
import time
import argparse
import numpy as np
from scipy.io import wavfile
import scipy.signal as signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from benchmark_ai_anc import (
    build_scenarios, build_clean_speech, model_hardware_nonlinearities,
    score_result, ACOUSTIC_PATH,
)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ai"))
from dataset_pipeline import DefenceNoiseGenerator, CleanSpeechGenerator
from real_noise_dataset import RealNoiseDataset, RealNoiseDownloader, discover_real_noise
from edge_inference_engine import EdgeAIRealtimeEngine
from model_dpcrn import DPCRNSpeechEnhancer

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

FS = 16000
DURATION_SEC = 5.0
CHECKPOINT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "checkpoints", "best_model.pth")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# Map validation scenarios to real-noise classes (aligns with the 7-scenario benchmark).
VALIDATION_CLASSES = {
    "1. Stationary Engine (T-90 Tank)": "TANK",
    "4. Automatic Gunfire (12.7mm HMG)": "GUNFIRE",
    "5. Drone / UAV Propulsion": "DRONE",
    "6. Helicopter Rotor Blade-Slap": "HELICOPTER",
}


def get_validation_scenarios():
    """Returns scenarios to validate, with real noise if available else synthetic fallback."""
    real_ds = RealNoiseDataset(fs=FS)
    synth_gen = DefenceNoiseGenerator(fs=FS)
    scenarios = []
    for sc in build_scenarios(FS, DURATION_SEC):
        cls = VALIDATION_CLASSES.get(sc["name"])
        if cls is None:
            continue
        real_noise = real_ds.sample(cls, duration_sec=DURATION_SEC)
        if real_noise is not None:
            scenarios.append({"name": sc["name"], "input_snr": sc["input_snr"],
                              "noise": real_noise, "real": True, "class": cls})
        else:
            # Synthetic fallback (labelled honestly). Aligns synthetic class to scenario name.
            synthetic_noise = None
            if "Gunfire" in sc["name"]:
                synthetic_noise = synth_gen.generate_gunshot_noise(DURATION_SEC)
            elif "Drone" in sc["name"]:
                synthetic_noise = synth_gen.generate_drone_uav_noise(DURATION_SEC)
            elif "Helicopter" in sc["name"]:
                synthetic_noise = synth_gen.generate_helicopter_noise(DURATION_SEC)
            elif "Tank" in sc["name"]:
                synthetic_noise = synth_gen.get_noise_by_class("ARMORED_VEHICLE", DURATION_SEC)
            scenarios.append({"name": sc["name"], "input_snr": sc["input_snr"],
                              "noise": synthetic_noise, "real": False, "class": cls})
    return scenarios


def run_dsp(fs, d_throat, x_ambient):
    engine = EdgeAIRealtimeEngine(sample_rate=fs, frame_size=64)
    proc = engine.enhance_hybrid_pipeline(d_throat, x_ambient)
    return model_hardware_nonlinearities(proc)


def run_dpcrn(model, d_throat, x_ambient):
    d_t = torch.from_numpy(d_throat).unsqueeze(0).float()
    x_t = torch.from_numpy(x_ambient).unsqueeze(0).float()
    with torch.no_grad():
        enh, _, _ = model(d_t, x_t)
    return enh.squeeze(0).cpu().numpy().astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download-real", action="store_true", help="Download CC real noise from Freesound first")
    ap.add_argument("--token", default=None, help="Freesound.org API token")
    ap.add_argument("--no-dpcrn", action="store_true", help="Skip DPCRN (Tier-2) for speed")
    args = ap.parse_args()

    if args.download_real:
        dl = RealNoiseDownloader(token=args.token)
        dl.download_all(count=6)
        print()

    scenarios = get_validation_scenarios()
    avail = discover_real_noise()
    print(f"[RealWorld] Real-noise classes available: {sorted(avail) or 'NONE (using synthetic fallback)'}")

    # Real speech from waves_yesno corpus
    speech_gen = CleanSpeechGenerator(fs=FS, corpus_dir=os.path.join("ai", "corpus", "waves_yesno"))
    clean_speech = speech_gen.generate_tactical_speech(DURATION_SEC)
    t_axis = np.linspace(0, DURATION_SEC, len(clean_speech), endpoint=False)
    clean_speech = clean_speech / (np.max(np.abs(clean_speech)) + 1e-6) * 0.75

    model = None
    if not args.no_dpcrn and TORCH_AVAILABLE:
        ckpt = torch.load(CHECKPOINT, map_location="cpu")
        model = DPCRNSpeechEnhancer()
        model.load_state_dict(ckpt["model_state_dict"])
        model.eval()
        print(f"[DPCRN] Loaded checkpoint (epoch={ckpt.get('epoch')}, val_SI-SNR={ckpt.get('val_sisnr'):.2f} dB)\n")
    elif not args.no_dpcrn:
        print("[DPCRN] torch unavailable — Tier-2 DPCRN skipped.\n")

    print("=" * 120)
    print("  NIRDHVANI: Real-World Validation Subset — Synthetic vs Real Noise")
    print("  Speech: REAL (waves_yesno corpus)   |   Noise: REAL if available, else labelled SYNTHETIC FALLBACK")
    print("=" * 120)

    hdr = (f"{'Scenario':<34} | {'Noise Src':<20} | {'Tier':<6} | {'SNR(dB)':>7} | "
           f"{'STOI In->Out':>15} | {'PESQ In->Out':>15}")
    lines = [hdr, "-" * 118]
    print(hdr)
    print("-" * 118)

    for sc in scenarios:
        noise_src = "REAL" if sc["real"] else "SYNTH-FALLBACK"
        x_ambient = sc["noise"]
        leaked_noise = signal.lfilter(ACOUSTIC_PATH, [1.0], x_ambient)
        d_throat = clean_speech + leaked_noise
        is_impulsive = "Artillery" in sc["name"] or "Gunfire" in sc["name"]

        dsp_out = run_dsp(FS, d_throat, x_ambient)
        dsp = score_result(clean_speech, d_throat, leaked_noise, dsp_out, sc, t_axis, FS, is_impulsive=is_impulsive)
        line = (f"{sc['name']:<34} | {noise_src:<20} | {'DSP':<6} | {dsp['output_snr']:>6.1f} | "
                f"{dsp['raw_stoi']:.2f}->{dsp['out_stoi']:.2f} | {dsp['raw_pesq']:.2f}->{dsp['out_pesq']:.2f}")
        lines.append(line)
        print(line)

        if model is not None:
            dpcrn_out = run_dpcrn(model, d_throat, x_ambient)
            dpcrn = score_result(clean_speech, d_throat, leaked_noise, dpcrn_out, sc, t_axis, FS, is_impulsive=is_impulsive)
            line = (f"{sc['name']:<34} | {noise_src:<20} | {'DPCRN':<6} | {dpcrn['output_snr']:>6.1f} | "
                    f"{dpcrn['raw_stoi']:.2f}->{dpcrn['out_stoi']:.2f} | {dpcrn['raw_pesq']:.2f}->{dpcrn['out_pesq']:.2f}")
            lines.append(line)
            print(line)
    print("-" * 118)

    os.makedirs(OUT_DIR, exist_ok=True)
    report_path = os.path.join(OUT_DIR, "real_world_validation_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        f.write("\n\nNOTES:\n"
                "- Speech source: REAL waves_yesno open speech corpus (ai/corpus/waves_yesno).\n"
                "- Noise source: REAL if CC field recordings are present in ai/real_noise/<CLASS>/\n"
                "  (fetch with --download-real --token TOKEN, or drop real WAVs in). Otherwise the\n"
                "  row is labelled 'SYNTH-FALLBACK' to be transparent.\n"
                "- Tier-1 DSP scored after modeled 8-bit DAC quantization; Tier-2 DPCRN on raw 24-bit output.\n")
    print(f"\n[Real-World Validation Report Saved] -> {report_path}")
    print("Note: run `python ai/real_noise_dataset.py --download --token <FREESOUND_TOKEN>` then re-run "
          "to populate REAL noise; without it the rows above are honest synthetic-fallback values.")


if __name__ == "__main__":
    main()
