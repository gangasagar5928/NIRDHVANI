# 🧾 NIRDHVANI: Bill of Materials (BOM) & Connections Guide
> **N**oise-**I**solated **I**mpulse-**R**esilient Real-Time **D**ecoupled **H**ardware **V**oice **A**daptive **N**etwork **I**solator
> *(Sanskrit for "Silence / Noise-Free" — Defence Signal Processing)*
> **Purpose:** One document to source every component and wire them together for the NIRDHVANI prototype. Complements [`../hardware/bom.md`](../hardware/bom.md) (cost tables) and [`../hardware/hardware_schematic.md`](../hardware/hardware_schematic.md) (detailed schematics).

---

## 1. System Block Diagram

```
             ┌────────────────────────────────────────────────────────────┐
  Throat Piezo│   MCP6001 High-Z   ┌──────────────────────────────┐        │
  (27mm brass)│── Buffer (10MΩ RRIO)── ADC Ch0 (GPIO34)           │        │
             └────────────────────── │                             │        │
                                     │        MCU (ESP32/STM32)    │        │
  Ambient Mic │   MAX4466 preamp ─── ADC Ch1 (GPIO35)             │        │
  (electret)  │                        │                           │        │
             └────────────────────── │  Block-Wiener Canceller    │        │
                                     │  → Spectral Residual Gate   │        │
                                     │  → Soft-Tanh Limiter        │        │
                                     │  → AGC                      │        │
                                     │   │                         │        │
                                     │   ▼                         │        │
                                     │  DAC (GPIO25) / I2S ───────┘        │
                                     └────────────┬─────────────────────────┘
                                                  ▼
                                RC Reconstruction (100Ω + 10nF)
                                                  ▼
                              PAM8403 Class-D Amp → 3.5mm Jack → Earphones
```

---

## 2. Bill of Materials (Hackathon Prototype — ₹780 target)

| # | Component | Part / Model | Qty | Unit (₹) | Sourcing Note |
| :---: | :--- | :--- | :---: | :---: | :--- |
| 1 | Main Compute MCU | ESP32-WROOM-32E DevKit (or STM32F401 Black Pill) | 1 | ₹280 | Dual 12-bit ADC, isolated DSP core, 8-bit DAC / I2S. |
| 2 | Throat Contact Sensor | 27 mm Brass Piezo Transducer (×2 for differential) | 1 | ₹60 | Direct skin-contact vocal-cord vibration pickup. |
| 3 | High-Z Rail-to-Rail Buffer | **MCP6001 / TS321** (RRIO op-amp) | 2 | ₹25 | 10 MΩ input, 0.025 V–3.275 V swing; one per piezo. |
| 4 | Ambient Noise Sensor | MAX4466 Electret Mic Module | 1 | ₹145 | Adjustable pre-amp (25×–125×), captures airborne noise. |
| 5 | Audio Power Amp | PAM8403 3 W Class-D Stereo | 1 | ₹40 | >90% efficiency, drives 4 Ω–32 Ω earphones. |
| 6 | Output Interface | 3.5 mm Female Jack + 32 Ω Earphones | 1 set | ₹75 | Low-latency listening interface. |
| 7 | Power System | 3.7 V 2000 mAh 18650 Li-ion + TP4056 USB-C | 1 set | ₹120 | Protected, rechargeable, with charge/discharge IC. |
| 8 | Passives & Protection | BAT54S diodes, 10 MΩ, 1 kΩ, 100 kΩ, 100 Ω FB, 0.1 µF, 10 µF | 1 set | ₹35 | Clamping, bias, LC/RC filtering, shielded cable. |
| **TOTAL** | **Complete Prototype** | | | **₹780** | *(+₹90 optional: MAX98357A/PCM5102A I2S 24-bit DAC)* |

> See [`../hardware/bom.md`](../hardware/bom.md) for the military-grade production BOM (STM32H723/ADAU1467, OPA2353, Knowles MEMS, TLV320AIC3254).

---

## 3. Complete Connections / Wiring Guide (Zero-Conflict Pinout)

### 3.1 MCU Pin Mapping (ESP32-WROOM-32 / STM32F401)

| Subsystem | Signal | ESP32-WROOM-32 Pin | STM32F401 Pin | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Throat Sensor Ch0 | Primary speech d(n) | **GPIO34** (ADC1_CH6) | PA0 (ADC1_IN0) | After MCP6001 buffer. |
| Throat Sensor Ch1 | Differential piezo 2 | **GPIO36** (ADC1_CH0) | PA1 (ADC1_IN1) | Optional 2nd channel. |
| Ambient Mic | Reference noise x(n) | **GPIO35** (ADC1_CH7) | PA1 (ADC1_IN1) | MAX4466 preamp output. |
| Audio Output | Clean speech e(n) | **GPIO25** (8-bit DAC) / I2S | PA4 (DAC_OUT1) / I2S | → RC filter → PAM8403. |
| Status LED 1 | ANC Active | GPIO2 (on-board) | PC13 (on-board) | Processing active. |
| Status LED 2 | Limiter/DTD | GPIO4 | PB0 | Blast/impulse active. |
| Bypass Switch | ANC on/off | GPIO18 (pull-up) | PB12 (pull-up) | Ground to toggle. |
| Power Rail | Clean 3.3 V | 3V3 | 3V3 | Filtered analog rail. |
| Ground | Analog ground | GND | GND | Star ground to chassis. |

### 3.2 Analog Front-End Wiring (Throat Piezo → MCP6001 → ADC)

```
 PIEZO(+) ──[ C_IN: 0.1µF ]──[ R_PROT: 1kΩ ]──┬──── MCP6001 Non-Inv (+) ──► GPIO34
                                              ├──[▼ BAT54S → GND]        (unity-gain follower)
                                              └──[▲ BAT54S → +3.3V_ANA]
 PIEZO(−) ──────────────────────────────────── GND
 Bias: MCP6001 (+) also tied to V_BIAS (1.65 V) via 10 MΩ (VCC/2 virtual ground).
```

- **Purpose of 10 MΩ:** preserves low-frequency speech fundamentals (F0 ≈ 85–255 Hz) that a low-impedance ADC would high-pass away.
- **Purpose of BAT54S clamps:** limit blast-induced piezo transients (>15 V) to −0.3 V … +3.6 V before the op-amp/ADC.
- **Two piezo elements** are wired differentially to cancel common-mode neck/strap friction.

### 3.3 Ambient Mic Wiring (MAX4466 → ADC)

```
 MAX4466 VCC ─── +3.3V_ANA
 MAX4466 GND ─── AGND
 MAX4466 OUT ─── GPIO35 (ADC1_CH7)
 MAX4466 Pot  ─── trim gain so ambient RMS ≈ leaked-throat RMS during silence
```

### 3.4 Output Path Wiring (DAC → Filter → Amp → Earphones)

```
 GPIO25 (DAC) ──[ R_REC: 100Ω ]──┬──[ C_DC: 1µF ]──► PAM8403 L_IN
                                 │
                            [ C_REC: 10nF ]  (fc ≈ 159 kHz reconstruction)
                                 │
                                AGND

 PAM8403 SPK+ / SPK− ───► 3.5mm Jack ───► 32Ω Earphones
 (Class-D output; use short twisted leads to minimize 250 kHz ripple)
```

### 3.5 Power Tree

```
 18650 Li-ion (3.7 V)
      │
  TP4056 (USB-C charge) ── +BAT ──► [5V boost / LDO → 3.3V] ──► MCU VIN
      │
      └──► PAM8403 VCC (direct, with 100µF + 0.1µF decoupling)
 3.3V ──[ 100Ω @ 100MHz Ferrite Bead ]──► +3.3V_ANA (op-amp + ADC reference)
                                             └─ 10µF tantalum + 0.1µF ceramic to AGND
```

> **Star grounding:** route all AGND (analog) returns to a single star point connected to chassis ground. Keep the 250 kHz Class-D PWM return and the sensitive piezo return physically separate.

---

## 4. Assembly Order (Checklist)

1. **Power first:** 18650 + TP4056 → verify 3.3 V and 5 V rails.
2. **MCU:** flash firmware, verify USB serial + on-board LED.
3. **Analog front-end:** solder MCP6001 buffers + BAT54S clamps; check piezo output with scope (~1.65 V bias, mV speech signal).
4. **Ambient mic:** wire MAX4466, trim gain.
5. **Output path:** DAC → RC filter → PAM8403 → jack; verify clean tone at earphones.
6. **Power isolation:** add ferrite bead on 3V3_ANA; confirm no 250 kHz ripple on ADC.
7. **Mechanical:** fit dual-piezo neckband with silicone pads at 1.5–2.5 N/cm².
8. **Calibration:** silent-user null (ADC Ch0 ≈ 2048 ± 60 counts); match ambient RMS to leaked RMS; verify ANC cancels stationary tone with user silent.

---

## 5. Wiring Safety Notes

- Never apply > 3.6 V to any ADC pin — rely on BAT54S clamps + 1 kΩ series.
- Use shielded/twisted pair for the throat-piezo cable to reject EMI/RFI.
- Confirm the PAM8403 heat sink / decoupling before long runs.
- For MIL-hardening, follow [`../hardware/hardware_schematic.md`](../hardware/hardware_schematic.md) §6 (EMI/RFI shielding, MIL-STD-810G methods).

*Maintained by the NIRDHVANI Tactical Communications Engineering Team.*
