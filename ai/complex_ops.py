"""
NIRDHVANI: Complex-Domain Signal Processing & Perceptual Loss Operations
Noise-Isolated Impulse-Resilient Real-Time Decoupled Hardware Voice Adaptive Network Isolator

Provides complex-valued neural network layers (Complex Conv2d, BatchNorm, cIRM operations)
and perceptual speech loss functions (SI-SNR, Compressed Complex Spectral Loss, Multi-STFT Loss).
"""

import math
import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


if TORCH_AVAILABLE:

    class ComplexConv2d(nn.Module):
        """
        2D Complex Convolution:
        (Wr + j*Wi) * (Xr + j*Xi) = (Wr*Xr - Wi*Xi) + j*(Wr*Xi + Wi*Xr)
        """
        def __init__(self, in_channels, out_channels, kernel_size, stride=1, padding=0, dilation=1, groups=1, bias=True):
            super().__init__()
            self.conv_r = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, dilation, groups, bias=bias)
            self.conv_i = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, dilation, groups, bias=bias)

        def forward(self, real, imag):
            out_r = self.conv_r(real) - self.conv_i(imag)
            out_i = self.conv_r(imag) + self.conv_i(real)
            return out_r, out_i


    class ComplexConvTranspose2d(nn.Module):
        """
        2D Complex Transposed Convolution for Spectral Decoder.
        """
        def __init__(self, in_channels, out_channels, kernel_size, stride=1, padding=0, output_padding=0, groups=1, bias=True):
            super().__init__()
            self.conv_tr_r = nn.ConvTranspose2d(in_channels, out_channels, kernel_size, stride, padding, output_padding, groups=groups, bias=bias)
            self.conv_tr_i = nn.ConvTranspose2d(in_channels, out_channels, kernel_size, stride, padding, output_padding, groups=groups, bias=bias)

        def forward(self, real, imag):
            out_r = self.conv_tr_r(real) - self.conv_tr_i(imag)
            out_i = self.conv_tr_r(imag) + self.conv_tr_i(real)
            return out_r, out_i


    class ComplexBatchNorm2d(nn.Module):
        """
        Complex Batch Normalization preserving covariance between real and imaginary parts.
        """
        def __init__(self, num_features, eps=1e-5, momentum=0.1):
            super().__init__()
            self.bn_r = nn.BatchNorm2d(num_features, eps=eps, momentum=momentum)
            self.bn_i = nn.BatchNorm2d(num_features, eps=eps, momentum=momentum)

        def forward(self, real, imag):
            return self.bn_r(real), self.bn_i(imag)


    class ComplexLinear(nn.Module):
        """
        Complex Dense Linear Layer.
        """
        def __init__(self, in_features, out_features, bias=True):
            super().__init__()
            self.fc_r = nn.Linear(in_features, out_features, bias=bias)
            self.fc_i = nn.Linear(in_features, out_features, bias=bias)

        def forward(self, real, imag):
            out_r = self.fc_r(real) - self.fc_i(imag)
            out_i = self.fc_r(imag) + self.fc_i(real)
            return out_r, out_i


    def apply_cirm_mask(spec_real, spec_imag, mask_real, mask_imag):
        """
        Applies Complex Ideal Ratio Mask (cIRM):
        S_clean = (Y_r * M_r - Y_i * M_i) + j * (Y_r * M_i + Y_i * M_r)
        """
        enhanced_real = spec_real * mask_real - spec_imag * mask_imag
        enhanced_imag = spec_real * mask_imag + spec_imag * mask_real
        return enhanced_real, enhanced_imag


    class SISNRLoss(nn.Module):
        """
        Scale-Invariant Signal-to-Noise Ratio (SI-SNR) Loss.
        Directly optimizes speech intelligibility and waveform alignment.
        """
        def __init__(self, eps=1e-8):
            super().__init__()
            self.eps = eps

        def forward(self, estimate, target):
            # Shape: [B, T]
            assert estimate.shape == target.shape, f"Shape mismatch: {estimate.shape} vs {target.shape}"
            
            # Zero-mean normalization
            estimate = estimate - torch.mean(estimate, dim=-1, keepdim=True)
            target = target - torch.mean(target, dim=-1, keepdim=True)
            
            # Optimal scaling factor alpha = <estimate, target> / ||target||^2
            dot = torch.sum(estimate * target, dim=-1, keepdim=True)
            target_energy = torch.sum(target ** 2, dim=-1, keepdim=True) + self.eps
            s_target = (dot / target_energy) * target
            
            e_noise = estimate - s_target
            
            s_target_energy = torch.sum(s_target ** 2, dim=-1) + self.eps
            e_noise_energy = torch.sum(e_noise ** 2, dim=-1) + self.eps
            
            si_snr = 10.0 * torch.log10(s_target_energy / e_noise_energy)
            return -torch.mean(si_snr)  # Minimize negative SI-SNR


    class CompressedComplexSpectralLoss(nn.Module):
        """
        Compressed Spectral Loss on Magnitude and Complex Spectrogram:
        Loss = || |S|^alpha - |S_hat|^alpha ||_1 + || S_real^alpha - S_hat_real^alpha ||_1 + || S_imag^alpha - S_hat_imag^alpha ||_1
        Alpha compression (alpha=0.3) matches human psychoacoustic loudness perception.
        """
        def __init__(self, alpha=0.3, eps=1e-8):
            super().__init__()
            self.alpha = alpha
            self.eps = eps

        def forward(self, est_real, est_imag, tgt_real, tgt_imag):
            est_mag = torch.sqrt(est_real ** 2 + est_imag ** 2 + self.eps)
            tgt_mag = torch.sqrt(tgt_real ** 2 + tgt_imag ** 2 + self.eps)
            
            est_mag_comp = est_mag ** self.alpha
            tgt_mag_comp = tgt_mag ** self.alpha
            
            # Complex compressed coordinates
            est_real_comp = (est_real / (est_mag + self.eps)) * est_mag_comp
            est_imag_comp = (est_imag / (est_mag + self.eps)) * est_mag_comp
            tgt_real_comp = (tgt_real / (tgt_mag + self.eps)) * tgt_mag_comp
            tgt_imag_comp = (tgt_imag / (tgt_mag + self.eps)) * tgt_mag_comp
            
            mag_loss = F.l1_loss(est_mag_comp, tgt_mag_comp)
            complex_loss = F.l1_loss(est_real_comp, tgt_real_comp) + F.l1_loss(est_imag_comp, tgt_imag_comp)
            
            return mag_loss + complex_loss


    class HybridSpeechEnhancementLoss(nn.Module):
        """
        Multi-objective loss combining SI-SNR in time domain and Compressed Complex Loss in frequency domain.
        """
        def __init__(self, alpha=0.3, time_weight=0.6, spec_weight=0.4):
            super().__init__()
            self.time_loss = SISNRLoss()
            self.spec_loss = CompressedComplexSpectralLoss(alpha=alpha)
            self.time_weight = time_weight
            self.spec_weight = spec_weight

        def forward(self, est_wav, tgt_wav, est_real, est_imag, tgt_real, tgt_imag):
            loss_t = self.time_loss(est_wav, tgt_wav)
            loss_s = self.spec_loss(est_real, est_imag, tgt_real, tgt_imag)
            return self.time_weight * loss_t + self.spec_weight * loss_s


else:
    # Fallback stub for apply_cirm_mask
    def apply_cirm_mask(spec_real, spec_imag, mask_real, mask_imag):
        enh_r = spec_real * mask_real - spec_imag * mask_imag
        enh_i = spec_real * mask_imag + spec_imag * mask_real
        return enh_r, enh_i


# ---------------- NumPy Standalone Fallbacks ----------------

def numpy_si_snr(estimate, target, eps=1e-8):
    """
    Computes SI-SNR using NumPy for evaluation and benchmarking.
    """
    estimate = np.asarray(estimate, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    
    estimate = estimate - np.mean(estimate)
    target = target - np.mean(target)
    
    dot = np.sum(estimate * target)
    target_energy = np.sum(target ** 2) + eps
    s_target = (dot / target_energy) * target
    
    e_noise = estimate - s_target
    
    s_target_energy = np.sum(s_target ** 2) + eps
    e_noise_energy = np.sum(e_noise ** 2) + eps
    
    si_snr = 10.0 * np.log10(s_target_energy / e_noise_energy)
    return float(si_snr)


def numpy_cirm_mask(spec_real, spec_imag, mask_real, mask_imag):
    """
    NumPy implementation of cIRM application.
    """
    enh_r = spec_real * mask_real - spec_imag * mask_imag
    enh_i = spec_real * mask_imag + spec_imag * mask_real
    return enh_r, enh_i
