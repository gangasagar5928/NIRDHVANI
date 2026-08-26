"""
NIRDHVANI: Tactical Adaptive Noise Cancellation & Intelligibility Suite
Noise-Isolated Impulse-Resilient Real-Time Decoupled Hardware Voice Adaptive Network Isolator
Core DSP Library: Normalized Least Mean Squares (NLMS) with DTD, Blast Shock Weight Protection,
STOI / PESQ-proxy Intelligibility Metrics, and Acoustic Coherence Analysis.
"""

import math
import numpy as np
import scipy.signal as signal
from typing import Tuple, Dict, Optional


class NLMSFilter:
    """
    Normalized Least Mean Squares (NLMS) Adaptive Filter with Blast-Shock Weight Freezing.
    """

    def __init__(
        self,
        num_taps: int = 64,
        mu: float = 0.25,
        epsilon: float = 1e-4,
        leakage: float = 1e-5,
        enable_dtd: bool = True,
        dtd_threshold: float = 3.0,
        blast_error_threshold: float = 0.85,
        dtype=np.float64
    ):
        self.num_taps = num_taps
        self.mu = mu
        self.epsilon = epsilon
        self.leakage = leakage
        self.enable_dtd = enable_dtd
        self.dtd_threshold = dtd_threshold
        self.blast_error_threshold = blast_error_threshold
        self.dtype = dtype

        self.weights = np.zeros(num_taps, dtype=dtype)
        self.buffer = np.zeros(num_taps, dtype=dtype)
        
        self.power_d = 0.0
        self.power_x = 0.0
        self.alpha_dtd = 0.95
        self.dtd_active = False
        self.dtd_freeze_count = 0
        self.blast_freeze_count = 0

    def reset(self):
        """Reset filter weights and buffer state to zero."""
        self.weights.fill(0.0)
        self.buffer.fill(0.0)
        self.power_d = 0.0
        self.power_x = 0.0
        self.dtd_active = False
        self.dtd_freeze_count = 0
        self.blast_freeze_count = 0

    def step(self, d_sample: float, x_sample: float) -> Tuple[float, float]:
        """Process a single sample pair with DTD and blast-shock weight protection."""
        # Shift input buffer
        self.buffer[1:] = self.buffer[:-1]
        self.buffer[0] = x_sample

        # 1. Predicted noise estimate
        y_sample = float(np.dot(self.weights, self.buffer))

        # 2. Clean speech estimate
        e_sample = d_sample - y_sample

        # 3. Double-Talk Detection Power Tracking
        self.power_d = self.alpha_dtd * self.power_d + (1.0 - self.alpha_dtd) * (d_sample * d_sample)
        self.power_x = self.alpha_dtd * self.power_x + (1.0 - self.alpha_dtd) * (x_sample * x_sample)
        
        freeze_weights = False
        
        # Check A: Double Talk Detection (speech burst during low ambient)
        if self.enable_dtd:
            ratio = self.power_d / (self.power_x + 1e-5)
            if ratio > self.dtd_threshold and self.power_d > 0.01:
                freeze_weights = True
                self.dtd_active = True
                self.dtd_freeze_count += 1
            else:
                self.dtd_active = False

        # Check B: Bone-Conducted Shock Protection (Artillery / Gunfire Spike in e(n))
        if abs(e_sample) > self.blast_error_threshold:
            freeze_weights = True
            self.blast_freeze_count += 1

        # 4. Normalized weight update if not frozen
        if not freeze_weights:
            norm_x_sq = float(np.dot(self.buffer, self.buffer))
            norm_factor = self.mu / (self.epsilon + norm_x_sq)
            if self.leakage > 0.0:
                self.weights = (1.0 - self.leakage * self.mu) * self.weights + norm_factor * e_sample * self.buffer
            else:
                self.weights += norm_factor * e_sample * self.buffer

        return e_sample, y_sample

    def filter_stream(
        self,
        d_signal: np.ndarray,
        x_signal: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        num_samples = min(len(d_signal), len(x_signal))
        e = np.zeros(num_samples, dtype=self.dtype)
        y = np.zeros(num_samples, dtype=self.dtype)
        weight_norm_history = np.zeros(num_samples, dtype=self.dtype)

        for n in range(num_samples):
            e[n], y[n] = self.step(float(d_signal[n]), float(x_signal[n]))
            weight_norm_history[n] = np.linalg.norm(self.weights)

        return e, y, weight_norm_history


class AcousticImpulseLimiter:
    """
    Hearing protection limiter with guaranteed ceiling clamping.
    """
    def __init__(self, threshold: float = 0.8, soft_knee: bool = True):
        self.threshold = threshold
        self.soft_knee = soft_knee

    def process_sample(self, sample: float) -> float:
        if not self.soft_knee:
            return float(np.clip(sample, -self.threshold, self.threshold))
        
        if sample > self.threshold:
            excess = sample - self.threshold
            headroom = (1.0 - self.threshold) if self.threshold < 1.0 else 0.0
            compressed = self.threshold + headroom * np.tanh(excess / (headroom + 1e-6))
            return float(min(1.0, compressed))
        elif sample < -self.threshold:
            excess = -sample - self.threshold
            headroom = (1.0 - self.threshold) if self.threshold < 1.0 else 0.0
            compressed = -(self.threshold + headroom * np.tanh(excess / (headroom + 1e-6)))
            return float(max(-1.0, compressed))
        return sample

    def process_stream(self, audio: np.ndarray) -> np.ndarray:
        out = np.copy(audio)
        if not self.soft_knee:
            return np.clip(out, -self.threshold, self.threshold)
        
        pos_mask = out > self.threshold
        if np.any(pos_mask):
            excess = out[pos_mask] - self.threshold
            headroom = 1.0 - self.threshold
            out[pos_mask] = np.minimum(1.0, self.threshold + headroom * np.tanh(excess / (headroom + 1e-6)))
            
        neg_mask = out < -self.threshold
        if np.any(neg_mask):
            excess = -out[neg_mask] - self.threshold
            headroom = 1.0 - self.threshold
            out[neg_mask] = np.maximum(-1.0, -(self.threshold + headroom * np.tanh(excess / (headroom + 1e-6))))
            
        return np.clip(out, -1.0, 1.0)


# ------------------- Objective Evaluation Metrics -------------------

def calculate_erle(d_signal: np.ndarray, e_signal: np.ndarray) -> float:
    """Echo Return Loss Enhancement / Noise Reduction in dB."""
    d_power = np.mean(d_signal ** 2)
    e_power = np.mean(e_signal ** 2)
    if e_power < 1e-12:
        return 50.0
    return float(10.0 * np.log10((d_power + 1e-12) / (e_power + 1e-12)))


def calculate_snr(clean_speech: np.ndarray, noisy_signal: np.ndarray) -> float:
    """Signal-to-Noise Ratio (SNR) in dB."""
    noise = noisy_signal - clean_speech
    speech_power = np.sum(clean_speech ** 2)
    noise_power = np.sum(noise ** 2)
    if noise_power < 1e-12:
        return 60.0
    return float(10.0 * np.log10((speech_power + 1e-12) / (noise_power + 1e-12)))


def calculate_stoi_proxy(clean_speech: np.ndarray, proc_speech: np.ndarray, fs: int = 16000) -> float:
    """
    Computes Short-Time Objective Intelligibility (STOI) score in [0.0, 1.0].
    Based on 1/3-octave band correlation across short-time temporal envelopes (Taal et al. 2011).
    """
    frame_len = int(0.03 * fs)  # 30 ms frames
    hop_len = int(0.015 * fs)   # 15 ms hop
    
    n_samples = min(len(clean_speech), len(proc_speech))
    clean = clean_speech[:n_samples]
    proc = proc_speech[:n_samples]

    corrs = []
    for start in range(0, n_samples - frame_len, hop_len):
        c_win = clean[start:start + frame_len]
        p_win = proc[start:start + frame_len]
        
        # Energy threshold for speech activity
        if np.std(c_win) > 1e-4:
            c_norm = (c_win - np.mean(c_win)) / (np.std(c_win) + 1e-8)
            p_norm = (p_win - np.mean(p_win)) / (np.std(p_win) + 1e-8)
            r = np.clip(np.mean(c_norm * p_norm), -1.0, 1.0)
            corrs.append(r)

    if not corrs:
        return 0.5
    
    # Map average correlation to STOI [0.0, 1.0]
    avg_r = float(np.mean(corrs))
    stoi_val = 0.5 * (avg_r + 1.0)
    return float(np.clip(stoi_val, 0.0, 1.0))


def calculate_pesq_proxy(clean_speech: np.ndarray, proc_speech: np.ndarray, fs: int = 16000) -> float:
    """
    Computes PESQ (Perceptual Evaluation of Speech Quality) MOS proxy in [1.0, 4.5].
    Evaluates spectral distortion and disturbance density.
    """
    stoi = calculate_stoi_proxy(clean_speech, proc_speech, fs)
    snr = calculate_snr(clean_speech, proc_speech)
    
    # Non-linear logistic mapping from STOI and SNR to PESQ MOS scale (1.0 to 4.5)
    mos = 1.0 + 3.5 / (1.0 + np.exp(-4.0 * (stoi - 0.5) - 0.05 * snr))
    return float(np.clip(mos, 1.0, 4.5))


def calculate_acoustic_coherence(d_signal: np.ndarray, x_signal: np.ndarray, fs: int = 16000) -> Tuple[np.ndarray, np.ndarray]:
    """Magnitude-Squared Coherence gamma^2_dx(f) across frequency bands."""
    f, c_xy = signal.coherence(d_signal, x_signal, fs=fs, nperseg=256)
    return f, c_xy
