"""
NIRDHVANI: Live Demo Bundle — Prove BOTH the Real-Time DSP and the AI/ML DPCRN Work
Noise-Isolated Impulse-Resilient Real-Time Decoupled Hardware Voice Adaptive Network Isolator

For the defence presentation, the likely question is "where's the AI?" This script answers it
honestly and visually. For 1–2 scenarios it produces, on the SAME noisy input:

  - audio_clean.wav            : clean reference speech
  - audio_noisy.wav            : noisy input d(n)
  - audio_dsp.wav              : Tier-1 real-time DSP output (deployed)
  - audio_dpcrn.wav            : Tier-2 AI/ML DPCRN output (neural net, Jetson-tier)
  - demo_<scenario>.png        : 4-panel spectrogram side-by-side of all of the above

This proves the neural model genuinely produces output (not just a claim), while the DSP
row shows why the real-time tier is deployed. The DPCRN row is NOT hidden even though it
underperforms the DSP — honesty under questioning.

  Run:  python simulation/demo_ai.py [--scenario 1] [--no-dpcrn]
"""

import os
import sys
import argparse
import numpy as np
from scipy.io import wavfile
import scipy.signal as signal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from benchmark_ai_anc import build_scenarios, build_clean_speech, ACOUSTIC_PATH
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ai"))
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
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "demo")


def spectrogram_ax(ax, sig, fs, title):
    f, t, Sxx = signal.spectrogram(sig, fs, nperseg=256, noverlap=128)
    ax.pcolormesh(t, f, 10 * np.log10(Sxx + 1e-6), shading="gouraud", cmap="magma")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Freq (Hz)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", type=int, default=1, help="Scenario index (1-7)")
    ap.add_argument("--no-dpcrn", action="store_true", help="Skip DPCRN (Tier-2) for speed")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    scenarios = build_scenarios(FS, DURATION_SEC)
    sc = scenarios[args.scenario - 1]
    t_axis, clean_speech, _ = build_clean_speech(FS, DURATION_SEC)

    x_ambient = sc["noise"]
    leaked_noise = signal.lfilter(ACOUSTIC_PATH, [1.0], x_ambient)
    d_throat = clean_speech + leaked_noise

    def to_int16(a):
        return (np.clip(a, -1.0, 1.0) * 32767).astype(np.int16)

    key = f"scenario{args.scenario}"
    wavfile.write(os.path.join(OUT_DIR, f"audio_clean.wav"), FS, to_int16(clean_speech))
    wavfile.write(os.path.join(OUT_DIR, f"audio_noisy.wav"), FS, to_int16(d_throat))

    # ---- Tier-1 DSP (deployed real-time) ----
    engine = EdgeAIRealtimeEngine(sample_rate=FS, frame_size=64)
    dsp_out = engine.enhance_hybrid_pipeline(d_throat, x_ambient)
    wavfile.write(os.path.join(OUT_DIR, f"audio_dsp.wav"), FS, to_int16(dsp_out))

    # ---- Tier-2 DPCRN (AI/ML neural net) ----
    dpcrn_out = None
    if not args.no_dpcrn and TORCH_AVAILABLE:
        ckpt = torch.load(CHECKPOINT, map_location="cpu")
        model = DPCRNSpeechEnhancer()
        model.load_state_dict(ckpt["model_state_dict"])
        model.eval()
        d_t = torch.from_numpy(d_throat).unsqueeze(0).float()
        x_t = torch.from_numpy(x_ambient).unsqueeze(0).float()
        with torch.no_grad():
            enh, _, _ = model(d_t, x_t)
        dpcrn_out = enh.squeeze(0).cpu().numpy().astype(np.float32)
        wavfile.write(os.path.join(OUT_DIR, f"audio_dpcrn.wav"), FS, to_int16(dpcrn_out))

    # ---- 4-panel figure ----
    n_panels = 4 if dpcrn_out is not None else 3
    fig, axs = plt.subplots(1, n_panels, figsize=(5.2 * n_panels, 4.2))
    if n_panels == 3:
        axs = [axs]
    fig.suptitle(f"NIRDHVANI Live Demo — {sc['name']}  (Noisy → Tier-1 DSP → Tier-2 DPCRN AI/ML)",
                 fontsize=13, fontweight="bold")
    spectrogram_ax(axs[0], d_throat, FS, "1. Noisy Input d(n)")
    spectrogram_ax(axs[1], dsp_out, FS, "2. Tier-1 DSP (deployed, real-time)")
    if dpcrn_out is not None:
        spectrogram_ax(axs[2], dpcrn_out, FS, "3. Tier-2 DPCRN (AI/ML, Jetson-tier)")
        spectrogram_ax(axs[3], clean_speech, FS, "4. Clean Reference")
    else:
        spectrogram_ax(axs[2], clean_speech, FS, "3. Clean Reference")
    plt.tight_layout()
    png_path = os.path.join(OUT_DIR, f"demo_{key}.png")
    plt.savefig(png_path, dpi=200)
    plt.close()

    print(f"\n[Demo] Scenario: {sc['name']}")
    print(f"[Demo] Bundle written to {os.path.relpath(OUT_DIR, os.getcwd())}/")
    for f in sorted(os.listdir(OUT_DIR)):
        if f.startswith("audio") or f.endswith(".png"):
            print(f"        {f}")
    print(f"\n[Demo] Figure: {os.path.relpath(png_path, os.getcwd())}")
    if dpcrn_out is None and not args.no_dpcrn:
        print("[Demo] DPCRN skipped (torch unavailable).")


if __name__ == "__main__":
    main()
