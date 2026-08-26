"""
Verification of C-equivalent NLMS filter & impulse limiter logic for NIRDHVANI.
"""
import math
import numpy as np

def run_test():
    print("=====================================================")
    print("  NIRDHVANI C DSP Logic Verification                 ")
    print("=====================================================")
    
    num_taps = 32
    mu = 0.35
    eps = 1e-4
    limiter_thresh = 0.80

    weights = np.zeros(num_taps)
    x_buf = np.zeros(num_taps)
    
    test_samples = 1000
    prev_x = [0.0] * 4

    err_powers_init = []
    err_powers_final = []

    for n in range(test_samples):
        t = n / 16000.0
        speech = 0.4 * math.sin(2.0 * math.pi * 200.0 * t)
        noise = 0.8 * math.sin(2.0 * math.pi * 50.0 * t) + (np.random.rand() - 0.5) * 0.1
        
        leaked = 0.5 * prev_x[2]
        prev_x[3] = prev_x[2]
        prev_x[2] = prev_x[1]
        prev_x[1] = prev_x[0]
        prev_x[0] = noise

        d_in = speech + leaked
        x_in = noise

        # C-logic step
        x_buf[1:] = x_buf[:-1]
        x_buf[0] = x_in

        y_hat = np.dot(weights, x_buf)
        power_x = np.dot(x_buf, x_buf)
        e_n = d_in - y_hat
        norm_factor = mu / (eps + power_x)
        weights += norm_factor * e_n * x_buf

        # Soft limiter
        if e_n > limiter_thresh:
            excess = e_n - limiter_thresh
            headroom = (1.0 - limiter_thresh) if limiter_thresh < 1.0 else 0.0
            e_out = min(1.0, limiter_thresh + headroom * math.tanh(excess / (headroom + 1e-6)))
        elif e_n < -limiter_thresh:
            excess = -e_n - limiter_thresh
            headroom = (1.0 - limiter_thresh) if limiter_thresh < 1.0 else 0.0
            e_out = max(-1.0, -(limiter_thresh + headroom * math.tanh(excess / (headroom + 1e-6))))
        else:
            e_out = e_n

        res_err = e_out - speech
        if n < 100:
            err_powers_init.append(res_err ** 2)
        elif n > test_samples - 100:
            err_powers_final.append(res_err ** 2)

    init_p = np.mean(err_powers_init)
    fin_p = np.mean(err_powers_final)
    atten = 10.0 * math.log10(init_p / (fin_p + 1e-12))

    print(f"Initial Error Power : {init_p:.6f}")
    print(f"Final Error Power   : {fin_p:.6f}")
    print(f"Noise Attenuation   : {atten:.2f} dB")
    assert fin_p < init_p, "Filter failed to reduce noise"
    print(">>> C LOGIC VERIFIED AND PASSED <<<")

if __name__ == "__main__":
    run_test()
