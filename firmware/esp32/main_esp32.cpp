/**
 * @file main_esp32.cpp
 * @brief NIRDHVANI: Tactical AI/ML Adaptive Noise Cancellation
 * Noise-Isolated Impulse-Resilient Real-Time Decoupled Hardware Voice Adaptive Network Isolator
 * ESP32 Production Firmware: Dual ADC Sampling + Real-Time NLMS Engine + DAC Driver
 * 
 * Hardware Pin Mapping:
 * - Piezo Throat Mic (LM358 High-Z Out): GPIO34 (ADC1_CH6)
 * - Ambient Reference Mic (MAX4466 Out) : GPIO35 (ADC1_CH7)
 * - Audio Headphone Driver (PAM8403 In) : GPIO25 (DAC_1)
 * - Status LED (ANC Active)             : GPIO2  (On-board)
 * - Blast Indicator LED                 : GPIO4
 * - ANC Bypass Switch                   : GPIO18 (Internal Pullup)
 */

#include <Arduino.h>
#include <driver/adc.h>
#include <driver/dac.h>
#include <soc/sens_reg.h>
#include <soc/soc.h>
#include "nlms_filter.h"

// ------------------- Configuration Constants -------------------
#define SAMPLE_RATE_HZ       16000
#define BLOCK_SIZE           64       // 4ms latency per block
#define PIN_THROAT_ADC       ADC1_CHANNEL_6 // GPIO34
#define PIN_AMBIENT_ADC      ADC1_CHANNEL_7 // GPIO35
#define PIN_DAC_OUT          DAC_CHANNEL_1  // GPIO25
#define PIN_LED_ANC          2
#define PIN_LED_BLAST        4
#define PIN_BYPASS_SW        18

#define ADC_MAX_VAL          4095.0f
#define V_REF_MV             3300.0f
#define DC_OFFSET_NORM       0.50f    // Virtual ground at VCC/2 (1.65V)

// ------------------- Global DSP Objects -------------------
static nlms_filter_t g_nlms_filter;
static volatile bool g_anc_enabled = true;
static volatile uint32_t g_isr_counter = 0;

// Ping-pong double buffers for streaming
typedef struct {
    int16_t throat[BLOCK_SIZE];
    int16_t ambient[BLOCK_SIZE];
} audio_buffer_t;

static audio_buffer_t g_buffers[2];
static volatile uint8_t g_active_buf_idx = 0;
static volatile bool g_buffer_ready = false;

// FreeRTOS Task Handle for Signal Processing Task
static TaskHandle_t g_dsp_task_handle = NULL;
static hw_timer_t *g_sample_timer = NULL;

// ------------------- Timer Interrupt (16 kHz Sample ISR) -------------------
void IRAM_ATTR onSampleTimerISR() {
    static uint16_t sample_idx = 0;
    
    // Read raw 12-bit ADC values synchronously
    int raw_throat = adc1_get_raw(PIN_THROAT_ADC);
    int raw_ambient = adc1_get_raw(PIN_AMBIENT_ADC);

    // Store in active input buffer
    uint8_t buf = g_active_buf_idx;
    g_buffers[buf].throat[sample_idx] = (int16_t)(raw_throat - 2048);   // Remove DC offset
    g_buffers[buf].ambient[sample_idx] = (int16_t)(raw_ambient - 2048);

    sample_idx++;
    if (sample_idx >= BLOCK_SIZE) {
        sample_idx = 0;
        g_active_buf_idx ^= 1; // Swap ping-pong buffer
        g_buffer_ready = true;

        // Wake up DSP task immediately
        BaseType_t xHigherPriorityTaskWoken = pdFALSE;
        vTaskNotifyGiveFromISR(g_dsp_task_handle, &xHigherPriorityTaskWoken);
        if (xHigherPriorityTaskWoken) {
            portYIELD_FROM_ISR();
        }
    }
    g_isr_counter++;
}

// ------------------- Real-Time DSP Task (Core 1) -------------------
void dsp_processing_task(void *pvParameters) {
    float d_block[BLOCK_SIZE];
    float x_block[BLOCK_SIZE];
    float e_block[BLOCK_SIZE];

    const float q_scale = 1.0f / 2048.0f; // Scale 12-bit ADC offset to [-1.0, 1.0]

    while (true) {
        // Block until timer ISR signals a full block is captured
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

        // Process inactive buffer
        uint8_t proc_buf_idx = g_active_buf_idx ^ 1;
        const int16_t *throat_raw = g_buffers[proc_buf_idx].throat;
        const int16_t *ambient_raw = g_buffers[proc_buf_idx].ambient;

        // Convert to normalized floating-point [-1.0, +1.0]
        for (int i = 0; i < BLOCK_SIZE; ++i) {
            d_block[i] = (float)throat_raw[i] * q_scale;
            x_block[i] = (float)ambient_raw[i] * q_scale;
        }

        if (g_anc_enabled) {
            // Execute NLMS Filter & Acoustic Impulse Limiter
            nlms_filter_process_block(&g_nlms_filter, d_block, x_block, e_block, BLOCK_SIZE);
        } else {
            // Bypass mode: pass raw throat signal directly
            memcpy(e_block, d_block, sizeof(d_block));
        }

        // Stream clean audio output to ESP32 DAC
        for (int i = 0; i < BLOCK_SIZE; ++i) {
            // Map [-1.0, 1.0] float back to 8-bit DAC [0, 255]
            float dac_val_f = (e_block[i] + 1.0f) * 127.5f;
            if (dac_val_f < 0.0f) dac_val_f = 0.0f;
            if (dac_val_f > 255.0f) dac_val_f = 255.0f;
            
            uint8_t dac_val = (uint8_t)dac_val_f;
            dac_output_voltage(PIN_DAC_OUT, dac_val);
        }

        // Blast Limiter status indicator
        if (g_nlms_filter.blast_clamps_count > 0) {
            digitalWrite(PIN_LED_BLAST, HIGH);
        } else {
            digitalWrite(PIN_LED_BLAST, LOW);
        }
    }
}

// ------------------- System Setup & Diagnostics -------------------
void setup() {
    Serial.begin(115200);
    delay(500);

    Serial.println("\n========================================================");
    Serial.println("  NIRDHVANI: Tactical AI/ML Adaptive Noise Cancellation ");
    Serial.println("  ESP32 Embedded DSP Engine Initializing...             ");
    Serial.println("========================================================");

    // 1. Configure GPIO LEDs and Switches
    pinMode(PIN_LED_ANC, OUTPUT);
    pinMode(PIN_LED_BLAST, OUTPUT);
    pinMode(PIN_BYPASS_SW, INPUT_PULLUP);
    digitalWrite(PIN_LED_ANC, HIGH);
    digitalWrite(PIN_LED_BLAST, LOW);

    // 2. Configure ADC1 (12-bit, 0dB/11dB attenuation for full 0-3.3V rail)
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(PIN_THROAT_ADC, ADC_ATTEN_DB_11);
    adc1_config_channel_atten(PIN_AMBIENT_ADC, ADC_ATTEN_DB_11);

    // 3. Configure DAC Output
    dac_output_enable(PIN_DAC_OUT);

    // 4. Initialize NLMS Filter
    nlms_config_t config;
    config.num_taps = 64;
    config.mu = 0.25f;
    config.epsilon = 1e-4f;
    config.leakage = 1e-5f;
    config.limiter_thresh = 0.75f;
    config.soft_clamping = true;
    nlms_filter_init(&g_nlms_filter, &config);

    Serial.printf("[DSP] NLMS Filter Initialized (Taps: %d, Mu: %.2f, Latency: %.2f ms)\n",
                  config.num_taps, config.mu, (float)BLOCK_SIZE * 1000.0f / SAMPLE_RATE_HZ);

    // 5. Create Real-Time Processing Task on Core 1
    xTaskCreatePinnedToCore(
        dsp_processing_task,
        "TacANC_DSP",
        4096,
        NULL,
        configMAX_PRIORITIES - 1, // Highest priority
        &g_dsp_task_handle,
        1                          // Pin to Core 1
    );

    // 6. Setup 16 kHz Hardware Timer
    // Timer 0, prescaler 80 (80MHz / 80 = 1MHz tick), count up
    g_sample_timer = timerBegin(0, 80, true);
    timerAttachInterrupt(g_sample_timer, &onSampleTimerISR, true);
    // Alarm every (1,000,000 / 16000) = 62.5 ticks => 62 ticks
    timerAlarmWrite(g_sample_timer, 1000000 / SAMPLE_RATE_HZ, true);
    timerAlarmEnable(g_sample_timer);

    Serial.println("[System] 16 kHz Synchronous Dual Sampling Active. Running.");
}

void loop() {
    // Background supervisory loop: read bypass switch, print metrics
    static uint32_t last_report = 0;
    
    // Read bypass button
    bool sw_state = (digitalRead(PIN_BYPASS_SW) == LOW);
    if (sw_state != g_anc_enabled) {
        g_anc_enabled = sw_state;
        digitalWrite(PIN_LED_ANC, g_anc_enabled ? HIGH : LOW);
        Serial.printf("[ANC State] Mode: %s\n", g_anc_enabled ? "ENABLED (Filtering)" : "BYPASS (Raw Throat)");
    }

    if (millis() - last_report >= 3000) {
        last_report = millis();
        Serial.printf("[Diagnostics] Processed Samples: %u | Blast Clamps: %u | ISR Count: %u\n",
                      g_nlms_filter.samples_processed,
                      g_nlms_filter.blast_clamps_count,
                      g_isr_counter);
        // Reset blast clamp count for next interval window
        g_nlms_filter.blast_clamps_count = 0;
    }

    vTaskDelay(pdMS_TO_TICKS(100));
}
