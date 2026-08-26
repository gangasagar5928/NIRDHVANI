"""
NIRDHVANI: Tactical Adaptive Noise Cancellation
Noise-Isolated Impulse-Resilient Real-Time Decoupled Hardware Voice Adaptive Network Isolator
Core DSP Library: Normalized Least Mean Squares (NLMS) with DTD & Impulse Limiting Algorithms
"""

import numpy as np
from typing import Tuple, Optional


class NLMSFilter:
    """
    Normalized Least Mean Squares (NLMS) Adaptive Filter with Double-Talk Detection.
    
    Mathematical Formulation:
    1. Filter Output (Predicted Noise):
       y(n) = w^T(n) * x(n) = sum_{k=0}^{N-1} w_k(n) * x(n-k)
       
    2. Error Signal (Clean Speech Estimate):
       e(n) = d(n) - y(n)
       
    3. Double-Talk Detection (DTD):
       P_d(n) = alpha * P_d(n-1) + (1-alpha) * d^2(n)
       P_x(n) = alpha * P_x(n-1) + (1-alpha) * x^2(n)
       if P_d(n) / (P_x(n) + eps) > dtd_threshold: freeze weight update
       
    4. Normalized Weight Update Equation:
       w(n+1) = (1 - gamma * mu) * w(n) + [mu / (epsilon + ||x(n)||^2)] * e(n) * x(n)
    """

    def __init__(
        self,
        num_taps: int = 64,
        mu: float = 0.25,
        epsilon: float = 1e-4,
        leakage: float = 1e-5,
        enable_dtd: bool = True,
        dtd_threshold: float = 3.0,
        dtype=np.float64
    ):
        assert num_taps > 0, "Number of taps must be positive"
        assert 0.0 < mu <= 2.0, "Step-size mu must be in (0, 2]"
        assert epsilon > 0.0, "Epsilon regularizer must be positive"
        
        self.num_taps = num_taps
        self.mu = mu
        self.epsilon = epsilon
        self.leakage = leakage
        self.enable_dtd = enable_dtd
        self.dtd_threshold = dtd_threshold
        self.dtype = dtype

        self.weights = np.zeros(num_taps, dtype=dtype)
        self.buffer = np.zeros(num_taps, dtype=dtype)
        
        self.power_d = 0.0
        self.power_x = 0.0
        self.alpha_dtd = 0.95
        self.dtd_active = False
        self.dtd_freeze_count = 0

    def reset(self):
        """Reset filter weights and buffer state to zero."""
        self.weights.fill(0.0)
        self.buffer.fill(0.0)
        self.power_d = 0.0
        self.power_x = 0.0
        self.dtd_active = False
        self.dtd_freeze_count = 0

    def step(self, d_sample: float, x_sample: float) -> Tuple[float, float]:
        """Process a single sample pair (d(n), x(n)) in real time with DTD protection."""
        # Shift input buffer
        self.buffer[1:] = self.buffer[:-1]
        self.buffer[0] = x_sample

        # 1. Compute predicted noise y(n) = w^T * x
        y_sample = float(np.dot(self.weights, self.buffer))

        # 2. Compute error signal e(n) = d(n) - y(n)
        e_sample = d_sample - y_sample

        # 3. Double-Talk Detection
        self.power_d = self.alpha_dtd * self.power_d + (1.0 - self.alpha_dtd) * (d_sample * d_sample)
        self.power_x = self.alpha_dtd * self.power_x + (1.0 - self.alpha_dtd) * (x_sample * x_sample)
        
        freeze_weights = False
        if self.enable_dtd:
            ratio = self.power_d / (self.power_x + 1e-5)
            if ratio > self.dtd_threshold and self.power_d > 0.01:
                freeze_weights = True
                self.dtd_active = True
                self.dtd_freeze_count += 1
            else:
                self.dtd_active = False

        # 4. Weight update if not frozen by DTD
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
    Tactical Hearing Protection: Fast Soft Tanh / Hard Peak Limiter.
    Suppresses extreme acoustic shocks (>120 dB blast impulses).
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


# Metrics & Evaluation
def calculate_erle(d_signal: np.ndarray, e_signal: np.ndarray, frame_size: int = 256) -> float:
    """Compute Echo Return Loss Enhancement (ERLE) / Noise Reduction in dB."""
    d_power = np.mean(d_signal ** 2)
    e_power = np.mean(e_signal ** 2)
    if e_power < 1e-12:
        return 50.0
    return float(10.0 * np.log10((d_power + 1e-12) / (e_power + 1e-12)))


def calculate_snr(clean_speech: np.ndarray, noisy_signal: np.ndarray) -> float:
    """Compute Signal-to-Noise Ratio (SNR) in dB."""
    noise = noisy_signal - clean_speech
    speech_power = np.sum(clean_speech ** 2)
    noise_power = np.sum(noise ** 2)
    if noise_power < 1e-12:
        return 60.0
    return float(10.0 * np.log10(speech_power / noise_power))
