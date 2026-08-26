# NIRDHVANI: Tactical AI/ML Adaptive Noise Cancellation Comms
> **N**oise-**I**solated **I**mpulse-**R**esilient Real-Time **D**ecoupled **H**ardware **V**oice **A**daptive **N**etwork **I**solator  
> *(Sanskrit for "Silence / Noise-Free" — Defence Signal Processing)*  
> **Tagline:** *"Decoupled Throat-Acoustic Adaptive Noise Cancellation for Extreme Battlefield Environments"*

**Sponsoring Organization:** Defence Research and Development Organisation (DRDO)  
**Theme:** Hardware | Defence Signal Processing & Tactical Communications

---

## 🎯 1. Project Overview & Problem Statement
In extreme military acoustic environments (120 dB to 140 dB SPL inside main battle tanks like Arjun/T-90, BMP-II ICVs, artillery positions, and low-altitude rotary-wing aircraft), conventional airborne microphones suffer from immediate acoustic overload, clipping speech signals into unintelligible distortion. Software-only frequency filters introduce phase delays (>30ms) and eliminate natural vocal formants.

**NIRDHVANI** provides a hardware-software co-designed tactical communication system based on **Acoustic Transducer Decoupling**:
- **Throat Contact Sensing:** A 27mm piezoelectric contact transducer samples vocal cord tissue vibrations directly from the user's thyroid cartilage, bypassing airborne acoustic waves.
- **High-Impedance Active Buffering:** An active LM358 op-amp stage ($R_{in} = 10\text{ M}\Omega$) prevents capacitive attenuation of fundamental speech frequencies ($100\text{ Hz} - 300\text{ Hz}$).
- **Ambient Noise Reference:** A high-AOP external electret/MEMS microphone samples ambient cockpit and gunfire noise.
- **Real-Time Embedded NLMS Core:** An adaptive FIR filter running on MCU (ESP32/STM32) continuously estimates and subtracts leaked noise from the throat channel in $<4\text{ ms}$.
- **Acoustic Impulse Protection:** A soft-knee tanh peak limiter clamps muzzle blasts and explosive shockwaves to protect soldier hearing.

---

## 📐 2. Mathematical Formulation

### Normalized Least Mean Squares (NLMS) Adaptive Algorithm
Let:
- $d(n)$: Desired signal captured by throat contact sensor ($s(n) + \text{leakage}$).
- $x(n)$: Reference noise captured by ambient microphone.
- $\mathbf{w}(n) = [w_0(n), w_1(n), \dots, w_{N-1}(n)]^T$: Adaptive weight vector ($N$ taps).
- $\mathbf{x}(n) = [x(n), x(n-1), \dots, x(n-N+1)]^T$: Delay line buffer.

#### Step 1: Predicted Noise Estimation
$$y(n) = \mathbf{w}^T(n) \mathbf{x}(n) = \sum_{k=0}^{N-1} w_k(n) x(n-k)$$

#### Step 2: Clean Speech Error Extraction
$$e(n) = d(n) - y(n)$$

#### Step 3: Weight Vector Update with Regularization
$$\mathbf{w}(n+1) = (1 - \gamma \mu) \mathbf{w}(n) + \frac{\mu}{\epsilon + \|\mathbf{x}(n)\|^2} e(n) \mathbf{x}(n)$$
where:
- $\mu$: Step-size learning rate ($\mu = 0.25 - 0.35$).
- $\epsilon$: Regularizer to prevent division by zero during silence ($\epsilon = 10^{-4}$).
- $\gamma$: Leakage factor preventing tap weight drift ($\gamma = 10^{-5}$).
- $\|\mathbf{x}(n)\|^2 = \sum_{k=0}^{N-1} x^2(n-k)$: Ambient signal power.

#### Step 4: Blast Impulse Protection Limiter
$$e_{\text{out}}(n) = \begin{cases} 
V_{\text{th}} + (1 - V_{\text{th}}) \tanh\left(\frac{e(n) - V_{\text{th}}}{1 - V_{\text{th}}}\right), & e(n) > V_{\text{th}} \\
-V_{\text{th}} - (1 - V_{\text{th}}) \tanh\left(\frac{-e(n) - V_{\text{th}}}{1 - V_{\text{th}}}\right), & e(n) < -V_{\text{th}} \\
e(n), & |e(n)| \le V_{\text{th}}
\end{cases}$$

---

## 🛠️ 3. System Architecture & Pin Connections

```
[ Piezo Throat Sensor ]  ---> [ LM358 High-Z Buffer ]  ---> ESP32 GPIO34 (ADC1_CH6)
[ MAX4466 Ambient Mic ]  ---> [ Gain / Bias Stage   ]  ---> ESP32 GPIO35 (ADC1_CH7)

                    +-------------------------+
                    |  ESP32 240MHz Dual-Core |
                    |  Core 1: 16kHz NLMS Task|
                    |  DMA Ping-Pong Buffers  |
                    +------------+------------+
                                 |
                          ESP32 GPIO25 (DAC_1)
                                 |
                                 v
                     [ PAM8403 Audio Amplifier ]
                                 |
                                 v
                    [ 3.5mm Headphone Jack ]
```

### Pin Mapping Table

| ESP32 Pin | Function | Description |
| :--- | :--- | :--- |
| **GPIO34 (ADC1_CH6)** | Throat Mic Input | LM358 buffered vocal cord signal ($d(n)$) |
| **GPIO35 (ADC1_CH7)** | Ambient Mic Input | MAX4466 ambient cockpit reference ($x(n)$) |
| **GPIO25 (DAC1)** | Audio Output | Processed clean speech to PAM8403 ($e(n)$) |
| **GPIO2** | ANC Active LED | Status indicator |
| **GPIO4** | Blast Limiter LED | Flashes when artillery shockwave is clamped |
| **GPIO18** | Bypass Switch | Toggles between raw throat and filtered ANC |

---

## 💻 4. Repository Structure

```
d:/AI ANC/
├── docs/
│   └── PRD.md                       # Official DRDO PRD Document
├── hardware/
│   ├── hardware_schematic.md        # LM358 circuit, MAX4466 & PAM8403 wiring
│   └── bom.md                       # Hackathon vs Military Grade BOM breakdown
├── simulation/
│   ├── dsp_core.py                  # Core NLMS filter & impulse limiter classes
│   ├── simulate_tactical_anc.py     # 120dB cockpit simulation, plots, and WAV audio
│   ├── requirements.txt             # Python dependencies
│   └── output/                      # Generated WAV samples & benchmark plots
│       ├── 1_clean_throat_speech.wav
│       ├── 2_ambient_cockpit_noise.wav
│       ├── 3_raw_throat_mixed_input.wav
│       ├── 4_processed_anc_output.wav
│       ├── tacanc_waveform_analysis.png
│       └── benchmark_report.txt
└── firmware/
    ├── include/
    │   └── nlms_filter.h            # ANSI C NLMS & limiter header
    ├── src/
    │   └── nlms_filter.c            # ANSI C NLMS signal processing engine
    ├── esp32/
    │   ├── main_esp32.cpp           # Production ESP32 firmware with FreeRTOS & Timer ISR
    │   └── platformio.ini           # PlatformIO project config
    ├── stm32/
    │   └── stm32_tacanc_driver.c    # STM32 CMSIS-DSP DMA double buffer driver
    └── tests/
        ├── test_nlms.c              # C unit test suite
        └── verify_c_dsp.py          # Python C-logic validation runner
```

---

## 🚀 5. Quickstart & Verification

### Running the Python Acoustic Simulation & Benchmark Suite
```bash
# 1. Install dependencies
pip install -r simulation/requirements.txt

# 2. Run simulation
python simulation/simulate_tactical_anc.py
```

### Running C Unit Test Verification
```bash
python firmware/tests/verify_c_dsp.py
```

---

## 📊 6. Performance Benchmarks

- **Sampling Rate:** $16.0\text{ kHz}$ / 12-bit synchronous dual ADC
- **Processing Latency:** $< 4.0\text{ ms}$ (64-sample ping-pong block)
- **Noise Attenuation (ERLE):** $+27.75\text{ dB}$ reduction on ambient tank engine noise
- **Artillery Blast Clamping:** $< 1.0\text{ ms}$ response time with soft-tanh distortion suppression
- **Prototype Hardware BOM Cost:** ₹765 INR (~$9.20 USD)
- **Target Industrial Mass Production:** ~₹380 INR (~$4.60 USD)
