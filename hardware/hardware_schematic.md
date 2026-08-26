# NIRDHVANI Hardware Schematics & Engineering Guide
> **N**oise-**I**solated **I**mpulse-**R**esilient Real-Time **D**ecoupled **H**ardware **V**oice **A**daptive **N**etwork **I**solator  
> *(Sanskrit for "Silence / Noise-Free" — Defence Signal Processing)*  
> **Tagline:** *"Decoupled Throat-Acoustic Adaptive Noise Cancellation for Extreme Battlefield Environments"*

## 1. Electrical Architecture Overview

```
+-----------------------------------------------------------------------------------+
|                              TACTICAL HEADSET / NECKBAND                          |
|                                                                                   |
|  [ Dual-Piezo Contact Sensor ]               [ MAX4466 Electret Mic ]             |
|       (Throat Vocalization)                     (Ambient Airborne Noise)          |
+----------------------+------------------------------------+-----------------------+
                       |                                    |
                       v                                    v
+--------------------------------------+   +----------------------------------------+
|   LM358 High-Z Analog Front-End      |   |   Ambient Mic Gain & Anti-Aliasing     |
| - Voltage Follower (Gain = 1.0)      |   | - MAX4466 Built-in Low-Noise Pre-amp   |
| - Rin = 10 Megohm Bias Network       |   | - 20Hz - 20kHz Bandwidth               |
| - 0.1uF Input DC Decoupling          |   | - DC Offset Bias ~ VCC/2 (1.65V)       |
| - VCC/2 Virtual Ground Reference     |   |                                        |
+----------------------+---------------+   +--------------------+-------------------+
                       |                                        |
                       v (ADC Ch0 / GPIO34)                     v (ADC Ch1 / GPIO35)
+-----------------------------------------------------------------------------------+
|                        ESP32 / STM32F401 SIGNAL PROCESSOR                         |
|                                                                                   |
|  - Dual Synchronous 12-bit ADC @ 16 kHz (DMA Double-Buffered)                     |
|  - Real-time Normalized LMS (NLMS) Adaptive Filter Core (64 Taps)                 |
|  - Soft Tanh Impulse Blast Limiter (>85 dBA Suppression)                          |
|  - Output: 8-bit DAC (GPIO25) / I2S Audio Bus                                     |
+--------------------------------------+--------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------+
|                            AUDIO POWER OUTPUT STAGE                               |
|                                                                                   |
|  [ PAM8403 Class-D Stereo Amp ] ---> [ 3.5mm Female Jack ] ---> [ Tactical Earset]|
+-----------------------------------------------------------------------------------+
```

---

## 2. Analog Front-End (AFE): LM358 High-Z Piezo Buffer

A piezoelectric contact disc exhibits high source impedance ($R_s > 1\text{ M}\Omega$) and capacitive behavior ($C_s \approx 20\text{ nF}$). Direct connection to MCU ADC ($R_{in} \approx 10\text{ k}\Omega - 50\text{ k}\Omega$) forms a high-pass filter with a high cutoff frequency ($f_c = \frac{1}{2\pi R C} \approx 160\text{ Hz} - 800\text{ Hz}$), severely attenuating speech fundamental frequencies ($F_0 \approx 85\text{ Hz} - 255\text{ Hz}$).

### LM358 Non-Inverting Voltage Follower Circuit Schematic

```
               +3.3V (VCC_ANA)
                 |
               [ R1: 100k ]
                 |-----+-------- V_BIAS (1.65V Virtual Ground)
                 |     |
               [ R2: 100k ]  [ C_BIAS: 10uF Electrolytic ]
                 |     |
                GND   GND
                       |
   PIEZO (+) ----------+---[ C_IN: 0.1uF ]----+
   (Throat Disc)                              |
                                            [ R_IN: 10M ]
   PIEZO (-) ----------- GND                  |
                                            V_BIAS (1.65V)
                                              |
                                              v
                                         |\
                                         | \
                            Non-Inv (+)  |  \
                     ------------------->|   \
                                         |    \________ Pin 1 (V_OUT) ------> ESP32 GPIO34
                                    +--->|    /             |                 (ADC1_CH6)
                                    |    |   /              |
                                    |    |  /               |
                                    |    | /                |
                                    |    |/                 |
                                    +-----------------------+  (Unity Gain Feedback)
                                         |
                                        GND
```

### Component Values & Justification
- **`R_IN` (10 MΩ):** Sets input impedance high enough so that $f_c = \frac{1}{2\pi \cdot 10\text{M}\Omega \cdot 20\text{nF}} \approx 0.8\text{ Hz}$, ensuring complete low-frequency speech retention.
- **`C_IN` (0.1 µF Ceramic):** Blocks DC bias voltage from reaching the piezo element.
- **`R1, R2` (100 kΩ matched) + `C_BIAS` (10 µF):** Generates an ultra-clean virtual ground at $V_{CC}/2 = 1.65\text{ V}$ to place the bidirectional AC voice swing in the linear operating range of the 12-bit ADC ($0\text{ V} - 3.3\text{ V}$).

---

## 3. Reference Noise Sensor (MAX4466) & Pinout

```
+---------------+
| MAX4466 Board |
|               |
| VCC ---------> +3.3V (Clean Analog Rail)
| GND ---------> AGND
| OUT ---------> ESP32 GPIO35 (ADC1_CH7) / STM32 PA1
+---------------+
```
- Gain Trimmer set to mid-point (~25x - 40x gain) for linear response up to $110\text{ dB}$ airborne noise.
- Direct analog coupling with internal $1.65\text{ V}$ self-bias.

---

## 4. Audio Amplifier Stage (PAM8403) & Connections

```
ESP32 DAC (GPIO25) -----[ C_DC: 1uF ]-----+---- PAM8403 L_IN
                                          |
                                       [ 10k Potentiometer (Volume) ]
                                          |
                                         GND

PAM8403 Power:
- VDD -> +5V (or 3.7V Li-ion direct rail)
- GND -> Power GND
- L_OUT (+) / (-) -> 3.5mm Audio Jack (Tip & Sleeve)
```

---

## 5. Microcontroller Pin Mapping Table

| Subsystem | Signal Function | ESP32-WROOM-32 Pin | STM32F401 Black Pill Pin |
| :--- | :--- | :--- | :--- |
| **Throat Sensor (Ch0)** | Primary Speech Input $d(n)$ | GPIO34 (ADC1_CH6) | PA0 (ADC1_IN0) |
| **Ambient Mic (Ch1)** | Reference Noise $x(n)$ | GPIO35 (ADC1_CH7) | PA1 (ADC1_IN1) |
| **Audio DAC Output** | Processed Clean Speech $e(n)$| GPIO25 (DAC_1) | PA4 (DAC_OUT1 / I2S WS) |
| **Status LED 1** | Processing Active / ANC ON | GPIO2 (On-board LED)| PC13 (On-board LED) |
| **Status LED 2** | Impulse Limiter Triggered | GPIO4 | PB0 |
| **Control Switch** | ANC Bypass Toggle | GPIO18 (Pull-up) | PB12 (Pull-up) |
| **Analog Rail (VCC)**| Clean Analog 3.3V | 3V3 Pin | 3V3 Pin |
| **Analog Ground** | AGND | GND Pin | GND Pin |
