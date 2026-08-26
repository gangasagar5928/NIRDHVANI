# Bill of Materials (BOM) & Sourcing Guide
## NIRDHVANI: Tactical AI/ML Adaptive Noise Cancellation Comms
> **N**oise-**I**solated **I**mpulse-**R**esilient Real-Time **D**ecoupled **H**ardware **V**oice **A**daptive **N**etwork **I**solator  
> *(Sanskrit for "Silence / Noise-Free" — Defence Signal Processing)*  
> **Tagline:** *"Decoupled Throat-Acoustic Adaptive Noise Cancellation for Extreme Battlefield Environments"*

### 1. Student Hackathon Prototype BOM (Target: < ₹1,000)

| Item | Component | Specification / Part Number | Qty | Unit Cost (INR) | Source / Vendor | Engineering Note |
| :---: | :--- | :--- | :---: | :---: | :--- | :--- |
| **1** | Main MCU | ESP32-WROOM-32 (30-pin DevKit) | 1 | ₹280 | Robu.in / Amazon IN | Dual 12-bit ADC, Dual Core 240MHz, Internal DAC |
| **2** | Throat Contact Sensor | 27mm Brass Piezoelectric Transducer | 1 | ₹60 | Local Electronics / Robu.in | Resonant frequency 4.6kHz, contact mounted on neck strap |
| **3** | High-Z Op-Amp Buffer | LM358 Dual Low-Power Op-Amp DIP-8 | 1 | ₹15 | Local Shop / ElectronicsComp | 10 MΩ input bias, unity gain buffer for piezo |
| **4** | Reference Noise Sensor| MAX4466 Electret Microphone Module | 1 | ₹145 | Robu.in | Adjustable gain (25x-125x), captures airborne cockpit noise |
| **5** | Audio Power Amp | PAM8403 Mini 3W Class-D Stereo Amp | 1 | ₹40 | Robu.in / ElectronicsComp | High efficiency (>90%), drives 4Ω-32Ω tactical earphones |
| **6** | Headset & Connector | 3.5mm Female Audio Jack + 32Ω In-Ear Buds| 1 set | ₹75 | Local Shop | Low latency listening interface |
| **7** | Power System | 3.7V 2000mAh 18650 Li-ion + TP4056 USB-C | 1 set | ₹120 | Robu.in | Rechargeable battery with over-current/discharge protection |
| **8** | Discrete Passives | Resistors (10M, 100k, 10k), Caps (0.1uF, 10uF) | 1 set | ₹30 | Local Market | Analog bias network & DC coupling |
| **TOTAL**| **Complete Prototype** | **NIRDHVANI Student Unit** | — | **~₹765** | — | Complete functional hardware unit |

---

### 2. Military Grade Industrial Scale BOM (Target Production)

| Module | Military Grade Component | Industrial Specification | Advantage over Hackathon Unit |
| :--- | :--- | :--- | :--- |
| **DSP Core** | STM32H723ZGT6 / ADAU1467 | 550MHz Cortex-M7, Double FPU | Hardware SIMD acceleration, <1ms DSP latency |
| **Primary Sensor** | Tactical Dual Piezo Contact Bar | Balanced Piezo Element in Silicone | IP67 immersion rated, ergonomic neck collar |
| **High-Z AFE** | OPA2353 / AD8605 Precision Op-Amp | $10^{12}\ \Omega$ FET Input, 0.0001% THD | Zero low-frequency attenuation, ultra-low noise floor |
| **AOP Reference Mic**| Knowles / ADI ICS-40730 MEMS | 134 dB SPL Acoustic Overload Point | No clipping up to heavy artillery muzzle blast |
| **Codec / Amp** | TI TLV320AIC3254 DSP Codec | Ultra-Low Power miniDSP, Differential Out| Integrated EQ, stereo ANC, hardware limiter |
| **Enclosure & Power**| Ruggedized CNC Anodized Aluminum | MIL-STD-810G / EMI Shielded Enclosure | Ballistic vibration and RF electromagnetic immunity |
