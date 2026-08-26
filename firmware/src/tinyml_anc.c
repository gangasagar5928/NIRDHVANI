/**
 * @file tinyml_anc.c
 * @brief NIRDHVANI: TinyML Neural Step-Size Controller & Noise Classifier
 * Standalone embedded C inference engine implementation.
 */

#include "tinyml_anc.h"
#include <math.h>
#include <string.h>

static inline float sigmoidf_fast(float x) {
    return 1.0f / (1.0f + expf(-x));
}

void tinyml_anc_init(tinyml_state_t *state) {
    if (!state) return;
    state->prev_energy_x = 0.0f;
    state->total_inferences = 0;
    state->stationary_frames = 0;
    state->non_stationary_frames = 0;
    state->impulse_frames = 0;
}

void tinyml_anc_infer_block(
    tinyml_state_t *state,
    const float *d_block,
    const float *x_block,
    uint16_t block_size,
    tinyml_inference_result_t *result
) {
    if (!state || !d_block || !x_block || !result || block_size == 0) return;

    // 1. Feature Extraction (8 features)
    float sum_sq_d = 0.0f;
    float sum_sq_x = 0.0f;
    float max_peak_x = 0.0f;
    float zcr_sum = 0.0f;
    float hf_sum = 0.0f;

    for (uint16_t i = 0; i < block_size; ++i) {
        float d_val = d_block[i];
        float x_val = x_block[i];

        sum_sq_d += d_val * d_val;
        sum_sq_x += x_val * x_val;

        float abs_x = fabsf(x_val);
        if (abs_x > max_peak_x) max_peak_x = abs_x;

        if (i > 0) {
            // Zero crossing
            if ((x_val >= 0.0f && x_block[i - 1] < 0.0f) || (x_val < 0.0f && x_block[i - 1] >= 0.0f)) {
                zcr_sum += 1.0f;
            }
            // High frequency proxy (first difference)
            float diff = x_val - x_block[i - 1];
            hf_sum += diff * diff;
        }
    }

    const float eps = 1e-6f;
    float p_d = sum_sq_d / (float)block_size;
    float p_x = sum_sq_x / (float)block_size;

    float log_p_d = log10f(p_d + eps);
    float log_p_x = log10f(p_x + eps);
    float cross_ratio = p_d / (p_x + eps);
    float spec_flux = fabsf(p_x - state->prev_energy_x) / (p_x + state->prev_energy_x + eps);
    float zcr = zcr_sum / (float)block_size;
    float hf_ratio = (hf_sum / (float)block_size) / (p_x + eps);
    float papr = (max_peak_x * max_peak_x) / (p_x + eps);
    float blast_flag = (max_peak_x > 0.85f) ? 1.0f : 0.0f;

    state->prev_energy_x = p_x;

    // Feature vector normalization / clamping
    float features[TINYML_NUM_FEATURES];
    features[0] = log_p_d;
    features[1] = log_p_x;
    features[2] = (cross_ratio > 10.0f) ? 10.0f : cross_ratio;
    features[3] = (spec_flux > 5.0f) ? 5.0f : spec_flux;
    features[4] = zcr;
    features[5] = (hf_ratio > 5.0f) ? 5.0f : hf_ratio;
    features[6] = (papr > 20.0f) ? 20.0f : papr;
    features[7] = blast_flag;

    // 2. Layer 1 Forward Pass: Input (8) -> Hidden (16) with ReLU
    float hidden[TINYML_HIDDEN_NEURONS];
    for (int h = 0; h < TINYML_HIDDEN_NEURONS; ++h) {
        float sum = TINYML_B1[h];
        for (int in = 0; in < TINYML_NUM_FEATURES; ++in) {
            sum += features[in] * TINYML_W1[in][h];
        }
        hidden[h] = (sum > 0.0f) ? sum : 0.0f; // ReLU
    }

    // 3. Layer 2 Forward Pass: Hidden (16) -> Output (5)
    float out_raw[TINYML_OUTPUT_NEURONS];
    for (int o = 0; o < TINYML_OUTPUT_NEURONS; ++o) {
        float sum = TINYML_B2[o];
        for (int h = 0; h < TINYML_HIDDEN_NEURONS; ++h) {
            sum += hidden[h] * TINYML_W2[h][o];
        }
        out_raw[o] = sum;
    }

    // 4. Output Post-Processing
    // [0] -> Optimal step-size mu
    float mu_sig = sigmoidf_fast(out_raw[0]);
    float mu_opt = 0.02f + 0.43f * mu_sig;

    // [1] -> DTD Probability
    float p_dtd = sigmoidf_fast(out_raw[1]);

    if (p_dtd > 0.65f) {
        mu_opt = 0.005f; // Freeze weight update during double-talk
    }
    if (blast_flag > 0.5f) {
        mu_opt = 0.001f; // Instant freeze on blast
    }

    result->mu_optimal = mu_opt;
    result->p_dtd = p_dtd;
    result->blast_detected = (blast_flag > 0.5f);

    // [2,3,4] -> Softmax Classification for Noise Scene
    float max_logit = out_raw[2];
    if (out_raw[3] > max_logit) max_logit = out_raw[3];
    if (out_raw[4] > max_logit) max_logit = out_raw[4];

    float exp2 = expf(out_raw[2] - max_logit);
    float exp3 = expf(out_raw[3] - max_logit);
    float exp4 = expf(out_raw[4] - max_logit);
    float sum_exp = exp2 + exp3 + exp4;

    result->class_probabilities[0] = exp2 / sum_exp;
    result->class_probabilities[1] = exp3 / sum_exp;
    result->class_probabilities[2] = exp4 / sum_exp;

    if (result->class_probabilities[0] >= result->class_probabilities[1] &&
        result->class_probabilities[0] >= result->class_probabilities[2]) {
        result->predicted_class = NOISE_CLASS_STATIONARY_ENGINE;
        state->stationary_frames++;
    } else if (result->class_probabilities[1] >= result->class_probabilities[0] &&
               result->class_probabilities[1] >= result->class_probabilities[2]) {
        result->predicted_class = NOISE_CLASS_NON_STATIONARY_TRACK;
        state->non_stationary_frames++;
    } else {
        result->predicted_class = NOISE_CLASS_IMPULSIVE_BLAST;
        state->impulse_frames++;
    }

    state->total_inferences++;
}
