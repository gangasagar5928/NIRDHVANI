# NIRDHVANI Hardware Schematics & Engineering Guide
> **N**oise-**I**solated **I**mpulse-**R**esilient Real-Time **D**ecoupled **H**ardware **V**oice **A**daptive **N**etwork **I**solator  
> *(Sanskrit for "Silence / Noise-Free" — Defence Signal Processing)*  
> **Tagline:** *"Decoupled Throat-Acoustic Adaptive Noise Cancellation for Extreme Battlefield Environments"*

## 1. Electrical & Physical Architecture Overview

<p align="center">
  <img src="../docs/assets/nirdhvani_3d_prototype_view.jpg" alt="NIRDHVANI 3D Real-Time Onboard Prototype View" width="850">
</p>

<p align="center">
  <img src="../docs/assets/nirdhvani_exploded_hardware_architecture.jpg" alt="NIRDHVANI Exploded Mil-Spec Hardware Layer Architecture" width="850">
</p>

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
|   MCP6001 / TS321 High-Z AFE Stage   |   |   Ambient Mic Gain & Anti-Aliasing     |
| - Rail-to-Rail I/O Voltage Follower  |   | - MAX4466 Built-in Low-Noise Pre-amp   |
| - Rin = 10 Megohm Bias Network       |   | - 20Hz - 20kHz Bandwidth               |
| - 0.1uF Input DC Decoupling          |   | - DC Offset Bias ~ VCC/2 (1.65V)       |
| - VCC/2 Virtual Ground Reference     |   |                                        |
+----------------------+---------------+   +--------------------+-------------------+
                       |                                        |
                       v (ADC Ch0 / GPIO34)                     v (ADC Ch1 / GPIO35)
+-----------------------------------------------------------------------------------+
|                        ESP32 / STM32F401 SIGNAL PROCESSOR                         |
|                                                                                   |
|  - Dual Synchronous 12-bit ADC (Calibrated via eFuse / Linearized LUT)            |
|  - Real-time Normalized LMS (NLMS) Engine + Double-Talk Detector (Core 1 Pinned)  |
|  - Soft Tanh Impulse Blast Limiter (>85 dBA Suppression)                          |
|  - Output: 8-bit DAC (GPIO25) with RC Reconstruction Filter / 24-bit I2S          |
+--------------------------------------+--------------------------------------------+
                                       |
                   [ RC Low-Pass Filter: 100Ω + 10nF (fc = 160kHz) ]
                                       |
                                       v
+-----------------------------------------------------------------------------------+
|                            AUDIO POWER OUTPUT STAGE                               |
|                                                                                   |
|  [ PAM8403 Class-D Stereo Amp ] ---> [ 3.5mm Female Jack ] ---> [ Tactical Earset]|
+-----------------------------------------------------------------------------------+
```

---

## 2. Analog Front-End (AFE): Rail-to-Rail High-Z Piezo Buffer

A piezoelectric contact disc exhibits high source impedance ($R_s > 1\text{ M}\Omega$) and capacitive behavior ($C_s \approx 20\text{ nF}$). Direct connection to an unbuffered MCU ADC ($R_{in} \approx 10\text{ k}\Omega - 50\text{ k}\Omega$) forms a high-pass filter with a high cutoff frequency ($f_c = \frac{1}{2\pi R C} \approx 160\text{ Hz} - 800\text{ Hz}$), severely attenuating speech fundamental frequencies ($F_0 \approx 85\text{ Hz} - 255\text{ Hz}$).

### Op-Amp Selection: Rail-to-Rail MCP6001 / TS321 (Primary Design)
- **Primary Design:** **MCP6001 / TS321 / OPA2353** True **Rail-to-Rail Input/Output (RRIO)** with output saturation within $25\text{ mV}$ of both supply rails ($0.025\text{ V} - 3.275\text{ V}$), providing a clean $\pm 1.6\text{ V}$ dynamic linear range without clipping.
- **Historical Reference:** Legacy LM358 op-amp from early v1.0 prototype is obsoleted due to non-rail-to-rail upper swing ($V_{sat} \approx 2.1\text{ V}$ on 3.3V).

### MCP6001 Rail-to-Rail Voltage Follower & BAT54S Transient Clamping Schematic

```
                                          +3.3V_ANA
                                              |
                                            [▲] D1 (BAT54S Schottky)
                                              |
   PIEZO (+) ---[ C_IN: 0.1uF ]---[ R_PROT: 1kΩ ]---+------------+
   (Throat Disc)                                    |            |
                                                  [▼] D2       [ R_IN: 10M ]
                                                    |            |
                                                   GND         V_BIAS (1.65V)
                                                                 |
                                                                 v
                                                            |\
                                                            | \  MCP6001 / TS321 (RRIO)
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

#### Hardware Overvoltage Protection Operation:
- **Mechanical Blast Shocks:** Extreme acoustic shockwaves (>140 dB) or physical impacts on the piezo disc produce high peak voltages ($>15\text{ V}$).
- **Dual Clamping Diodes:** D1 and D2 (BAT54S low-forward-drop Schottky) clamp raw transient voltages to $-0.3\text{ V} \le V_{\text{in}} \le +3.6\text{ V}$.
- **Current Limiting:** $R_{\text{PROT}} = 1\text{ k}\Omega$ restricts peak diode current to $< 10\text{ mA}$, protecting the op-amp input stage and ADC pins before software limiting executes.

---

## 3. Class-D PAM8403 Switching Noise Decoupling & Reconstruction

To prevent PAM8403 250 kHz PWM switching ripple from coupling into the sensitive high-Z analog front-end:

```
+3.3V (Digital Rail) -----[ Ferrite Bead 100Ω @ 100MHz ]-----+---- +3.3V_ANA (Op-Amp & ADC)
                                                             |
                                                       [ 10uF Tantalum ]
                                                             |
                                                       [ 0.1uF Ceramic ]
                                                             |
                                                            AGND

ESP32 DAC (GPIO25) -----[ R_REC: 100Ω ]-----+-----[ C_DC: 1uF ]-----> PAM8403 L_IN
                                            |
                                      [ C_REC: 10nF ] (fc = 159 kHz DAC reconstruction)
                                            |
                                           AGND
```

---

## 4. Double-Talk Detection (DTD) & Adaptive Energy Scaling

```
   Throat Mic Power  P_d(n) = 0.95*P_d(n-1) + 0.05*d^2(n)
   Ambient Mic Power P_x(n) = 0.95*P_x(n-1) + 0.05*x^2(n)

   Ratio = P_d(n) / (P_x(n) + 1e-5)
   IF (Ratio > 3.0 AND P_d(n) > 0.01) OR (|e(n)| > 0.85):
       -> Freeze Filter Weight Updates: w(n+1) = w(n)
       -> Maintain Subtraction: e(n) = d(n) - y(n)
       -> Trigger Status Indicator LED
```
- **Voice Preservation:** Eliminates voice distortion and filter divergence when the operator speaks loudly during quiet battlefield moments.
- **Bone-Conducted Shock Immunity:** Freezes weights if $|e(n)| > 0.85$, stopping blast shock energy from corrupting the FIR tap weights.

---

## 5. Throat Contact Microphone Calibration & Mechanical Fitting

```
[ Step 1: Neckband Placement ] ---> [ Step 2: Contact Pressure Check ] ---> [ Step 3: Gain Staging ]
```

1. **Anatomical Placement:**
   - Position the 27mm brass contact element on the lateral side of the thyroid cartilage (larynx / Adam's apple), ~1.5 cm from the midline.
   - Dual-sensor configuration places one element on each lateral wing for balanced differential pickup.
2. **Contact Pressure Tuning:**
   - The elastic collar must apply consistent mechanical pressure ($1.5 - 2.5\text{ N/cm}^2$).
   - Silicone dampening pads isolate the back of the piezo disc from neckband strap friction.
3. **Gain Staging & Null Calibration:**
   - With user silent, verify ADC Ch0 sits at $1.65\text{ V} \pm 50\text{ mV}$ ($2048 \pm 60$ raw ADC counts).
   - Adjust ambient MAX4466 potentiometer so ambient noise RMS matches leaked throat noise RMS during silence.

---

## 6. EMI / RFI Shielding & Targeted MIL-STD-810G Environmental Methods

```
   [ Aluminum Shielded Chassis / Enclosure ] ================== CHASSIS GND (Shield)
       |
     [ 1nF 1kV High-Voltage Cap || 1MΩ Resistor ]
       |
   [ Star Circuit Ground (AGND / DGND) ] ---------------------- SIGNAL GND
       |
     +---+---+--------------------+
     |       |                    |
   [TVS]   [Ferrite Bead]     [Shielded Twisted Pair]
   Diodes  (100Ω @ 100MHz)    (Throat Sensor Cable)
```

### Targeted Environmental Test Methods (Design Guidelines):
- **MIL-STD-810G Method 514.6 (Vibration):** Category 20 (Ground Combat Vehicles — Tracked & Wheeled armor vibration spectrum $10\text{ Hz} - 500\text{ Hz}$).
- **MIL-STD-810G Method 516.6 (Mechanical Shock):** Functional shock $40\text{ g}$, $11\text{ ms}$ half-sine pulse for vehicle weapon recoil.
- **MIL-STD-810G Method 501.5 / 502.5 (High & Low Temperature):** Operating range $-20^\circ\text{C to }+60^\circ\text{C}$; Storage $-40^\circ\text{C to }+85^\circ\text{C}$.
- **MIL-STD-810G Method 506.5 (Rain & Ingress):** IP54/IP67 sealed enclosure with silicone gaskets.
*(Note: Full certified compliance requires accredited third-party test chamber qualification in production phase).*

---

## 7. Microcontroller Pin Mapping Table

| Subsystem | Signal Function | ESP32-WROOM-32 Pin | STM32F401 Black Pill Pin |
| :--- | :--- | :--- | :--- |
| **Throat Sensor (Ch0)** | Primary Speech Input $d(n)$ | GPIO34 (ADC1_CH6) | PA0 (ADC1_IN0) |
| **Ambient Mic (Ch1)** | Reference Noise $x(n)$ | GPIO35 (ADC1_CH7) | PA1 (ADC1_IN1) |
| **Audio Output** | Processed Clean Speech $e(n)$| GPIO25 (8-bit DAC) / I2S | PA4 (DAC_OUT1) / I2S |
| **Status LED 1** | Processing Active / ANC ON | GPIO2 (On-board LED)| PC13 (On-board LED) |
| **Status LED 2** | DTD / Limiter Active | GPIO4 | PB0 |
| **Control Switch** | ANC Bypass Toggle | GPIO18 (Pull-up) | PB12 (Pull-up) |
| **Analog Rail (VCC)**| Clean Filtered 3.3V | 3V3 Pin | 3V3 Pin |
| **Analog Ground** | AGND | GND Pin | GND Pin |

---

## 8. Hardware Diagram Mapping & Engineering Evolution (L1 to L6)

The attached 3D view and exploded architecture diagrams illustrate the 6-layer physical stack. The table below details the original design vs. the audit-hardened engineering enhancements:

| Layer # | Diagram Label | Initial Conceptual Diagram | Audit-Hardened Engineering Implementation | Why the Change Was Made |
| :---: | :--- | :--- | :--- | :--- |
| **L6** | **Tactical Headset & Transducer** | Single Piezo Neckband + 3.5mm Jack | Dual-Piezo Differential Contact Assembly with silicone damping pads | Eliminates mechanical neck rotation artifacts and cable strain. |
| **L5** | **High-Impedance Analog Front-End** | LM358 Op-Amp ($R_{in} = 10\text{ M}\Omega$) | **MCP6001 / TS321 / OPA2353** True Rail-to-Rail I/O Buffer | LM358 clips at $\sim 2.1\text{ V}$ on $3.3\text{ V}$ rail. MCP6001 provides full $0.025\text{ V} - 3.275\text{ V}$ dynamic range without clipping. |
| **L4** | **Ambient Reference Layer** | MAX4466 / ICS-40730 MEMS Mic | MAX4466 with balanced acoustic overload mesh & gain-trim calibration | Matches ambient noise RMS with throat leakage floor during silence. |
| **L3** | **DSP & Neural Computing Layer** | ESP32 / STM32F4 Dual-ADC ($\mu=0.3, \epsilon=10^{-4}$) | **NLMS + Double-Talk Detector (DTD) + `esp_adc_cal` eFuse Linearization + Core 1 Isolation** | Protects vocal integrity from weight divergence during loud speech; eliminates FreeRTOS interrupt jitter. |
| **L2** | **Power & Amplifier Layer** | PAM8403 3W + 18650 Li-ion + TP4056 | PAM8403 + **$100\Omega @ 100\text{ MHz}$ Ferrite Bead LC Filter + $159\text{ kHz}$ RC Reconstruction Filter** | Decouples 250 kHz Class-D PWM switching ripple from analog input; suppresses DAC quantization step noise. |
| **L1** | **Rugged Enclosure Layer** | MIL-STD-810G Aluminum / Polycarbonate | Aluminum Faraday chassis with Chassis-to-Signal star grounding & TVS ESD diodes | Protects against combat vehicle alternator ripple, high-power VHF/UHF radio RF, and static discharges. |

