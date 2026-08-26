# NIRDHVANI: Tactical AI/ML Adaptive Noise Cancellation Comms
> **N**oise-**I**solated **I**mpulse-**R**esilient Real-Time **D**ecoupled **H**ardware **V**oice **A**daptive **N**etwork **I**solator  
> *(Sanskrit for "Silence / Noise-Free" — Defence Signal Processing)*  
> **Tagline:** *"Decoupled Throat-Acoustic Adaptive Noise Cancellation for Extreme Battlefield Environments"*

**Sponsoring Organization:** Defence Research and Development Organisation (DRDO)  
**Category / Theme:** Hardware | Defence Signal Processing & Tactical Communications

---

## 1. Executive Summary & Mission Objective
Standard acoustic communication devices in extreme combat environments (120 dB to 140 dB SPL inside main battle tanks, infantry combat vehicles, artillery emplacements) suffer from immediate acoustic clipping, structural reverberation, and severe speech intelligibility degradation. Software-only airborne noise suppression introduces unacceptable latency (>30ms) and destroys vital human speech formant structures ($F_1, F_2$).

**NIRDHVANI** implements **Acoustic Transducer Decoupling**:
1. **Primary Sensor (Speech):** Dual-piezoelectric contact transducer coupled directly to user's thyroid cartilage / vocal tract. Immune to high-SPL airborne acoustic waves.
2. **Signal Conditioning:** Active ultra-high impedance ($>10\text{ M}\Omega$) Rail-to-Rail MCP6001 / TS321 op-amp voltage follower stage to prevent low-frequency capacitive loading and preserve low-frequency speech fundamentals ($100\text{ Hz} - 300\text{ Hz}$) without clipping on a 3.3V rail.
3. **Reference Sensor (Ambient Noise):** High-AOP airborne microphone (MAX4466 electret / Knowles MEMS) sampling background engine, track vibration, and gunfire noise.
4. **Embedded DSP Engine:** Real-time Normalized Least Mean Squares (NLMS) adaptive filter running on isolated MCU Core (ESP32 / STM32F401), computing $e(n) = d(n) - \mathbf{w}^T(n)\mathbf{x}(n)$ with normalized weight updates.
5. **Impulse Clamping:** Hearing protection limiter stage clamping acoustic spikes ($>85\text{ dBA}$ equivalent) from artillery and firearm blasts.
6. **Output Driver:** Low-latency differential output to tactical bone-conduction / hear-through headsets via PAM8403 amplifier.

---

## 2. System Architecture & Component Mapping

<p align="center">
  <img src="assets/nirdhvani_exploded_hardware_architecture.jpg" alt="NIRDHVANI Exploded Mil-Spec Hardware Architecture" width="850">
</p>

| Module | Hackathon Prototype Part (Student Budget) | Production Component (Industrial Scale) | Function / Purpose |
| :--- | :--- | :--- | :--- |
| **Compute Core** | ESP32-WROOM-32 / STM32F401 Black Pill | STM32H723 ARM Cortex-M7 @ 550MHz / ADAU1467 DSP | Dual-channel synchronous ADC sampling, Core 1 isolated NLMS DSP |
| **Speech Sensor** | DIY 27mm Piezoelectric Disc + Elastic Neckband | Tactical Dual-Piezo Throat Microphone Assembly | Contact-based vocal cord vibration sensing (airborne immune) |
| **Impedance Buffer** | MCP6001 / TS321 Rail-to-Rail Buffer (or LM358) | OPA2353 High-Impedance Precision Buffer | Prevents low-frequency speech attenuation; true 0-3.3V swing |
| **Noise Reference Sensor**| MAX4466 Electret Microphone Module | Knowles / Analog Devices ICS-40730 MEMS (>130 dB AOP) | Ambient gunfire, tank engine, and impulse noise sampling |
| **Audio Output Stage** | 8-bit DAC + PAM8403 Mini 3W Amp + 3.5mm Jack | TI TLV320AIC3254 24-bit Codec + Tactical Headset | Differential audio amplification for hear-through headsets |
| **Power Subsystem** | 3.7V 18650 Li-ion Cell + TP4056 + AMS1117-3.3 | MIL-STD-810G Regulated Li-ion Pack + TVS Diodes | Low-ripple power delivery for high-gain analog audio front-end |

---

## 3. Functional Requirements (FR)

### FR-1: Decoupled Acquisition & Analog Conditioning
- **Channel 0 (Speech / Desired signal $d(n)$):** Sample piezo contact transducer buffered through MCP6001 / TS321 non-inverting voltage follower with $10\text{ M}\Omega$ input resistance, $0.1\mu\text{F}$ AC coupling, and $1.65\text{ V}$ virtual ground bias.
- **Channel 1 (Noise Reference $x(n)$):** Sample electret microphone with adjustable pre-amp gain.
- **Sampling Parameters:** Synchronous dual ADC sampling at $f_s = 16\text{ kHz}$ with eFuse piecewise calibration, processed in 64-sample ping-pong blocks ($4.0\text{ ms}$ algorithmic latency).

### FR-2: NLMS Adaptive Noise Cancellation Core
- **Filter Model:** 64-tap adaptive FIR filter with regularized normalized step size:
  $$\mathbf{w}(n+1) = (1 - \gamma \mu)\mathbf{w}(n) + \frac{\mu}{\epsilon + \|\mathbf{x}(n)\|^2} e(n) \mathbf{x}(n)$$
- **Target Performance:** $> 20\text{ dB}$ noise attenuation under simulated 120 dB SPL armored vehicle acoustic field.

### FR-3: Acoustic Impulse Limiter (Blast Protection)
- Detect sample amplitude $|e(n)| > V_{\text{th}}$ ($85\text{ dBA}$ SPL equivalent).
- Apply soft sigmoid tanh saturation clamping:
  $$e_{\text{clamped}}(n) = \text{sgn}(e(n)) \cdot \left[ V_{\text{th}} + (1 - V_{\text{th}}) \tanh\left(\frac{|e(n)| - V_{\text{th}}}{1 - V_{\text{th}}}\right) \right]$$

### FR-4: Audio Driver Output
- Convert filtered output $e_{\text{clamped}}(n)$ via 8-bit DAC (`GPIO25`) or 24-bit I2S interface to PAM8403 Class-D amplifier.

---

## 4. Engineering Vulnerability Mitigations & Hardware Caveats

> [!IMPORTANT]
> **Simulation vs. Hardware Verification Caveat:**  
> The **27.75 dB ERLE** figure represents an ideal floating-point simulation benchmark. Under real-world hardware non-linearities (ESP32 SAR ADC DNL noise + 8-bit internal DAC reconstruction), the modeled ERLE is **~21.5 dB to 23.8 dB**. Physical anechoic/acoustic chamber testing on hardware prototype is actively in progress.

1. **ESP32 ADC Linearity:** ESP32 ADC DNL non-linearity is mitigated via `esp_adc_cal` factory eFuse characterization and biasing signals within the linear $0.5\text{ V} - 2.8\text{ V}$ window.
2. **Op-Amp Rail-to-Rail Swing:** Replaced legacy LM358 with **MCP6001 / TS321** to prevent top-clipping at 3.3V supply rails.
3. **Core Isolation:** Pinned real-time DSP task to **Core 1** with priority `configMAX_PRIORITIES - 1` to eliminate FreeRTOS scheduler timing jitter.
4. **Resolution Honesty:** Explicitly distinguishes between 12-bit calibrated ADC input, 8-bit prototype DAC output, and 24-bit production I2S audio codecs.
5. **EMI & Shielding:** Implements star grounding, TVS ESD protection, ferrite beads, and shielded twisted-pair cabling for tactical vehicle environments.
