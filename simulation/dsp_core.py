"""
NIRDHVANI: Tactical Adaptive Noise Cancellation
Noise-Isolated Impulse-Resilient Real-Time Decoupled Hardware Voice Adaptive Network Isolator
Core DSP Library: Normalized Least Mean Squares (NLMS) & Impulse Limiting Algorithms
"""

import numpy as np
from typing import Tuple, Optional


class NLMSFilter:
    """
    Normalized Least Mean Squares (NLMS) Adaptive Filter.
    
    Mathematical Formulation:
    1. Filter Output (Predicted Noise):
       y(n) = w^T(n) * x(n) = sum_{k=0}^{N-1} w_k(n) * x(n-k)
       
    2. Error Signal (Clean Speech Estimate):
       e(n) = d(n) - y(n)
       
    3. Power Estimation:
       P_x(n) = ||x(n)||^2 = sum_{k=0}^{N-1} x^2(n-k)
       
    4. Weight Update Equation:
       w(n+1) = w(n) + [mu / (epsilon + P_x(n))] * e(n) * x(n)
       
    With Leakage factor gamma (Leaky NLMS for drift prevention):
       w(n+1) = (1 - gamma * mu) * w(n) + [mu / (epsilon + P_x(n))] * e(n) * x(n)
    """

    def __init__(
        self,
        num_taps: int = 64,
        mu: float = 0.25,
        epsilon: float = 1e-4,
        leakage: float = 0.0,
        dtype=np.float64
    ):
        """
        Initialize NLMS Adaptive Filter.

        Parameters:
        -----------
        num_taps : int
            Filter length (number of FIR coefficients / taps).
        mu : float
            Step-size adaptation rate (0.0 < mu <= 1.0).
        epsilon : float
            Regularization parameter to avoid division by zero during silence.
        leakage : float
            Leakage coefficient to prevent weight drift (gamma).
        """
        assert num_taps > 0, "Number of taps must be positive"
        assert 0.0 < mu <= 2.0, "Step-size mu must be in (0, 2]"
        assert epsilon > 0.0, "Epsilon regularizer must be positive"
        
        self.num_taps = num_taps
        self.mu = mu
        self.epsilon = epsilon
        self.leakage = leakage
        self.dtype = dtype

        # Filter weights w(n) and input history buffer x(n)
        self.weights = np.zeros(num_taps, dtype=dtype)
        self.buffer = np.zeros(num_taps, dtype=dtype)

    def reset(self):
        """Reset filter weights and buffer state to zero."""
        self.weights.fill(0.0)
        self.buffer.fill(0.0)

    def step(self, d_sample: float, x_sample: float) -> Tuple[float, float]:
        """
        Process a single sample pair (d(n), x(n)) in real time.

        Parameters:
        -----------
        d_sample : float
            Desired signal sample (Throat mic: speech + residual noise).
        x_sample : float
            Reference signal sample (Ambient airborne noise).

        Returns:
        --------
        e_sample : float
            Error signal (Filtered clean speech estimate).
        y_sample : float
            Predicted noise estimate.
        """
        # Shift input buffer and insert new sample at index 0
        self.buffer[1:] = self.buffer[:-1]
        self.buffer[0] = x_sample

        # 1. Compute predicted noise y(n) = w^T * x
        y_sample = float(np.dot(self.weights, self.buffer))

        # 2. Compute error signal e(n) = d(n) - y(n)
        e_sample = d_sample - y_sample

        # 3. Compute energy of current input buffer: ||x(n)||^2
        norm_x_sq = float(np.dot(self.buffer, self.buffer))

        # 4. Normalized step size: mu / (epsilon + ||x||^2)
        norm_factor = self.mu / (self.epsilon + norm_x_sq)

        # 5. Update weights with optional leakage
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
        """
        Process batch / block streaming audio.

        Returns:
        --------
        e : np.ndarray
            Clean speech error output.
        y : np.ndarray
            Estimated noise signal.
        weight_history : np.ndarray
            Trajectory of weight norms over time (for convergence analysis).
        """
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
        """
        Parameters:
        -----------
        threshold : float
            Maximum allowable normalized amplitude (|amp| <= 1.0).
        soft_knee : bool
            If True, uses smooth tanh compression curve. If False, hard clips.
        """
        self.threshold = threshold
        self.soft_knee = soft_knee

    def process_sample(self, sample: float) -> float:
        """Apply limiting to single audio sample."""
        if not self.soft_knee:
            return float(np.clip(sample, -self.threshold, self.threshold))
        
        # Soft tanh compression when exceeding threshold
        if abs(sample) > self.threshold:
            sign = np.sign(sample)
            excess = abs(sample) - self.threshold
            # Smoothly compress excess above threshold
            compressed = self.threshold + (1.0 - self.threshold) * np.tanh(excess / (1.0 - self.threshold + 1e-6))
            return float(sign * min(compressed, 1.0))
        return sample

    def process_stream(self, audio: np.ndarray) -> np.ndarray:
        """Vectorized stream processing."""
        out = np.copy(audio)
        if not self.soft_knee:
            return np.clip(out, -self.threshold, self.threshold)
        
        mask = np.abs(out) > self.threshold
        excess = np.abs(out[mask]) - self.threshold
        scale = 1.0 - self.threshold + 1e-6
        out[mask] = np.sign(out[mask]) * (self.threshold + scale * np.tanh(excess / scale))
        return np.clip(out, -1.0, 1.0)


# Metrics & Evaluation
def calculate_erle(d_signal: np.ndarray, e_signal: np.ndarray, frame_size: int = 256) -> float:
    """
    Compute Echo Return Loss Enhancement (ERLE) / Noise Reduction in dB.
    ERLE = 10 * log10( E[d^2(n)] / E[e^2(n)] ) during noise-only segments.
    """
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
