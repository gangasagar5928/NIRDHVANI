"""
NIRDHVANI: Real-World Noise Dataset & Validation Tooling
Noise-Isolated Impulse-Resilient Real-Time Decoupled Hardware Voice Adaptive Network Isolator

PURPOSE (dataset authenticity):
  The primary benchmark uses fully synthetic noise (DSP-generated Friedlander blasts,
  rotor harmonics, engine sinusoids). This module adds REAL-WORLD validation:

  1. `RealNoiseDownloader`   - pulls CC-licensed field noise from Freesound.org
                               (firing range, helicopter flyover, vehicle engine) given
                               an API token; saves into `ai/real_noise/<class>/`.
  2. `discover_real_noise()` - finds locally-downloaded real noise WAVs.
  3. `RealNoiseDataset`      - loads/resamples real noise, exposes per-class samples so
                               the real-world validation benchmark can mix them with the
                               real `waves_yesno` speech corpus.

  Honest behavior: if no real noise is available (no token, no local files), the
  validation benchmark runs on the SYNTHETIC noise and labels it "SYNTHETIC FALLBACK"
  rather than pretending it is real. Real files dropped into `ai/real_noise/<class>/`
  are picked up automatically.

Usage:
  # One-time download (requires Freesound API token; skip if unavailable)
  python ai/real_noise_dataset.py --download --token YOUR_TOKEN --count 8

  # List what real noise is available
  python ai/real_noise_dataset.py --list
"""

import os
import glob
import argparse
import numpy as np
import scipy.signal as signal

try:
    import soundfile as sf
    SF_AVAILABLE = True
except ImportError:
    SF_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Local dir where real noise WAVs are stored, one subdir per noise class.
REAL_NOISE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "real_noise")

# Freesound CC-licensed field-noise search queries (class -> query).
FREESOUND_QUERIES = {
    "GUNFIRE": "gunshot firing range",
    "HELICOPTER": "helicopter flyover rotor",
    "TANK": "diesel engine tank vehicle",
    "DRONE": "drone quadcopter motor",
    "SIREN": "siren alarm",
}

FREESOUND_API = "https://freesound.org/apiv2"


class RealNoiseDownloader:
    """Downloads CC-licensed field noise from Freesound.org (requires an API token)."""

    def __init__(self, token=None):
        self.token = token
        self.headers = {"Authorization": f"Token {token}"} if token else {}

    def search_and_download(self, query, out_dir, count=6, min_sec=4.0):
        """Searches Freesound for a query and downloads top `count` sounds to out_dir."""
        if not self.token:
            print(f"  [RealNoise] No Freesound API token — skipping '{query}' (provide --token to download).")
            return []
        if not REQUESTS_AVAILABLE:
            print("  [RealNoise] 'requests' not installed — cannot download.")
            return []

        os.makedirs(out_dir, exist_ok=True)
        r = requests.get(f"{FREESOUND_API}/search/text/",
                         headers=self.headers,
                         params={"query": query, "filter": "duration:[3.0 TO 15.0]",
                                 "fields": "id,name,duration,previews", "page_size": count},
                         timeout=30)
        r.raise_for_status()
        results = r.json().get("results", [])
        saved = []
        for i, s in enumerate(results):
            preview = s.get("previews", {}).get("preview-hq-mp3")
            if not preview:
                continue
            # Freesound previews are MP3; we store as-is and resample at load time.
            fname = os.path.join(out_dir, f"{s['id']}_{query.replace(' ', '_')}_{i}.mp3")
            with requests.get(preview, stream=True, timeout=60) as pr:
                pr.raise_for_status()
                with open(fname, "wb") as f:
                    for chunk in pr.iter_content(8192):
                        f.write(chunk)
            saved.append(fname)
            print(f"  [RealNoise] Downloaded -> {fname}")
        return saved

    def download_all(self, count=6):
        """Downloads one set per defence-noise class into ai/real_noise/<CLASS>/."""
        paths = []
        for cls, query in FREESOUND_QUERIES.items():
            out_dir = os.path.join(REAL_NOISE_DIR, cls)
            paths += self.search_and_download(query, out_dir, count=count)
        return paths


def discover_real_noise(real_noise_dir=REAL_NOISE_DIR):
    """Returns {class_name: [wav/mp3 paths]} for locally available real noise."""
    found = {}
    if not os.path.isdir(real_noise_dir):
        return found
    for sub in sorted(os.listdir(real_noise_dir)):
        sub_dir = os.path.join(real_noise_dir, sub)
        if not os.path.isdir(sub_dir):
            continue
        files = sorted(glob.glob(os.path.join(sub_dir, "*.wav")) +
                       glob.glob(os.path.join(sub_dir, "*.mp3")) +
                       glob.glob(os.path.join(sub_dir, "*.flac")))
        if files:
            found[sub.upper()] = files
    return found


class RealNoiseDataset:
    """Loads real noise files, resamples to fs, and returns a 5 s sample for a class."""

    def __init__(self, fs=16000, real_noise_dir=REAL_NOISE_DIR):
        self.fs = fs
        self.real_noise_dir = real_noise_dir
        self.available = discover_real_noise(real_noise_dir)

    def has(self, cls):
        return cls.upper() in self.available

    def sample(self, cls, duration_sec=5.0, seed=0):
        """Returns a normalized 5 s real-noise sample for `cls`, or None if unavailable."""
        files = self.available.get(cls.upper())
        if not files or not SF_AVAILABLE:
            return None
        rng = np.random.default_rng(seed)
        path = files[int(rng.integers(0, len(files)))]
        try:
            data, sr = sf.read(path)
            if len(data.shape) > 1:
                data = data[:, 0]
            data = data.astype(np.float32)
            target = int(self.fs * duration_sec)
            if sr != self.fs:
                data = signal.resample(data, int(len(data) * self.fs / sr))
            if len(data) < target:
                reps = int(np.ceil(target / len(data)))
                data = np.tile(data, reps)[:target]
            else:
                # Pick a random contiguous window
                start = int(rng.integers(0, max(1, len(data) - target)))
                data = data[start:start + target]
            data = data / (np.max(np.abs(data)) + 1e-6)
            return data
        except Exception as e:
            print(f"  [RealNoise] Failed to load {path}: {e}")
            return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true", help="Download real noise from Freesound")
    ap.add_argument("--token", default=None, help="Freesound.org API token")
    ap.add_argument("--count", type=int, default=6, help="Sounds per class")
    ap.add_argument("--list", action="store_true", help="List available real noise")
    args = ap.parse_args()

    if args.list or (args.download and not args.token):
        avail = discover_real_noise()
        if not avail:
            print("[RealNoise] No real noise found in ai/real_noise/. "
                  "Download with --download --token TOKEN, or drop real WAVs into ai/real_noise/<CLASS>/.")
        for cls, files in avail.items():
            print(f"  {cls}: {len(files)} files")
            for f in files:
                print(f"      {os.path.relpath(f, os.getcwd())}")

    if args.download:
        dl = RealNoiseDownloader(token=args.token)
        dl.download_all(count=args.count)
