/**
 * @file nlms_filter.c
 * @brief NIRDHVANI: Tactical AI/ML Adaptive Noise Cancellation
 * Noise-Isolated Impulse-Resilient Real-Time Decoupled Hardware Voice Adaptive Network Isolator
 * Core C implementation of Normalized LMS with SIMD/FPU vectorization hooks.
 */

#include "nlms_filter.h"
#include <string.h>

void nlms_filter_init(nlms_filter_t *filter, const nlms_config_t *config) {
    if (!filter) return;

    if (config) {
        filter->config = *config;
        if (filter->config.num_taps > TACANC_MAX_TAPS) {
            filter->config.num_taps = TACANC_MAX_TAPS;
        }
        if (filter->config.num_taps == 0) {
            filter->config.num_taps = TACANC_DEFAULT_TAPS;
        }
        if (filter->config.mu <= 0.0f) {
            filter->config.mu = TACANC_DEFAULT_MU;
        }
        if (filter->config.epsilon <= 0.0f) {
            filter->config.epsilon = TACANC_DEFAULT_EPSILON;
        }
    } else {
        filter->config.num_taps = TACANC_DEFAULT_TAPS;
        filter->config.mu = TACANC_DEFAULT_MU;
        filter->config.epsilon = TACANC_DEFAULT_EPSILON;
        filter->config.leakage = TACANC_DEFAULT_LEAKAGE;
        filter->config.limiter_thresh = TACANC_LIMITER_THRESH;
        filter->config.soft_clamping = true;
    }

    nlms_filter_reset(filter);
}

void nlms_filter_reset(nlms_filter_t *filter) {
    if (!filter) return;
    memset(filter->weights, 0, sizeof(filter->weights));
    memset(filter->x_buffer, 0, sizeof(filter->x_buffer));
    filter->buffer_index = 0;
    filter->current_power = 0.0f;
    filter->samples_processed = 0;
    filter->blast_clamps_count = 0;
}

float nlms_filter_process_sample(nlms_filter_t *filter, float d_sample, float x_sample) {
    const uint16_t N = filter->config.num_taps;
    const float mu = filter->config.mu;
    const float eps = filter->config.epsilon;
    const float leakage = filter->config.leakage;

    // 1. Shift buffer (linear shift for predictable SIMD / cache locality)
    // Moving N-1 elements
    for (int i = N - 1; i > 0; --i) {
        filter->x_buffer[i] = filter->x_buffer[i - 1];
    }
    filter->x_buffer[0] = x_sample;

    // 2. Compute predicted noise: y(n) = sum_{k=0}^{N-1} w_k * x(n-k)
    // and compute energy ||x(n)||^2
    float y_hat = 0.0f;
    float power_x = 0.0f;

    for (uint16_t i = 0; i < N; ++i) {
        float x_val = filter->x_buffer[i];
        y_hat += filter->weights[i] * x_val;
        power_x += x_val * x_val;
    }

    // 3. Compute error (clean speech): e(n) = d(n) - y_hat(n)
    float e_n = d_sample - y_hat;

    // 4. Normalized step size factor: mu / (eps + ||x||^2)
    float norm_factor = mu / (eps + power_x);

    // 5. Weight update: w(n+1) = (1 - gamma*mu)*w(n) + norm_factor * e(n) * x(n)
    float leak_factor = 1.0f - (leakage * mu);
    float err_scaled = norm_factor * e_n;

    for (uint16_t i = 0; i < N; ++i) {
        filter->weights[i] = (filter->weights[i] * leak_factor) + (err_scaled * filter->x_buffer[i]);
    }

    filter->samples_processed++;

    // 6. Hearing Protection Limiter
    float clamped_out = tacanc_impulse_limiter(e_n, filter->config.limiter_thresh, filter->config.soft_clamping);
    if (fabsf(clamped_out - e_n) > 0.05f) {
        filter->blast_clamps_count++;
    }

    return clamped_out;
}

void nlms_filter_process_block(nlms_filter_t *filter,
                               const float *d_block,
                               const float *x_block,
                               float *e_out,
                               uint16_t block_size) {
    if (!filter || !d_block || !x_block || !e_out) return;

    for (uint16_t n = 0; n < block_size; ++n) {
        e_out[n] = nlms_filter_process_sample(filter, d_block[n], x_block[n]);
    }
}

void nlms_filter_process_block_q15(nlms_filter_t *filter,
                                   const int16_t *d_q15,
                                   const int16_t *x_q15,
                                   int16_t *out_q15,
                                   uint16_t block_size) {
    if (!filter || !d_q15 || !x_q15 || !out_q15) return;

    const float q15_to_float = 1.0f / 32768.0f;
    const float float_to_q15 = 32767.0f;

    for (uint16_t n = 0; n < block_size; ++n) {
        float d_f = (float)d_q15[n] * q15_to_float;
        float x_f = (float)x_q15[n] * q15_to_float;
        float e_f = nlms_filter_process_sample(filter, d_f, x_f);

        // Clamp to Q15 range
        if (e_f > 1.0f) e_f = 1.0f;
        if (e_f < -1.0f) e_f = -1.0f;
        out_q15[n] = (int16_t)(e_f * float_to_q15);
    }
}
