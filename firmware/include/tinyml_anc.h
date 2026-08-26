/**
 * @file tinyml_anc.h
 * @brief NIRDHVANI: TinyML Neural Step-Size Controller & Noise Classifier
 * Portable, standalone embedded C inference engine for tactical audio.
 */

#ifndef NIRDHVANI_TINYML_ANC_H
#define NIRDHVANI_TINYML_ANC_H

#include <stdint.h>
#include <stdbool.h>
#include "tinyml_weights.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    NOISE_CLASS_STATIONARY_ENGINE = 0,
    NOISE_CLASS_NON_STATIONARY_TRACK = 1,
    NOISE_CLASS_IMPULSIVE_BLAST = 2
} noise_scene_class_t;

typedef struct {
    float mu_optimal;                   /**< Dynamically inferred step-size */
    float p_dtd;                        /**< Double-talk probability [0.0, 1.0] */
    noise_scene_class_t predicted_class;/**< Active noise classification */
    float class_probabilities[3];       /**< Softmax probabilities */
    bool blast_detected;                /**< Instantaneous blast trigger */
} tinyml_inference_result_t;

typedef struct {
    float prev_energy_x;                /**< Previous frame energy for spectral flux */
    uint32_t total_inferences;          /**< Diagnostics counter */
    uint32_t stationary_frames;         /**< Frame count per class */
    uint32_t non_stationary_frames;
    uint32_t impulse_frames;
} tinyml_state_t;

/**
 * @brief Initialize TinyML inference engine.
 */
void tinyml_anc_init(tinyml_state_t *state);

/**
 * @brief Extract 8-dim feature vector and run forward inference on 64-sample block.
 * @param state Pointer to TinyML state.
 * @param d_block Throat sensor block.
 * @param x_block Ambient reference block.
 * @param block_size Number of samples (e.g. 64).
 * @param result Pointer to inference result output.
 */
void tinyml_anc_infer_block(
    tinyml_state_t *state,
    const float *d_block,
    const float *x_block,
    uint16_t block_size,
    tinyml_inference_result_t *result
);

#ifdef __cplusplus
}
#endif

#endif // NIRDHVANI_TINYML_ANC_H
