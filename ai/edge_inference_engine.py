"""
NIRDHVANI: Real-Time Edge AI Streaming Inference Engine
Noise-Isolated Impulse-Resilient Real-Time Decoupled Hardware Voice Adaptive Network Isolator

Target Platforms:
- NVIDIA Jetson AGX Orin (64GB Developer Kit) / Jetson Xavier NX
- Embedded DSPs (STM32H7 / ADAU1467)
- Edge x86 / Raspberry Pi 5 Tactical Field Units

Architecture:
- Asynchronous Circular Ring Buffer Streaming (16 kHz, 64-sample chunks, 4.0ms block latency)
- Hybrid Dual-Stage Enhancement:
  Stage 1: Deep Complex Neural Masking (DPCRN / cIRM)
  Stage 2: Residual Leaky-NLMS Adaptive Filtering with Geigel DTD
  Stage 3: Soft-Tanh Acoustic Blast Limiter
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


class EdgeAIRealtimeEngine:
    """
    Real-time streaming inference engine executing the hybrid AI/ML + NLMS + Limiter pipeline.
    """
    def __init__(self, sample_rate=16000, frame_size=64, n_fft=512):
        self.sample_rate = sample_rate
        self.frame_size = frame_size # 4.0 ms
        self.n_fft = n_fft
        
        # Stage 1: Deep Learning Complex Masking Engine
        self.neural_enhancer = StandaloneNeuralEnhancer(n_fft=n_fft, hop_length=frame_size, sample_rate=sample_rate)
        
        # Stage 2: Residual Leaky-NLMS Adaptive Filter
        self.nlms_filter = NLMSFilter(num_taps=64, mu=0.25, epsilon=1e-4, leakage=1e-5)
        
        # Stage 3: Hearing Protection Soft-Tanh Blast Limiter
        self.blast_limiter = AcousticImpulseLimiter(threshold=0.8, soft_knee=True)
        
        # Internal circular streaming buffers
        self.d_ring = np.zeros(n_fft, dtype=np.float32)
        self.x_ring = np.zeros(n_fft, dtype=np.float32)
        
        # Metrics & telemetry
        self.processed_frames = 0
        self.total_proc_time_sec = 0.0

    def process_streaming_chunk(self, d_chunk, x_chunk):
        """
        Processes a single real-time frame (64 samples / 4.0ms) through the hybrid pipeline.
        
        Args:
            d_chunk: [64] Primary speech sensor samples.
            x_chunk: [64] Reference noise sensor samples.
        Returns:
            out_chunk: [64] Enhanced, noise-cancelled, blast-limited clean audio.
            proc_time_ms: Execution time for this 4.0ms frame.
        """
        start_t = time.perf_counter()
        
        # Shift ring buffers and insert new chunk
        self.d_ring = np.roll(self.d_ring, -self.frame_size)
        self.x_ring = np.roll(self.x_ring, -self.frame_size)
        self.d_ring[-self.frame_size:] = d_chunk
        self.x_ring[-self.frame_size:] = x_chunk
        
        # Stage 1: Fast Leaky-NLMS Adaptive Filtering on Raw Audio
        nlms_chunk = np.zeros(self.frame_size, dtype=np.float32)
        for i in range(self.frame_size):
            e, y = self.nlms_filter.step(d_chunk[i], x_chunk[i])
            nlms_chunk[i] = e
            
        # Update ring buffer with NLMS residual
        self.d_ring[-self.frame_size:] = nlms_chunk
        
        # Stage 2: Deep Complex Frequency-Domain Masking on Residual
        neural_frame = self.neural_enhancer.process_frame(self.d_ring, self.x_ring)
        # Extract centered reconstruction to avoid Hanning edge taper
        mid = self.n_fft // 2
        neural_chunk = neural_frame[mid - self.frame_size // 2 : mid + self.frame_size // 2] * 2.0
        
        # Stage 3: Soft-Tanh Blast Limiting
        out_chunk = self.blast_limiter.process_stream(neural_chunk)
        
        proc_time_ms = (time.perf_counter() - start_t) * 1000.0
        self.processed_frames += 1
        self.total_proc_time_sec += (proc_time_ms / 1000.0)
        
        return out_chunk, proc_time_ms

    def process_file_stream(self, d_wav_path, x_wav_path, out_wav_path=None):
        """
        Streams full audio files through the real-time engine, measuring real-time factor (RTF).
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
            
        avg_lat_ms = np.mean(frame_latencies)
        p99_lat_ms = np.percentile(frame_latencies, 99)
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
    print("  NIRDHVANI: Real-Time Edge AI Streaming Engine Benchmark                 ")
    print("==========================================================================\n")
    
    engine = EdgeAIRealtimeEngine()
    
    # Test on generated dataset
    test_noisy = "ai/data/test/test_0000_GUNSHOT_2dB_noisy.wav"
    test_ref = "ai/data/test/test_0000_GUNSHOT_2dB_ref.wav"
    out_file = "ai/data/output_enhanced_stream.wav"
    
    if os.path.exists(test_noisy) and os.path.exists(test_ref):
        res = engine.process_file_stream(test_noisy, test_ref, out_file)
        print(f"[Streaming Engine] Duration: {res['duration_sec']:.2f}s | Processed Frames: {res['num_frames']}")
        print(f"[Streaming Engine] Avg Frame Latency: {res['avg_latency_ms']:.3f} ms (Frame Budget: 4.000 ms)")
        print(f"[Streaming Engine] 99th Percentile Latency: {res['p99_latency_ms']:.3f} ms")
        print(f"[Streaming Engine] Real-Time Factor (RTF): {res['real_time_factor']:.3f}x (<1.0x = Real-Time Capable)")
        print(f"[Streaming Engine] Output saved to: {out_file}\n")
    else:
        print("[Streaming Engine] Generating 4s synthetic test buffer...")
        d_dummy = np.random.normal(0, 0.2, 64000).astype(np.float32)
        x_dummy = np.random.normal(0, 0.3, 64000).astype(np.float32)
        wavfile.write("ai/data/dummy_d.wav", 16000, (d_dummy * 32767).astype(np.int16))
        wavfile.write("ai/data/dummy_x.wav", 16000, (x_dummy * 32767).astype(np.int16))
        res = engine.process_file_stream("ai/data/dummy_d.wav", "ai/data/dummy_x.wav", out_file)
        print(f"[Streaming Engine] Avg Frame Latency: {res['avg_latency_ms']:.3f} ms | RTF: {res['real_time_factor']:.3f}x")
