/**
 * @file stm32_tacanc_driver.c
 * @brief NIRDHVANI: Tactical AI/ML Adaptive Noise Cancellation
 * Noise-Isolated Impulse-Resilient Real-Time Decoupled Hardware Voice Adaptive Network Isolator
 * STM32 ARM Cortex-M Dual ADC DMA & CMSIS-DSP Acceleration Driver.
 */

#include "nlms_filter.h"
#include <stdint.h>
#include <stdbool.h>

#define STM32_BLOCK_SIZE     64
#define STM32_DMA_BUF_SIZE   (STM32_BLOCK_SIZE * 2 * 2) // 2 Channels, Half+Full Transfer

// Interleaved ADC DMA Buffer: [Ch0_0, Ch1_0, Ch0_1, Ch1_1, ...]
static uint16_t g_adc_dma_buffer[STM32_DMA_BUF_SIZE];
static nlms_filter_t g_stm32_nlms;
static float g_d_block[STM32_BLOCK_SIZE];
static float g_x_block[STM32_BLOCK_SIZE];
static float g_e_block[STM32_BLOCK_SIZE];

/**
 * @brief Initialize STM32 TacANC processing engine.
 */
void stm32_tacanc_init(void) {
    nlms_config_t config = {
        .num_taps = 64,
        .mu = 0.25f,
        .epsilon = 1e-4f,
        .leakage = 1e-5f,
        .limiter_thresh = 0.80f,
        .soft_clamping = true
    };
    nlms_filter_init(&g_stm32_nlms, &config);
}

/**
 * @brief DMA Half-Transfer or Full-Transfer Complete Interrupt Handler.
 * Called automatically by STM32 DMA IRQ.
 * @param dma_offset Pointer to current active half of DMA memory.
 */
void stm32_tacanc_process_dma_buffer(const uint16_t *dma_offset) {
    const float q12_scale = 1.0f / 2048.0f;

    // De-interleave ADC Channels
    for (uint16_t i = 0; i < STM32_BLOCK_SIZE; ++i) {
        int16_t raw_throat = (int16_t)dma_offset[2 * i] - 2048;     // Ch0: PA0
        int16_t raw_ambient = (int16_t)dma_offset[2 * i + 1] - 2048; // Ch1: PA1

        g_d_block[i] = (float)raw_throat * q12_scale;
        g_x_block[i] = (float)raw_ambient * q12_scale;
    }

    // Execute NLMS filtering + acoustic limiter
    nlms_filter_process_block(&g_stm32_nlms, g_d_block, g_x_block, g_e_block, STM32_BLOCK_SIZE);

    // Feed output to DAC / PWM DMA Stream
    for (uint16_t i = 0; i < STM32_BLOCK_SIZE; ++i) {
        // Map [-1.0, 1.0] to 12-bit DAC [0, 4095]
        float dac_f = (g_e_block[i] + 1.0f) * 2047.5f;
        if (dac_f < 0.0f) dac_f = 0.0f;
        if (dac_f > 4095.0f) dac_f = 4095.0f;
        
        // Write to DAC register (e.g. DAC->DHR12R1 = (uint16_t)dac_f)
    }
}
