"""
NIRDHVANI: Tactical Adaptive Noise Cancellation & Intelligibility Suite
Noise-Isolated Impulse-Resilient Real-Time Decoupled Hardware Voice Adaptive Network Isolator
Core DSP Library: Block-Wiener Adaptive Canceller, NLMS with DTD, Blast Shock Weight Protection,
Spectral Residual Gate, STOI / PESQ-proxy Intelligibility Metrics, and Acoustic Coherence Analysis.
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


class BlockWienerCanceller:
    """
    Causal Block-Wiener Adaptive Noise Canceller with forgetting factor.

    Identifies the acoustic coupling path H between the noise reference x(n)
    and the primary sensor d(n) via recursive least-squares on a sliding block.

    Architecture:
    - Maintains running auto-correlation Rxx and cross-correlation rxd
    - Forgets old statistics with exponential forgetting factor λ
    - Recomputes weight vector w = Rxx⁻¹ rxd every `block_size` samples
    - Output: e(n) = d(n) − wᵀ·x_vec(n)

    This replaces the standard NLMS for ANC in the throat-mic + ambient-ref
    configuration where x(n) contains only noise (no speech leakage), making
    the least-squares path estimate unbiased even when speech is present in d(n).

    Parameters
    ----------
    num_taps : int
        FIR filter length (must exceed the true acoustic coupling path length).
    block_size : int
        Number of samples between weight recomputations.
    forgetting : float
        Exponential forgetting factor λ ∈ (0, 1]. 1.0 = infinite memory (batch).
    reg : float
        Tikhonov regularization for Rxx inversion stability.
    impulse_sigma : float
        If > 0, samples whose |e(n)| exceeds impulse_sigma × running RMS of x
        are excluded from Rxx/rxd to prevent impulse-induced weight corruption.
    """

    def __init__(self, num_taps: int = 64, block_size: int = 512,
                 forgetting: float = 0.995, reg: float = 1e-3,
                 impulse_sigma: float = 5.0):
        self.num_taps = num_taps
        self.block_size = block_size
        self.forgetting = forgetting
        self.reg = reg
        self.impulse_sigma = impulse_sigma
        self.reset()

    def reset(self):
        T = self.num_taps
        self.Rxx = np.zeros((T, T), dtype=np.float64)
        self.rxd = np.zeros(T, dtype=np.float64)
        # Per-block accumulation buffers (forgetting applied once per block)
        self.Rxx_block = np.zeros((T, T), dtype=np.float64)
        self.rxd_block = np.zeros(T, dtype=np.float64)
        self.weights = np.zeros(T, dtype=np.float64)
        self.x_buf = np.zeros(T, dtype=np.float64)
        self.samples_since_update = 0
        self.total_samples = 0
        self.rms_x_ema = 0.01  # exponential moving average of |x|

    def step(self, d_sample: float, x_sample: float) -> Tuple[float, float]:
        """
        Process one sample pair. Returns (error, predicted_noise).

        Statistics are accumulated within a block WITHOUT per-sample forgetting,
        then folded into the long-memory Rxx/rxd (with forgetting factor) at each
        block boundary, and weights are recomputed. This yields the long effective
        memory needed to identify the static acoustic coupling path while still
        adapting slowly to path drift.
        """
        # Shift causal buffer: x_buf = [x[n], x[n-1], ..., x[n-T+1]]
        self.x_buf[1:] = self.x_buf[:-1]
        self.x_buf[0] = x_sample

        # Current output with converged weights
        y = float(np.dot(self.weights, self.x_buf))
        e = d_sample - y

        # Update running RMS of x for impulse detection
        self.rms_x_ema = 0.999 * self.rms_x_ema + 0.001 * abs(x_sample)

        # Impulse rejection: skip stats accumulation for impulsive outliers
        is_impulse = False
        if self.impulse_sigma > 0 and self.total_samples > self.num_taps:
            is_impulse = abs(e) > self.impulse_sigma * max(self.rms_x_ema, 1e-6)

        # Accumulate block statistics (no forgetting within the block)
        if not is_impulse:
            self.Rxx_block += np.outer(self.x_buf, self.x_buf)
            self.rxd_block += self.x_buf * d_sample

        self.samples_since_update += 1
        self.total_samples += 1

        # Fold block into long-memory statistics and recompute weights
        if self.samples_since_update >= self.block_size:
            self.Rxx = self.forgetting * self.Rxx + self.Rxx_block
            self.rxd = self.forgetting * self.rxd + self.rxd_block
            self.Rxx_block.fill(0.0)
            self.rxd_block.fill(0.0)
            try:
                self.weights = np.linalg.solve(
                    self.Rxx + self.reg * np.eye(self.num_taps), self.rxd
                )
            except np.linalg.LinAlgError:
                pass  # keep previous weights on singular matrix
            self.samples_since_update = 0

        return e, y

    def filter_stream(self, d_signal: np.ndarray, x_signal: np.ndarray) -> np.ndarray:
        """Process full signal, returns error signal."""
        n = min(len(d_signal), len(x_signal))
        self.reset()
        e = np.zeros(n, dtype=np.float64)
        for i in range(n):
            e[i], _ = self.step(float(d_signal[i]), float(x_signal[i]))
        return e


class SpectralResidualGate:
    """
    Conservative residual-noise-floor tracking spectral gate (Martin 2001).

    Estimates the actual residual noise PSD via minimum statistics on the
    canceller's output, NOT the full reference PSD. The full reference PSD is
    ~100x larger than the true residual noise floor (because the Wiener
    already cancelled most of it), so using the reference causes over-
    suppression of speech formants (STOI degradation).

    Instead, this gate:
    1. Tracks the RESIDUAL PSD minimum over a 1.5 s sliding window as the
       noise-floor estimate (minimum corresponds to noise-only instants).
    2. Smooths the floor estimate with exponential averaging.
    3. Applies gentle Wiener suppression: gain = clip(1 - α·floor/residual),
       only when residual energy clearly exceeds the tracked floor.
    4. Uses a high floor gain (0.40) so speech bins are never killed.

    When the gate would over-suppress (e.g. reference-based heuristic detects
    that ERLE is already high), pass the residual through unchanged — the
    caller (EdgeAIRealtimeEngine.enhance_hybrid_pipeline) handles this via
    the skip_gate ERLE heuristic.

    Parameters
    ----------
    sample_rate : int
        Audio sample rate in Hz.
    frame_size / hop_size : int
        STFT frame/hop (default 512/256 at 16 kHz).
    alpha : float
        Suppression aggressiveness (lower = more conservative). Range 0.05-0.25.
    floor_gain : float
        Minimum gain per bin (higher = less suppression). Range 0.20-0.50.
    noise_smooth : float
        EMA smoothing for the noise-floor minimum estimate.
    """

    def __init__(self, sample_rate: int = 16000, frame_size: int = 512,
                 hop_size: int = 256, alpha: float = 0.10,
                 floor_gain: float = 0.40, noise_smooth: float = 0.85):
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        self.hop_size = hop_size
        self.alpha = alpha
        self.floor_gain = floor_gain
        self.noise_smooth = noise_smooth
        self.window = np.hanning(frame_size)
        # Minimum-statistics tracking window: ~1.5 s of frames
        n_frames = int(1.5 * sample_rate / hop_size)
        self._min_track_frames = max(n_frames, 16)
        self._psd_history: list = []  # type: ignore[var-annotated]
        self._noise_floor_psd = None  # type: ignore[var-annotated]

    def process_stream(self, residual: np.ndarray, reference: np.ndarray) -> np.ndarray:
        """
        Apply spectral gate with residual-noise-floor tracking.

        Parameters
        ----------
        residual  : output from adaptive canceller (BlockWiener e(n))
        reference : noise reference signal x(n) — UNUSED for PSD estimation
                    (kept in signature for API compatibility).
                    Spectral gate now tracks the residual noise floor, not the
                    reference PSD.
        """
        del reference  # unused — residual noise floor is tracked directly
        n = len(residual)
        out = np.zeros(n, dtype=np.float32)
        frame = self.frame_size
        hop = self.hop_size
        n_fft = frame // 2 + 1
        window_sum = np.zeros(n, dtype=np.float64)

        # Per-call state (no cross-call leakage)
        noise_floor_psd: Optional[np.ndarray] = None
        psd_history: list = []  # type: ignore[var-annotated]
        min_track = self._min_track_frames

        for start in range(0, n - frame, hop):
            end = start + frame
            # Residual frame spectrum
            e_frame = residual[start:end] * self.window
            E = np.fft.rfft(e_frame)
            e_psd = (np.abs(E) ** 2).astype(np.float64)  # type: ignore[var-annotated]

            # Minimum-statistics noise-floor tracking
            psd_history.append(e_psd.copy())
            if len(psd_history) > min_track:
                psd_history.pop(0)
            if noise_floor_psd is None:
                noise_floor_psd = e_psd.copy()
            else:
                # PSD minimum over sliding window = noise floor estimate
                psd_min = np.minimum.reduce(psd_history)  # type: ignore[call-overload]
                noise_floor_psd = (  # type: ignore[operator]
                    self.noise_smooth * noise_floor_psd
                    + (1 - self.noise_smooth) * psd_min
                )

            # Only suppress when residual clearly exceeds the tracked floor.
            # During speech, e_psd >> floor → gain ≈ 1.0 (no harm to speech).
            # During noise-only lulls, e_psd ≈ floor → gentle suppression.
            if np.mean(e_psd) > np.mean(noise_floor_psd) * 1.5:
                gain = np.clip(
                    1.0 - self.alpha * noise_floor_psd / (e_psd + 1e-10),
                    self.floor_gain, 1.0,
                )
            else:
                gain = np.ones(n_fft, dtype=np.float64)
            E_out = E * gain
            out_frame = np.fft.irfft(E_out, frame)
            out[start:end] += (out_frame * self.window).astype(np.float32)
            window_sum[start:end] += self.window ** 2

        nz = window_sum > 1e-8
        out[nz] /= window_sum[nz].astype(np.float32)
        return out


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


try:
    from pystoi import stoi as pystoi_stoi
    PYSTOI_AVAILABLE = True
except ImportError:
    PYSTOI_AVAILABLE = False

try:
    from pesq import pesq as pypesq_pesq
    PESQ_AVAILABLE = True
except ImportError:
    PESQ_AVAILABLE = False


def calculate_stoi_proxy(clean_speech: np.ndarray, proc_speech: np.ndarray, fs: int = 16000) -> float:
    """
    Computes Short-Time Objective Intelligibility (STOI) score in [0.0, 1.0].
    Uses pystoi (Taal et al. 2011) when available, with proxy fallback.
    """
    n_samples = min(len(clean_speech), len(proc_speech))
    clean = np.asarray(clean_speech[:n_samples], dtype=np.float64)
    proc = np.asarray(proc_speech[:n_samples], dtype=np.float64)

    if PYSTOI_AVAILABLE:
        try:
            return float(pystoi_stoi(clean, proc, fs, extended=False))
        except Exception:
            pass

    frame_len = int(0.03 * fs)  # 30 ms frames
    hop_len = int(0.015 * fs)   # 15 ms hop
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
    Computes PESQ (Perceptual Evaluation of Speech Quality) MOS score in [1.0, 4.5].
    Uses ITU-T P.862 wideband PESQ when available, with proxy fallback.
    """
    n_samples = min(len(clean_speech), len(proc_speech))
    clean = np.asarray(clean_speech[:n_samples], dtype=np.float64)
    proc = np.asarray(proc_speech[:n_samples], dtype=np.float64)

    if PESQ_AVAILABLE:
        try:
            # PESQ requires 16000 Hz or 8000 Hz
            target_fs = 16000 if fs >= 16000 else 8000
            mode = 'wb' if target_fs == 16000 else 'nb'
            score = pypesq_pesq(target_fs, clean, proc, mode)
            return float(np.clip(score, 1.0, 4.5))
        except Exception:
            pass

    stoi = calculate_stoi_proxy(clean_speech, proc_speech, fs)
    snr = calculate_snr(clean_speech, proc_speech)
    
    # Non-linear logistic mapping from STOI and SNR to PESQ MOS scale (1.0 to 4.5)
    mos = 1.0 + 3.5 / (1.0 + np.exp(-4.0 * (stoi - 0.5) - 0.05 * snr))
    return float(np.clip(mos, 1.0, 4.5))


def calculate_acoustic_coherence(d_signal: np.ndarray, x_signal: np.ndarray, fs: int = 16000) -> Tuple[np.ndarray, np.ndarray]:
    """Magnitude-Squared Coherence gamma^2_dx(f) across frequency bands."""
    f, c_xy = signal.coherence(d_signal, x_signal, fs=fs, nperseg=256)
    return f, c_xy
