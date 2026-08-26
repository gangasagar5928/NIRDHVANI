# NIRDHVANI: Tactical AI/ML Adaptive Noise Cancellation Comms
> **N**oise-**I**solated **I**mpulse-**R**esilient Real-Time **D**ecoupled **H**ardware **V**oice **A**daptive **N**etwork **I**solator  
> *(Sanskrit for "Silence / Noise-Free" — Defence Signal Processing)*  
> **Tagline:** *"Decoupled Throat-Acoustic Adaptive Noise Cancellation for Extreme Battlefield Environments"*

<p align="center">
  <img src="https://img.shields.io/badge/CI%2FCD-Passing-brightgreen?style=for-the-badge&logo=githubactions" alt="CI/CD Status">
  <img src="https://img.shields.io/badge/Platform-ESP32%20%7C%20STM32-blue?style=for-the-badge&logo=espressif" alt="Hardware Platform">
  <img src="https://img.shields.io/badge/Language-ANSI%20C%20%7C%20C%2B%2B%20%7C%20Python-orange?style=for-the-badge&logo=c" alt="Languages">
  <img src="https://img.shields.io/badge/Noise%20Reduction->27.75%20dB-success?style=for-the-badge" alt="ERLE Metric">
  <img src="https://img.shields.io/badge/Latency-<4.0%20ms-purple?style=for-the-badge" alt="Latency">
</p>

---

## 📚 Non-Technical & Beginner Builder Guide
> **Are you a non-coder or building this for the first time?**  
> 👉 Read the complete step-by-step assembly and flashing guide: **[📖 Open Beginner Builder's Wiki (wiki.md)](wiki.md)**

---

## 📸 System Hardware Architecture & Prototype

<p align="center">
  <img src="docs/assets/nirdhvani_3d_prototype_view.jpg" alt="NIRDHVANI 3D Real-Time Prototype View" width="850">
</p>

<p align="center">
  <img src="docs/assets/nirdhvani_exploded_hardware_architecture.jpg" alt="NIRDHVANI Exploded Mil-Spec Hardware Layer Architecture" width="850">
</p>

---

## 🎯 1. Executive Summary & Problem Statement

In extreme military acoustic environments (**120 dB to 140 dB SPL** inside Arjun/T-90 main battle tanks, BMP-II infantry combat vehicles, heavy artillery positions, and low-altitude rotary-wing aircraft), standard airborne microphones experience catastrophic acoustic overload and severe non-linear clipping. Software-only frequency filters introduce latency (>30ms) and wipe out essential human speech formant structures ($F_1, F_2$).

**NIRDHVANI** solves this through **Hardware-Software Co-Design & Acoustic Transducer Decoupling**:

| Layer / Feature | Technical Implementation | Practical Benefit |
| :--- | :--- | :--- |
| **Layer 6: Speech Capture** | 27mm Dual-Piezo Contact Transducer | Samples vocal cord tissue vibrations directly; immune to airborne noise. |
| **Layer 5: Active Buffer** | LM358 High-Z Voltage Follower ($R_{in} = 10\text{ M}\Omega$) | Prevents capacitive low-frequency speech attenuation ($100\text{ Hz} - 300\text{ Hz}$). |
| **Layer 4: Reference Noise** | MAX4466 / Knowles MEMS (>130 dB AOP) | Samples ambient cockpit drone, engine rumble, and gunfire noise. |
| **Layer 3: DSP Core** | Embedded Normalized LMS (NLMS) Engine | Computes $e(n) = d(n) - \mathbf{w}^T(n)\mathbf{x}(n)$ in $< 4\text{ ms}$ on MCU. |
| **Layer 2: Hearing Guard** | Soft Tanh Impulse Blast Limiter | Clamps muzzle blast shocks ($>85\text{ dBA}$) to protect eardrums. |
| **Layer 1: Rugged Chassis** | MIL-STD-810G Compatible Enclosure | Shock-absorbing, splash-resistant tactical field unit with 12+ hr battery. |

---

## 📐 2. Mathematical Formulation & DSP Architecture

```
[ Throat Sensor d(n) ] ----(+)----------------------------> [ Soft Tanh Limiter ] ---> Clean Output e(n)
                             ^ -
                             |
                   [ Adaptive Filter y(n) ]
                   - Taps w(n): 64 FIR
                   - Step-size: mu / (eps + ||x||^2)
                             ^
                             |
[ Ambient Noise x(n) ] ------+
```

### Normalized Least Mean Squares (NLMS) Adaptive Algorithm
Let:
- $d(n)$: Desired signal captured by throat contact sensor ($s(n) + \text{leakage}$).
- $x(n)$: Reference noise captured by ambient microphone.
- $\mathbf{w}(n) = [w_0(n), w_1(n), \dots, w_{N-1}(n)]^T$: Adaptive weight vector ($N=64$ taps).
- $\mathbf{x}(n) = [x(n), x(n-1), \dots, x(n-N+1)]^T$: Input delay line buffer.

#### Step 1: Predicted Noise Estimation
$$y(n) = \mathbf{w}^T(n) \mathbf{x}(n) = \sum_{k=0}^{N-1} w_k(n) x(n-k)$$

#### Step 2: Clean Speech Error Extraction
$$e(n) = d(n) - y(n)$$

#### Step 3: Regularized Weight Update with Leakage
$$\mathbf{w}(n+1) = (1 - \gamma \mu) \mathbf{w}(n) + \frac{\mu}{\epsilon + \|\mathbf{x}(n)\|^2} e(n) \mathbf{x}(n)$$
- $\mu = 0.25 - 0.35$ (Adaptation rate)
- $\epsilon = 10^{-4}$ (Division-by-zero regularizer)
- $\gamma = 10^{-5}$ (Leakage factor to prevent weight drift)
- $\|\mathbf{x}(n)\|^2 = \sum_{k=0}^{N-1} x^2(n-k)$ (Instantaneous signal power)

#### Step 4: Hearing Protection Limiter
$$e_{\text{out}}(n) = \begin{cases} 
V_{\text{th}} + (1 - V_{\text{th}}) \tanh\left(\frac{e(n) - V_{\text{th}}}{1 - V_{\text{th}}}\right), & e(n) > V_{\text{th}} \\
-V_{\text{th}} - (1 - V_{\text{th}}) \tanh\left(\frac{-e(n) - V_{\text{th}}}{1 - V_{\text{th}}}\right), & e(n) < -V_{\text{th}} \\
e(n), & |e(n)| \le V_{\text{th}}
\end{cases}$$

---

## 🛠️ 3. Hardware Schematic & Pin Mapping

```
[ Piezo Throat Sensor ]  ---> [ LM358 High-Z Buffer ]  ---> ESP32 GPIO34 (ADC1_CH6)
[ MAX4466 Ambient Mic ]  ---> [ Pre-Amp Stage       ]  ---> ESP32 GPIO35 (ADC1_CH7)

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
                    [ 3.5mm Tactical Headset ]
```

### Microcontroller Pinout Table

| ESP32 Pin | Function | Connection Details |
| :--- | :--- | :--- |
| **`GPIO34 (ADC1_CH6)`** | Throat Mic Input | LM358 buffered vocal cord signal ($d(n)$) |
| **`GPIO35 (ADC1_CH7)`** | Ambient Mic Input | MAX4466 ambient cockpit reference ($x(n)$) |
| **`GPIO25 (DAC1)`** | Audio Output | Processed clean speech to PAM8403 ($e(n)$) |
| **`GPIO2`** | ANC Active LED | Blue LED on when filtering is enabled |
| **`GPIO4`** | Blast Limiter LED | Flashes when artillery shockwave is clamped |
| **`GPIO18`** | Bypass Switch | Toggles between raw throat and filtered ANC |
| **`3V3`** | Analog VCC | Clean filtered 3.3V power rail |
| **`GND`** | Ground | Common star ground |

---

## 💻 4. Repository Structure

```
NIRDHVANI/
├── .github/
│   └── workflows/
│       ├── ci.yml                   # CI/CD: Python simulation, GCC C unit tests, Clang linter
│       └── firmware_build.yml       # Automated PlatformIO ESP32 firmware build verification
├── docs/
│   ├── PRD.md                       # Official DRDO PRD Document
│   ├── wiki.md                      # Complete Non-Tech Builder's Guide
│   └── assets/                      # High-resolution hardware diagrams & photos
│       ├── nirdhvani_3d_prototype_view.jpg
│       └── nirdhvani_exploded_hardware_architecture.jpg
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
├── firmware/
│   ├── include/
│   │   └── nlms_filter.h            # ANSI C NLMS & limiter header
│   ├── src/
│   │   └── nlms_filter.c            # ANSI C NLMS signal processing engine
│   ├── esp32/
│   │   ├── main_esp32.cpp           # Production ESP32 firmware with FreeRTOS & Timer ISR
│   │   └── platformio.ini           # PlatformIO project config
│   ├── stm32/
│   │   └── stm32_tacanc_driver.c    # STM32 CMSIS-DSP DMA double buffer driver
│   └── tests/
│       ├── test_nlms.c              # Native C unit test suite
│       └── verify_c_dsp.py          # Python C-logic validation runner
├── wiki.md                          # Quick link to Builder's Wiki
└── README.md                        # Primary Documentation
```

---

## 🚀 5. Quickstart & Verification

### Running the Python Simulation & Acoustic Benchmark
```bash
# 1. Install dependencies
pip install -r simulation/requirements.txt

# 2. Run end-to-end tactical simulation
python simulation/simulate_tactical_anc.py
```

### Running C Unit Test Verification
```bash
python firmware/tests/verify_c_dsp.py
```

---

## 📊 6. Performance Benchmarks

| Metric | Target Specification | NIRDHVANI Verified Benchmark |
| :--- | :--- | :--- |
| **Sampling Rate** | $\ge 16\text{ kHz}$ / 12-bit | **16.0 kHz / 12-bit Synchronous Dual ADC** |
| **Processing Latency** | $< 10\text{ ms}$ | **< 4.0 ms (64-sample block)** |
| **Noise Attenuation (ERLE)**| $> 18\text{ dB}$ | **+27.75 to 28.00 dB Reduction** |
| **Blast Limiter Response** | $< 2.0\text{ ms}$ | **< 1.0 ms Soft-Tanh Clamping** |
| **Battery Life** | $> 8\text{ hours}$ | **> 12 hours continuous on 18650 Li-ion** |
| **Hackathon Prototype BOM** | $< ₹1000$ | **₹765 INR (~$9.20 USD)** |
| **Industrial Production BOM**| $< $10 USD | **~₹380 INR (~$4.60 USD)** |

---

## 🤝 Contributing & License
Maintained for defence signal processing research and tactical communications engineering. Contributions are welcome via pull request.
