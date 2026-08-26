/**
 * @file test_nlms.c
 * @brief C Unit Test for NIRDHVANI NLMS Algorithm, TinyML Neural Controller, DTD & Limiter
 */

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <assert.h>
#include "../include/nlms_filter.h"
#include "../include/tinyml_anc.h"

#define TEST_SAMPLES 1500
#define PI 3.14159265358979323846

int main() {
    printf("===============================================================\n");
    printf("  NIRDHVANI C Unit Test: NLMS Filter, TinyML & Impulse Limiter  \n");
    printf("===============================================================\n");

    // 1. Test TinyML Initialization & Inference
    tinyml_state_t ml_state;
    tinyml_anc_init(&ml_state);
    
    float dummy_d[64] = {0};
    float dummy_x[64] = {0};
    for (int i = 0; i < 64; ++i) {
        dummy_x[i] = 0.5f * sinf(2.0f * PI * 50.0f * (float)i / 16000.0f);
        dummy_d[i] = 0.1f * dummy_x[i];
    }
    tinyml_inference_result_t ml_res;
    tinyml_anc_infer_block(&ml_state, dummy_d, dummy_x, 64, &ml_res);

    printf("[TinyML Engine] Inferred mu: %.4f | DTD Prob: %.4f | Class: %d\n",
           ml_res.mu_optimal, ml_res.p_dtd, ml_res.predicted_class);
    assert(ml_res.mu_optimal > 0.0f);
    assert(ml_res.p_dtd >= 0.0f && ml_res.p_dtd <= 1.0f);

    // 2. Test NLMS Convergence with DTD
    nlms_filter_t filter;
    nlms_config_t config = {
        .num_taps = 32,
        .mu = 0.35f,
        .epsilon = 1e-4f,
        .leakage = 1e-5f,
        .limiter_thresh = 0.80f,
        .dtd_threshold = 3.0f,
        .soft_clamping = true,
        .enable_dtd = true
    };
    nlms_filter_init(&filter, &config);

    float initial_err_power = 0.0f;
    float final_err_power = 0.0f;
    float prev_x[4] = {0};

    for (int n = 0; n < TEST_SAMPLES; ++n) {
        float t = (float)n / 16000.0f;
        
        // Speech active between 600..900 samples (Double-Talk burst)
        float speech = 0.0f;
        if (n >= 600 && n <= 900) {
            speech = 0.7f * sinf(2.0f * PI * 200.0f * t);
        } else if (n < 400) {
            speech = 0.2f * sinf(2.0f * PI * 200.0f * t);
        }
        
        float noise = 0.6f * sinf(2.0f * PI * 50.0f * t) + ((float)rand() / RAND_MAX - 0.5f) * 0.1f;
        
        float leaked = 0.4f * prev_x[2];
        prev_x[3] = prev_x[2];
        prev_x[2] = prev_x[1];
        prev_x[1] = prev_x[0];
        prev_x[0] = noise;

        float d_in = speech + leaked;
        float x_in = noise;

        float e_out = nlms_filter_process_sample(&filter, d_in, x_in);
        float residual_err = e_out - speech;

        if (n < 100) {
            initial_err_power += residual_err * residual_err;
        } else if (n > TEST_SAMPLES - 100) {
            final_err_power += residual_err * residual_err;
        }
    }

    initial_err_power /= 100.0f;
    final_err_power /= 100.0f;
    float attenuation_db = 10.0f * log10f(initial_err_power / (final_err_power + 1e-12f));

    printf("Initial Error Power : %.6f\n", initial_err_power);
    printf("Final Error Power   : %.6f\n", final_err_power);
    printf("NLMS Convergence    : %s (Noise Attenuation: %.2f dB)\n", 
           (final_err_power < initial_err_power) ? "PASSED" : "FAILED",
           attenuation_db);
    printf("DTD Freeze Samples  : %u samples protected\n", filter.dtd_freeze_count);

    // 3. Test Limiter on blast shock
    float shock_input = 2.5f;
    float shock_output = tacanc_impulse_limiter(shock_input, 0.80f, true);
    printf("Acoustic Blast Test : Input %.2f -> Clamped %.4f (Limit: 0.80)\n", shock_input, shock_output);

    assert(shock_output <= 1.0f);
    assert(shock_output >= -1.0f);
    assert(final_err_power < initial_err_power);
    assert(filter.dtd_freeze_count > 0);

    printf("\n>>> ALL C UNIT, TINYML & DTD TESTS PASSED SUCCESSFULLY! <<<\n");
    return 0;
}
