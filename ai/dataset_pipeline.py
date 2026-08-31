"""
NIRDHVANI: Scalable Defence Acoustic Dataset & Data Augmentation Pipeline
Noise-Isolated Impulse-Resilient Real-Time Decoupled Hardware Voice Adaptive Network Isolator

Generates realistic noisy-clean speech pairs covering 6 mandatory defence noise classes:
1. GUNSHOT: 12.7mm HMG / 7.62mm rifle muzzle blast impulses.
2. ARTILLERY: 155mm Dhanush / Bofors artillery blast (Friedlander shockwaves).
3. DRONE: Multi-rotor UAV propulsion & electric motor harmonics (1.2 kHz - 3.6 kHz).
4. HELICOPTER: Blade-vortex blade-slap (15 Hz - 30 Hz) + gas turbine whine.
5. ARMORED_VEHICLE: T-90 / Arjun 1000HP diesel engine + caterpillar track squeal.
6. SIREN: Emergency defense siren / tactical alarm chirps (600 Hz - 1.8 kHz).

Augmentation Pipeline:
- Variable SNR Mixing (-10 dB to +20 dB)
- Room Impulse Response (RIR) spatial acoustic reverberation
- Non-linear acoustic pre-amp clipping & saturation
- Random interference & time-frequency masking
"""

import os
import sys
import math
import json
import argparse
import numpy as np
import scipy.signal as signal
from scipy.io import wavfile


class DefenceNoiseGenerator:
    """
    Generates realistic military acoustic noise signatures across all 6 defence categories.
    """
    def __init__(self, fs=16000):
        self.fs = fs

    def generate_gunshot_noise(self, duration_sec=5.0, num_shots=8):
        """12.7mm Heavy Machine Gun / Rifle fire with rapid transient and structural decay."""
        n_samples = int(self.fs * duration_sec)
        noise = np.random.normal(0, 0.02, n_samples)
        
        # Shot trigger times
        shot_times = np.linspace(0.3, duration_sec - 0.4, num_shots)
        for t_shot in shot_times:
            idx = int(t_shot * self.fs)
            blast_len = int(0.04 * self.fs) # 40ms blast event
            if idx + blast_len < n_samples:
                t_blast = np.linspace(0, 0.04, blast_len)
                # Primary muzzle shock
                shock = 0.95 * np.exp(-t_blast / 0.003) * np.sin(2 * np.pi * 1200 * t_blast)
                # Reverberant body
                reverb = 0.4 * np.exp(-t_blast / 0.015) * np.random.normal(0, 1, blast_len)
                noise[idx:idx+blast_len] += shock + reverb
        return np.clip(noise, -1.0, 1.0)

    def generate_artillery_blast_noise(self, duration_sec=5.0, num_blasts=2):
        """155mm Heavy Artillery Blast modeled with Friedlander shockwave profile."""
        n_samples = int(self.fs * duration_sec)
        noise = np.random.normal(0, 0.03, n_samples)
        
        blast_times = [1.2, 3.4][:num_blasts]
        for t_blast in blast_times:
            idx = int(t_blast * self.fs)
            dur_blast = int(0.35 * self.fs) # 350ms shockwave + low frequency rumble
            if idx + dur_blast < n_samples:
                t = np.linspace(0, 0.35, dur_blast)
                t_pos = 0.012 # 12ms positive phase
                # Friedlander equation: P(t) = P_0 * (1 - t/t_pos) * exp(-b * t / t_pos)
                shock = np.where(t < t_pos, 1.2 * (1.0 - t / t_pos) * np.exp(-1.5 * t / t_pos),
                                 -0.35 * np.exp(-(t - t_pos) / 0.06) * np.sin(2 * np.pi * 35 * t))
                # Structural chassis vibration
                rumble = 0.25 * np.sin(2 * np.pi * 28 * t) * np.exp(-t / 0.15)
                noise[idx:idx+dur_blast] += shock + rumble
        return np.clip(noise, -1.0, 1.0)

    def generate_drone_uav_noise(self, duration_sec=5.0):
        """Multi-rotor UAV propulsion noise with high-frequency electric motor whines."""
        n_samples = int(self.fs * duration_sec)
        t = np.linspace(0, duration_sec, n_samples, endpoint=False)
        
        # Fundamental rotor blade passing frequencies (BPF) + harmonics
        f_bpf = 220.0 # 220 Hz
        drone_sound = (
            0.30 * np.sin(2 * np.pi * f_bpf * t) +
            0.25 * np.sin(2 * np.pi * 2 * f_bpf * t) +
            0.35 * np.sin(2 * np.pi * 1250 * t + 0.1 * np.sin(2 * np.pi * 5 * t)) + # 1.25 kHz motor whine
            0.20 * np.sin(2 * np.pi * 2500 * t) +
            0.15 * np.sin(2 * np.pi * 3750 * t)
        )
        # Turbulent wind & prop wash
        b, a = signal.butter(4, [300 / (self.fs / 2), 4000 / (self.fs / 2)], btype='band')
        wind = signal.lfilter(b, a, np.random.normal(0, 0.15, n_samples))
        return np.clip(drone_sound + wind, -1.0, 1.0)

    def generate_helicopter_noise(self, duration_sec=5.0):
        """Rotor blade-vortex interaction (blade-slap) + gas turbine engine."""
        n_samples = int(self.fs * duration_sec)
        t = np.linspace(0, duration_sec, n_samples, endpoint=False)
        
        # 22.5 Hz Main Rotor Blade-Slap Pulses
        f_rotor = 22.5
        rotor_slap = np.maximum(0, np.sin(2 * np.pi * f_rotor * t)) ** 6 * 0.7
        # Tail rotor 110 Hz
        tail_rotor = 0.25 * np.sin(2 * np.pi * 110 * t)
        # Gas turbine high-frequency whine (4.2 kHz)
        turbine = 0.20 * np.sin(2 * np.pi * 4200 * t)
        # Low frequency cabin body resonance
        cabin_rumble = 0.30 * np.sin(2 * np.pi * 45 * t)
        
        total = rotor_slap + tail_rotor + turbine + cabin_rumble
        return np.clip(total, -1.0, 1.0)

    def generate_armored_vehicle_noise(self, duration_sec=5.0):
        """1000 HP Diesel Tank Engine + Caterpillar Track Metallic Clatter."""
        n_samples = int(self.fs * duration_sec)
        t = np.linspace(0, duration_sec, n_samples, endpoint=False)
        
        # Diesel engine crankshaft harmonics (36.6 Hz fundamental)
        engine = (
            0.40 * np.sin(2 * np.pi * 36.6 * t) +
            0.35 * np.sin(2 * np.pi * 73.2 * t) +
            0.25 * np.sin(2 * np.pi * 109.8 * t) +
            0.20 * np.sin(2 * np.pi * 146.4 * t)
        )
        # Caterpillar track squeal (bandpass filtered non-stationary resonance)
        b, a = signal.butter(4, [1800 / (self.fs / 2), 3200 / (self.fs / 2)], btype='band')
        track_squeal = signal.lfilter(b, a, np.random.normal(0, 0.28, n_samples))
        # Periodic track pin clatter modulation (12 Hz)
        track_mod = 0.5 * (1.0 + np.sin(2 * np.pi * 12 * t))
        
        total = engine + (track_squeal * track_mod)
        return np.clip(total, -1.0, 1.0)

    def generate_emergency_siren_noise(self, duration_sec=5.0):
        """Tactical alarm / Emergency defense siren with chirped frequency modulation."""
        n_samples = int(self.fs * duration_sec)
        t = np.linspace(0, duration_sec, n_samples, endpoint=False)
        
        # FM Chirp from 650 Hz to 1750 Hz (0.5 Hz modulation cycle)
        f_mod = 0.5
        f_inst = 1200 + 550 * np.sin(2 * np.pi * f_mod * t)
        phase = 2 * np.pi * np.cumsum(f_inst) / self.fs
        siren = 0.70 * np.sin(phase) + 0.20 * np.sin(2 * phase)
        return np.clip(siren, -1.0, 1.0)

    def get_noise_by_class(self, noise_class: str, duration_sec=5.0):
        noise_class = noise_class.upper()
        if noise_class == "GUNSHOT":
            return self.generate_gunshot_noise(duration_sec)
        elif noise_class == "ARTILLERY":
            return self.generate_artillery_blast_noise(duration_sec)
        elif noise_class == "DRONE":
            return self.generate_drone_uav_noise(duration_sec)
        elif noise_class == "HELICOPTER":
            return self.generate_helicopter_noise(duration_sec)
        elif noise_class == "ARMORED_VEHICLE" or noise_class == "TANK":
            return self.generate_armored_vehicle_noise(duration_sec)
        elif noise_class == "SIREN":
            return self.generate_emergency_siren_noise(duration_sec)
        else:
            # Composite blend
            return (0.4 * self.generate_armored_vehicle_noise(duration_sec) +
                    0.3 * self.generate_drone_uav_noise(duration_sec) +
                    0.3 * self.generate_gunshot_noise(duration_sec))


class CleanSpeechGenerator:
    """
    Generates rich, multi-formant tactical human speech phonemes with natural pitch contours.
    """
    def __init__(self, fs=16000):
        self.fs = fs

    def generate_tactical_speech(self, duration_sec=5.0):
        """Synthesizes human speech utterances with natural formant resonance and breath pauses."""
        n_samples = int(self.fs * duration_sec)
        speech = np.zeros(n_samples, dtype=np.float32)
        
        # Active speech segments (word utterances)
        utterances = [(0.5, 1.6), (2.0, 3.2), (3.6, 4.7)]
        for start_t, end_t in utterances:
            if start_t >= duration_sec:
                continue
            idx_start = int(start_t * self.fs)
            idx_end = min(n_samples, int(end_t * self.fs))
            seg_len = idx_end - idx_start
            t_seg = np.linspace(0, (idx_end - idx_start) / self.fs, seg_len)
            
            # Vocal cord pitch frequency with dynamic vibrato (115 Hz - 145 Hz)
            f0 = 125.0 + 15.0 * np.sin(2 * np.pi * 3.5 * t_seg)
            phase0 = 2 * np.pi * np.cumsum(f0) / self.fs
            glottal_pulse = np.sin(phase0) + 0.5 * np.sin(2 * phase0) + 0.25 * np.sin(3 * phase0)
            
            # Vocal tract formant resonances (F1=700 Hz, F2=1220 Hz, F3=2600 Hz)
            formant1 = 0.55 * np.sin(2 * np.pi * 700 * t_seg)
            formant2 = 0.35 * np.sin(2 * np.pi * 1220 * t_seg)
            formant3 = 0.20 * np.sin(2 * np.pi * 2600 * t_seg)
            
            # Smooth attack and release envelope
            env = np.sin(np.pi * np.linspace(0, 1, seg_len)) ** 0.5
            speech[idx_start:idx_end] = (glottal_pulse * 0.4 + formant1 + formant2 + formant3) * env * 0.75
            
        return speech


class DataAugmentationEngine:
    """
    Applies spatial acoustic reverberation (RIR), non-linear clipping, and SNR scaling.
    """
    def __init__(self, fs=16000):
        self.fs = fs

    def generate_synthetic_rir(self, rt60=0.35):
        """Generates Room Impulse Response for enclosed armored vehicle cabins."""
        length = int(rt60 * self.fs)
        t = np.linspace(0, rt60, length)
        decay = np.exp(-6.91 * t / rt60)
        noise = np.random.normal(0, 1, length)
        rir = decay * noise
        rir[0] = 1.0 # Direct path
        return rir / np.max(np.abs(rir))

    def apply_reverberation(self, audio, rir=None):
        """Convolves audio with spatial impulse response."""
        if rir is None:
            rir = self.generate_synthetic_rir(rt60=0.30)
        reverbed = signal.fftconvolve(audio, rir, mode='full')[:len(audio)]
        return reverbed / (np.max(np.abs(reverbed)) + 1e-6)

    def apply_preamp_clipping(self, audio, clip_threshold=0.88):
        """Simulates analog front-end non-linear saturation."""
        return np.clip(audio, -clip_threshold, clip_threshold)

    def mix_at_snr(self, clean_speech, noise, target_snr_db):
        """Mixes clean speech and noise at exact target SNR."""
        speech_power = np.mean(clean_speech ** 2) + 1e-9
        noise_power = np.mean(noise ** 2) + 1e-9
        
        target_noise_power = speech_power / (10 ** (target_snr_db / 10.0))
        scale = np.sqrt(target_noise_power / noise_power)
        
        scaled_noise = noise * scale
        noisy_speech = clean_speech + scaled_noise
        return noisy_speech, scaled_noise


class TacticalDatasetPipeline:
    """
    Master dataset builder generating training, validation, and test sets.
    """
    def __init__(self, fs=16000, out_dir="ai/data"):
        self.fs = fs
        self.out_dir = out_dir
        self.noise_gen = DefenceNoiseGenerator(fs=fs)
        self.speech_gen = CleanSpeechGenerator(fs=fs)
        self.aug = DataAugmentationEngine(fs=fs)
        
        os.makedirs(out_dir, exist_ok=True)
        os.makedirs(os.path.join(out_dir, "clean"), exist_ok=True)
        os.makedirs(os.path.join(out_dir, "noisy"), exist_ok=True)
        os.makedirs(os.path.join(out_dir, "reference"), exist_ok=True)

    def generate_dataset_split(self, split_name="train", num_samples=50, duration_sec=4.0):
        """
        Generates noisy-clean paired dataset across random SNRs and defence noise classes.
        """
        classes = ["GUNSHOT", "ARTILLERY", "DRONE", "HELICOPTER", "ARMORED_VEHICLE", "SIREN"]
        snr_range = (-10.0, 20.0) # -10 dB to +20 dB
        metadata = []
        
        print(f"[Dataset Pipeline] Generating '{split_name}' split with {num_samples} samples...")
        
        for i in range(num_samples):
            noise_cls = classes[i % len(classes)]
            target_snr = float(np.random.uniform(snr_range[0], snr_range[1]))
            
            clean = self.speech_gen.generate_tactical_speech(duration_sec=duration_sec)
            noise_raw = self.noise_gen.get_noise_by_class(noise_cls, duration_sec=duration_sec)
            
            # Apply RIR reverberation to noise
            noise_reverb = self.aug.apply_reverberation(noise_raw)
            
            # Mix at target SNR
            noisy, scaled_noise = self.aug.mix_at_snr(clean, noise_reverb, target_snr)
            
            # Apply microphone clipping augmentation randomly
            if np.random.rand() > 0.6:
                noisy = self.aug.apply_preamp_clipping(noisy, clip_threshold=0.85)
                
            sample_id = f"{split_name}_{i:04d}_{noise_cls}_{int(target_snr)}dB"
            clean_path = os.path.join(self.out_dir, "clean", f"{sample_id}_clean.wav")
            noisy_path = os.path.join(self.out_dir, "noisy", f"{sample_id}_noisy.wav")
            ref_path = os.path.join(self.out_dir, "reference", f"{sample_id}_ref.wav")
            
            wavfile.write(clean_path, self.fs, (clean * 32767).astype(np.int16))
            wavfile.write(noisy_path, self.fs, (noisy * 32767).astype(np.int16))
            wavfile.write(ref_path, self.fs, (scaled_noise * 32767).astype(np.int16))
            
            metadata.append({
                "sample_id": sample_id,
                "noise_class": noise_cls,
                "snr_db": target_snr,
                "duration_sec": duration_sec,
                "clean_file": clean_path,
                "noisy_file": noisy_path,
                "reference_file": ref_path
            })
            
        meta_file = os.path.join(self.out_dir, f"{split_name}_metadata.json")
        with open(meta_file, "w") as f:
            json.dump(metadata, f, indent=2)
            
        print(f"[Dataset Pipeline] '{split_name}' complete. Metadata saved to: {meta_file}")
        return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NIRDHVANI Tactical Dataset Pipeline")
    parser.add_argument("--generate", action="store_true", help="Generate full dataset splits")
    parser.add_argument("--num_samples", type=int, default=60, help="Number of samples per split")
    parser.add_argument("--out_dir", type=str, default="ai/data", help="Output dataset directory")
    args = parser.parse_args()

    pipeline = TacticalDatasetPipeline(out_dir=args.out_dir)
    pipeline.generate_dataset_split(split_name="train", num_samples=args.num_samples)
    pipeline.generate_dataset_split(split_name="val", num_samples=max(12, args.num_samples // 5))
    pipeline.generate_dataset_split(split_name="test", num_samples=max(12, args.num_samples // 5))
    print("[Dataset Pipeline] All defence dataset splits successfully generated!")
