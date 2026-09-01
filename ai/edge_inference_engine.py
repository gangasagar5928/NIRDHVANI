"""
NIRDHVANI: Real-Time Edge AI Streaming Inference Engine (<4.0 ms Latency)
Noise-Isolated Impulse-Resilient Real-Time Decoupled Hardware Voice Adaptive Network Isolator

Target Platforms:
- NVIDIA Jetson AGX Orin (64GB Developer Kit) / Jetson Xavier NX
- Embedded DSPs (STM32H7 / ADAU1467)
- Ultra-Low-Power Soldier-Worn MCU (ESP32-WROOM-32E)

Architecture:
- Causal 64-sample (4.0 ms) block streaming with ZERO future lookahead delay
- Multi-Stage Pipeline:
  Stage 1: Normalized Least Mean Squares (NLMS) with DTD & Leaky Drift Guard
  Stage 2: Causal Sub-Band Neural Masking Engine (Formant-Preserving)
  Stage 3: Soft-Tanh Acoustic Blast Shock Limiter (<85 dBA Protection)
"""

import os
import sys
import time
import math
import numpy as np
from scipy.io import wavfile

# Local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model_dpcrn import StandaloneNeuralEnhancer
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "simulation"))
from dsp_core import NLMSFilter, AcousticImpulseLimiter


try:
    import torch
    from model_dpcrn import DPCRNSpeechEnhancer
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class DeepNeuralEnhancerEngine:
    """
    Executes deep complex recurrent neural network (DPCRN) mask estimation on audio.
    """
    def __init__(self, checkpoint_path=None, device="cpu"):
        self.device = torch.device(device) if TORCH_AVAILABLE else None
        self.model = None
        if TORCH_AVAILABLE:
            self.model = DPCRNSpeechEnhancer().to(self.device)
            if checkpoint_path and os.path.exists(checkpoint_path):
                try:
                    ckpt = torch.load(checkpoint_path, map_location=self.device)
                    if "model_state_dict" in ckpt:
                        self.model.load_state_dict(ckpt["model_state_dict"])
                    else:
                        self.model.load_state_dict(ckpt)
                    self.model.eval()
                except Exception as e:
                    print(f"[DeepNeuralEngine] Warning loading checkpoint: {e}")

    def enhance(self, d_audio: np.ndarray, x_audio: np.ndarray) -> np.ndarray:
        """Runs complex STFT cIRM mask inference across full audio sequence."""
        if not TORCH_AVAILABLE or self.model is None:
            return d_audio
        
        n_samples = min(len(d_audio), len(x_audio))
        d_t = torch.from_numpy(d_audio[:n_samples]).unsqueeze(0).float().to(self.device)
        x_t = torch.from_numpy(x_audio[:n_samples]).unsqueeze(0).float().to(self.device)
        
        with torch.no_grad():
            enh_t, _, _ = self.model(d_t, x_t)
            
        enh = enh_t.squeeze(0).cpu().numpy()
        return enh.astype(np.float32)


class EdgeAIRealtimeEngine:
    """
    Real-time streaming inference engine executing the hybrid AI/ML + NLMS + Limiter pipeline.
    """
    def __init__(self, sample_rate=16000, frame_size=64, checkpoint_path="checkpoints/best_model.pth"):
        self.sample_rate = sample_rate
        self.frame_size = frame_size # 64 samples = 4.0 ms at 16 kHz
        
        # Stage 1: Leaky-NLMS Adaptive Filter with DTD
        self.nlms_filter = NLMSFilter(num_taps=64, mu=0.35, epsilon=1e-4, leakage=1e-5, enable_dtd=True)
        
        # Stage 2A: Causal Sub-Band Neural Enhancer (Real-time edge streaming)
        self.neural_enhancer = StandaloneNeuralEnhancer(sample_rate=sample_rate, num_bands=16, frame_size=frame_size)
        
        # Stage 2B: Deep Neural Core (DPCRN)
        self.deep_engine = DeepNeuralEnhancerEngine(checkpoint_path=checkpoint_path)
        
        # Stage 3: Hearing Protection Soft-Tanh Blast Limiter
        self.blast_limiter = AcousticImpulseLimiter(threshold=0.80, soft_knee=True)
        
        # Telemetry
        self.processed_frames = 0
        self.total_proc_time_sec = 0.0

    def process_streaming_chunk(self, d_chunk: np.ndarray, x_chunk: np.ndarray):
        """
        Processes a single causal 64-sample frame (4.0 ms) with strictly zero lookahead delay.
        """
        start_t = time.perf_counter()
        
        # Stage 1: Linear Adaptive Noise Cancellation (NLMS)
        nlms_chunk = np.zeros(self.frame_size, dtype=np.float32)
        for i in range(self.frame_size):
            e, y = self.nlms_filter.step(float(d_chunk[i]), float(x_chunk[i]))
            nlms_chunk[i] = e
            
        # Stage 2: Causal Neural Sub-Band Masking on Residual
        neural_chunk = self.neural_enhancer.enhance_frame(nlms_chunk, x_chunk)
        
        # Stage 3: Hearing Protection Blast Shock Limiting
        out_chunk = self.blast_limiter.process_stream(neural_chunk)
        
        proc_time_ms = (time.perf_counter() - start_t) * 1000.0
        self.processed_frames += 1
        self.total_proc_time_sec += (proc_time_ms / 1000.0)
        
        return out_chunk, proc_time_ms

    def enhance_hybrid_pipeline(self, d_audio: np.ndarray, x_audio: np.ndarray) -> np.ndarray:
        """
        Full 3-stage hybrid pipeline:
        Stage 1: Leaky-NLMS + DTD cancels linear acoustic coupling.
        Stage 2: Deep DPCRN cIRM Neural Core suppresses non-linear battlefield noise.
        Stage 3: Soft-Tanh Limiter protects eardrums against blast shocks.
        """
        n_samples = min(len(d_audio), len(x_audio))
        d_audio = d_audio[:n_samples]
        x_audio = x_audio[:n_samples]
        
        # Stage 1: NLMS
        nlms_out = np.zeros(n_samples, dtype=np.float32)
        self.nlms_filter.reset()
        for i in range(n_samples):
            e, _ = self.nlms_filter.step(float(d_audio[i]), float(x_audio[i]))
            nlms_out[i] = e
            
        # Stage 2: Deep DPCRN Neural Core
        if TORCH_AVAILABLE and self.deep_engine.model is not None:
            neural_out = self.deep_engine.enhance(nlms_out, x_audio)
        else:
            neural_out = nlms_out
            
        # Stage 3: Blast Limiter
        final_out = self.blast_limiter.process_stream(neural_out)
        return final_out

    def process_file_stream(self, d_wav_path, x_wav_path, out_wav_path=None):
        """
        Streams full audio files through the engine, measuring execution speed and RTF.
        """
        fs_d, d_data = wavfile.read(d_wav_path)
        fs_x, x_data = wavfile.read(x_wav_path)
        
        assert fs_d == self.sample_rate, f"Sample rate mismatch: {fs_d} vs {self.sample_rate}"
        
        d_audio = d_data.astype(np.float32) / 32767.0
        x_audio = x_data.astype(np.float32) / 32767.0
        
        T = min(len(d_audio), len(x_audio))
        num_frames = T // self.frame_size
        
        out_audio = np.zeros(T, dtype=np.float32)
        frame_latencies = []
        
        for f in range(num_frames):
            idx = f * self.frame_size
            d_chk = d_audio[idx:idx + self.frame_size]
            x_chk = x_audio[idx:idx + self.frame_size]
            
            out_chk, lat_ms = self.process_streaming_chunk(d_chk, x_chk)
            out_audio[idx:idx + self.frame_size] = out_chk
            frame_latencies.append(lat_ms)
            
        avg_lat_ms = float(np.mean(frame_latencies))
        p99_lat_ms = float(np.percentile(frame_latencies, 99))
        rtf = avg_lat_ms / 4.0 # Frame duration is 4.0 ms
        
        if out_wav_path:
            os.makedirs(os.path.dirname(out_wav_path), exist_ok=True)
            wavfile.write(out_wav_path, self.sample_rate, (np.clip(out_audio, -1.0, 1.0) * 32767).astype(np.int16))
            
        return {
            "num_frames": num_frames,
            "duration_sec": T / self.sample_rate,
            "avg_latency_ms": avg_lat_ms,
            "p99_latency_ms": p99_lat_ms,
            "real_time_factor": rtf,
            "stream_safe": rtf < 1.0,
            "output_audio": out_audio
        }


if __name__ == "__main__":
    print("\n==========================================================================")
    print("  NIRDHVANI: Real-Time Edge AI Streaming Engine Benchmark (<4.0 ms Latency)")
    print("==========================================================================\n")
    
    engine = EdgeAIRealtimeEngine()
    
    d_dummy = np.random.normal(0, 0.2, 64000).astype(np.float32)
    x_dummy = np.random.normal(0, 0.3, 64000).astype(np.float32)
    
    os.makedirs("ai/data", exist_ok=True)
    wavfile.write("ai/data/dummy_d.wav", 16000, (d_dummy * 32767).astype(np.int16))
    wavfile.write("ai/data/dummy_x.wav", 16000, (x_dummy * 32767).astype(np.int16))
    
    res = engine.process_file_stream("ai/data/dummy_d.wav", "ai/data/dummy_x.wav", "ai/data/dummy_out.wav")
    print(f"[Streaming Engine] Duration: {res['duration_sec']:.2f}s | Processed Frames: {res['num_frames']}")
    print(f"[Streaming Engine] Avg Frame Compute Time: {res['avg_latency_ms']:.3f} ms (Budget: 4.000 ms)")
    print(f"[Streaming Engine] Algorithmic Delay: Exactly 4.000 ms (Zero Lookahead)")
    print(f"[Streaming Engine] Real-Time Factor (RTF): {res['real_time_factor']:.3f}x (<1.0x = Real-Time Capable)\n")
