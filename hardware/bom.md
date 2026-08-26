# Bill of Materials (BOM) & Sourcing Guide
## NIRDHVANI: Tactical AI/ML Adaptive Noise Cancellation Comms
> **N**oise-**I**solated **I**mpulse-**R**esilient Real-Time **D**ecoupled **H**ardware **V**oice **A**daptive **N**etwork **I**solator  
> *(Sanskrit for "Silence / Noise-Free" — Defence Signal Processing)*  
> **Tagline:** *"Decoupled Throat-Acoustic Adaptive Noise Cancellation for Extreme Battlefield Environments"*

---

### 1. Student Hackathon Prototype BOM (Target: < ₹1,000)

| Item | Component | Specific Part / Model | Qty | Unit Cost (INR) | Sourcing / Engineering Note |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **1** | Main Compute MCU | ESP32-WROOM-32 (30-pin DevKit) | 1 | ₹280 | Dual 12-bit ADC (calibrated via eFuse), Core 1 isolated DSP, 8-bit internal DAC. |
| **2** | Throat Contact Sensor | 27mm Brass Piezoelectric Transducer | 1 | ₹60 | Direct skin contact vocal cord vibration sensing. |
| **3** | High-Z Rail-to-Rail Buffer | **MCP6001 / TS321** (or LM358*) | 1 | ₹25 | True Rail-to-Rail I/O op-amp ($R_{in} = 10\text{ M}\Omega$). *(LM358 is low-cost fallback with top 200mV swing limit).* |
| **4** | Ambient Noise Sensor | MAX4466 Electret Microphone Module | 1 | ₹145 | Adjustable pre-amp gain (25x–125x), captures airborne cockpit/engine noise. |
| **5** | Audio Power Amp | PAM8403 Mini 3W Class-D Stereo Amp | 1 | ₹40 | High efficiency (>90%), drives 4Ω–32Ω tactical earphones. |
| **6** | Output Interface | 3.5mm Female Audio Jack + 32Ω Earphones | 1 set | ₹75 | Low-latency listening interface. |
| **7** | Power System | 3.7V 2000mAh 18650 Li-ion + TP4056 USB-C | 1 set | ₹120 | Protected rechargeable 3.7V source with overcharge/discharge IC. |
| **8** | Passives & Shielding | 10MΩ, 100kΩ, 10kΩ, 0.1µF, 10µF, Shielded Cable| 1 set | ₹35 | Virtual ground bias network, anti-aliasing filter, braided cable. |
| **TOTAL**| **Complete Prototype** | **NIRDHVANI Hackathon Unit** | — | **~₹780** | **Complete functional hardware unit** |

*(Optional Audio Upgrade: External I2S 24-bit DAC Module MAX98357A / PCM5102A can be added for +₹90).*

---

### 2. Military Grade Industrial Scale BOM (Production Deployment)

| Module | Military Grade Component | Industrial Specification | Advantage over Hackathon Unit |
| :--- | :--- | :--- | :--- |
| **DSP Core** | STM32H723ZGT6 / ADAU1467 | 550MHz Cortex-M7, Double FPU | Hardware SIMD acceleration, <1ms DSP latency, 24-bit internal precision. |
| **Primary Sensor** | Tactical Dual Piezo Contact Bar | Balanced Piezo Element in Silicone | IP67 immersion rated, ergonomic tactical neck collar with breakaway connector. |
| **High-Z AFE** | OPA2353 / AD8605 Precision Op-Amp | $10^{12}\ \Omega$ FET Input, RRIO, 0.0001% THD | Zero low-frequency attenuation, rail-to-rail swing, ultra-low noise floor. |
| **AOP Reference Mic**| Knowles / ADI ICS-40730 MEMS | 134 dB SPL Acoustic Overload Point | Prevents acoustic clipping up to heavy artillery muzzle blast levels. |
| **Codec / Amp** | TI TLV320AIC3254 DSP Codec | Ultra-Low Power miniDSP, Differential Out| 24-bit 96kHz stereo DAC/ADC, hardware EQ, hardware dynamic range compressor. |
| **Enclosure & Shielding**| CNC Anodized Aluminum Housing | MIL-STD-810G / EMI Shielded Enclosure | Ballistic vibration, thermal shock (-40°C to +85°C), and RF electromagnetic immunity. |
| **TOTAL (Mass Prod)**| **Tactical Headset Unit** | **NIRDHVANI Production Unit** | — | **~₹380 / $4.60 USD** (at 10,000+ unit scale) |
