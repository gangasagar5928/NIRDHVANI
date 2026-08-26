/**
 * @file test_nlms.c
 * @brief C Unit Test for NIRDHVANI NLMS Algorithm & Impulse Limiter
 */

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <assert.h>
#include "../include/nlms_filter.h"

#define TEST_SAMPLES 1000
#define PI 3.14159265358979323846

int main() {
    printf("=====================================================\n");
    printf("  NIRDHVANI C Unit Test: NLMS Filter & Limiter        \n");
    printf("=====================================================\n");

    nlms_filter_t filter;
    nlms_config_t config = {
        .num_taps = 32,
        .mu = 0.35f,
        .epsilon = 1e-4f,
        .leakage = 0.0f,
        .limiter_thresh = 0.80f,
        .soft_clamping = true
    };

    nlms_filter_init(&filter, &config);

    // Synthetic test:
    // Speech s(n) = 0.4 * sin(2*pi*200*t)
    // Ambient noise x(n) = 0.8 * sin(2*pi*50*t) + random
    // Leaked noise into mic = 0.5 * x(n - 2)
    // Desired mic input d(n) = s(n) + 0.5 * x(n - 2)

    float initial_err_power = 0.0f;
    float final_err_power = 0.0f;

    float prev_x[4] = {0};

    for (int n = 0; n < TEST_SAMPLES; ++n) {
        float t = (float)n / 16000.0f;
        float speech = 0.4f * sinf(2.0f * PI * 200.0f * t);
        float noise = 0.8f * sinf(2.0f * PI * 50.0f * t) + ((float)rand() / RAND_MAX - 0.5f) * 0.1f;
        
        // Delay line for acoustic transfer
        float leaked = 0.5f * prev_x[2];
        prev_x[3] = prev_x[2];
        prev_x[2] = prev_x[1];
        prev_x[1] = prev_x[0];
        prev_x[0] = noise;

        float d_in = speech + leaked;
        float x_in = noise;

        // Process through filter
        float e_out = nlms_filter_process_sample(&filter, d_in, x_in);

        // Difference between filter output and true clean speech
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

    // Test Limiter on blast shock
    float shock_input = 2.5f;
    float shock_output = tacanc_impulse_limiter(shock_input, 0.80f, true);
    printf("Acoustic Blast Test : Input %.2f -> Clamped %.4f (Limit: 0.80)\n", shock_input, shock_output);

    assert(shock_output <= 1.0f);
    assert(final_err_power < initial_err_power);

    printf("\n>>> ALL C UNIT TESTS PASSED SUCCESSFULLY! <<<\n");
    return 0;
}
