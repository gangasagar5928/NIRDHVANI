/**
 * @file nlms_filter.h
 * @brief NIRDHVANI: Tactical AI/ML Adaptive Noise Cancellation
 * Noise-Isolated Impulse-Resilient Real-Time Decoupled Hardware Voice Adaptive Network Isolator
 * High-performance, low-latency C implementation of Normalized LMS (NLMS)
 * with Acoustic Blast Limiter for ESP32 and STM32 Cortex-M.
 */

#ifndef NIRDHVANI_NLMS_FILTER_H
#define NIRDHVANI_NLMS_FILTER_H

#include <stdint.h>
#include <stdbool.h>
#include <math.h>

#ifdef __cplusplus
extern "C" {
#endif

#define TACANC_MAX_TAPS        128
#define TACANC_DEFAULT_TAPS    64
#define TACANC_DEFAULT_MU      0.25f
#define TACANC_DEFAULT_EPSILON 1e-4f
#define TACANC_DEFAULT_LEAKAGE 1e-5f
#define TACANC_LIMITER_THRESH  0.80f

/**
 * @brief Configuration parameters for NLMS Adaptive Filter
 */
typedef struct {
    uint16_t num_taps;     /**< Filter length (e.g. 32, 64, 128) */
    float mu;              /**< Normalized step-size (0.01 to 0.5) */
    float epsilon;         /**< Regularizer to avoid div-by-zero */
    float leakage;         /**< Leakage coefficient (prevents weight drift) */
    float limiter_thresh;  /**< Acoustic impulse clamp threshold (0.1 to 1.0) */
    bool soft_clamping;    /**< True: smooth tanh, False: hard clip */
} nlms_config_t;

/**
 * @brief State structure for NLMS Adaptive Filter
 */
typedef struct {
    nlms_config_t config;
    float weights[TACANC_MAX_TAPS];     /**< Filter tap weights w(n) */
    float x_buffer[TACANC_MAX_TAPS];    /**< Circular/Linear delay line x(n) */
    uint16_t buffer_index;              /**< Current circular index */
    float current_power;                /**< Running signal energy ||x(n)||^2 */
    uint32_t samples_processed;         /**< Diagnostics counter */
    uint32_t blast_clamps_count;        /**< Acoustic spikes clamped */
} nlms_filter_t;

/**
 * @brief Initialize NLMS filter with specified configuration.
 * @param filter Pointer to filter state structure.
 * @param config Pointer to configuration parameters (NULL for defaults).
 */
void nlms_filter_init(nlms_filter_t *filter, const nlms_config_t *config);

/**
 * @brief Reset weights and internal history buffer to zero.
 * @param filter Pointer to filter state structure.
 */
void nlms_filter_reset(nlms_filter_t *filter);

/**
 * @brief Process a single sample pair in real time.
 * @param filter Pointer to filter state structure.
 * @param d_sample Desired signal sample from throat mic (speech + leakage).
 * @param x_sample Reference noise sample from ambient mic.
 * @return Filtered, clean speech sample e(n).
 */
float nlms_filter_process_sample(nlms_filter_t *filter, float d_sample, float x_sample);

/**
 * @brief Block-based processing for DMA / ping-pong buffers.
 * @param filter Pointer to filter state structure.
 * @param d_block Input block of throat mic samples.
 * @param x_block Input block of ambient mic samples.
 * @param e_out Output block for filtered clean speech.
 * @param block_size Number of samples in block.
 */
void nlms_filter_process_block(nlms_filter_t *filter,
                               const float *d_block,
                               const float *x_block,
                               float *e_out,
                               uint16_t block_size);

/**
 * @brief Fixed-point 16-bit block processing helper for low-power MCUs.
 * @param filter Pointer to filter state structure.
 * @param d_q15 Input throat samples in Q15 format [-32768, 32767].
 * @param x_q15 Input ambient samples in Q15 format [-32768, 32767].
 * @param out_q15 Output clean samples in Q15 format.
 * @param block_size Number of samples.
 */
void nlms_filter_process_block_q15(nlms_filter_t *filter,
                                   const int16_t *d_q15,
                                   const int16_t *x_q15,
                                   int16_t *out_q15,
                                   uint16_t block_size);

/**
 * @brief Acoustic impulse limiter (hearing protection).
 * @param sample Raw output sample.
 * @param threshold Clamping threshold [0.0, 1.0].
 * @param soft_knee If true, applies smooth tanh compression.
 * @return Clamped safe sample.
 */
static inline float tacanc_impulse_limiter(float sample, float threshold, bool soft_knee) {
    if (!soft_knee) {
        if (sample > threshold) return threshold;
        if (sample < -threshold) return -threshold;
        return sample;
    }

    if (sample > threshold) {
        float excess = sample - threshold;
        float headroom = 1.0f - threshold + 1e-6f;
        return threshold + headroom * tanhf(excess / headroom);
    } else if (sample < -threshold) {
        float excess = -sample - threshold;
        float headroom = 1.0f - threshold + 1e-6f;
        return -(threshold + headroom * tanhf(excess / headroom));
    }
    return sample;
}

#ifdef __cplusplus
}
#endif

#endif // TACANC_NLMS_FILTER_H
