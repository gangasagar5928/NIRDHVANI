# 📖 NIRDHVANI Complete Builder's Wiki & Non-Tech Assembly Guide
> **N**oise-**I**solated **I**mpulse-**R**esilient Real-Time **D**ecoupled **H**ardware **V**oice **A**daptive **N**etwork **I**solator  
> *(Sanskrit for "Silence / Noise-Free" — Defence Signal Processing)*  
> **Tagline:** *"Decoupled Throat-Acoustic Adaptive Noise Cancellation for Extreme Battlefield Environments"*

---

## 🧭 Table of Contents
1. [What is NIRDHVANI in Simple Words?](#1-what-is-nirdhvani-in-simple-words)
2. [How Does it Work? (The Physics Simplified)](#2-how-does-it-work-the-physics-simplified)
3. [Required Parts & Tools (Shopping List)](#3-required-parts--tools-shopping-list)
4. [Step-by-Step Hardware Assembly Guide](#4-step-by-step-hardware-assembly-guide)
   - [Step 1: Making the Throat Sensor Neckband](#step-1-making-the-throat-sensor-neckband)
   - [Step 2: Building the MCP6001 / Rail-to-Rail Buffer Circuit](#step-2-building-the-mcp6001--rail-to-rail-buffer-circuit)
   - [Step 3: Wiring the Ambient Microphone](#step-3-wiring-the-ambient-microphone)
   - [Step 4: Wiring the ESP32 Microcontroller](#step-4-wiring-the-esp32-microcontroller)
   - [Step 5: Wiring the Audio Amplifier & Earphone Jack](#step-5-wiring-the-audio-amplifier--earphone-jack)
   - [Step 6: Power Subsystem & Battery Safety](#step-6-power-subsystem--battery-safety)
5. [Throat Mic Mechanical Fitting & Calibration](#5-throat-mic-mechanical-fitting--calibration)
6. [Step-by-Step Software Installation (Beginner Friendly)](#6-step-by-step-software-installation-beginner-friendly)
7. [First-Time Power-On & Testing Guide](#7-first-time-power-on--testing-guide)
8. [Troubleshooting & Common Fixes](#8-troubleshooting--common-fixes)
9. [Frequently Asked Questions (FAQ)](#9-frequently-asked-questions-faq)

---

## 1. What is NIRDHVANI in Simple Words?

Imagine standing inside a heavy battle tank or near artillery firing: the roar of the engine and gunshots is deafening (120 to 140 decibels). If you speak into a standard phone or walkie-talkie mic, three bad things happen:
1. **The microphone overloads ("clips"):** Sound turns into horrible scratchy distortion.
2. **Noise drowns your voice:** The listener only hears engine roar.
3. **Explosions hurt your ears:** Sudden shockwaves can cause permanent hearing damage.

**NIRDHVANI fixes this with two sensors and a smart chip:**
- **Sensor 1 (Throat Mic):** A small vibration disc sits directly on your neck. It feels your vocal cords vibrating through your skin like a doctor's stethoscope. Airborne noise *cannot* get in.
- **Sensor 2 (Ambient Mic):** A regular mic pointing outward listens *only* to the surrounding battlefield noise.
- **The Brain (ESP32 Chip):** In real time, the chip takes the noise heard by Sensor 2 and subtracts it from Sensor 1, leaving only crystal-clear human speech, while clamping any dangerous explosive spikes to protect your hearing.

---

## 2. How Does it Work? (The Physics Simplified)

```
[ Your Throat ] ---> Vibrations ---> [ Piezo Contact Disc ] ---> [ MCP6001 Buffer ] ---> [ ESP32 ADC Ch0 ]
                                                                                               |
[ Engine/Guns ] ---> Airborne Sound ---> [ Ambient Mic ] -----------------------------> [ ESP32 ADC Ch1 ]
                                                                                               |
                                                                                       (NLMS Subtraction)
                                                                                               |
                                                                                      [ Clean Speech Out ]
                                                                                               |
                                                                                      [ PAM8403 Amp ]
                                                                                               |
                                                                                      [ Tactical Earphones ]
```

1. **Vocal Cords vibrate your neck tissue:** When you speak, your neck skin moves.
2. **The Piezo Disc converts movement to electricity:** A small brass disc with ceramic coating generates a tiny electrical voltage when pushed.
3. **The Buffer protects the sound:** Because the piezo disc generates very delicate electrical signals, passing it directly to a computer chip loses all bass (your voice sounds tinny). We use an **MCP6001 or TS321 chip** as an electrical cushion ("Rail-to-Rail high impedance buffer") so full rich vocal tones are saved without clipping on a 3.3V power supply.
4. **The Filter removes background rumble:** A mathematical algorithm called **NLMS** compares the outside noise to what leaked into the neckband and cancels it out in less than 4 milliseconds.
5. **The Limiter guards your hearing:** Any blast louder than 85 dB is instantly flattened by a soft mathematical clamp.

---

## 3. Required Parts & Tools (Shopping List)

You do **not** need expensive lab equipment. Everything can be bought online from sites like Robu.in, Amazon, or your local hobby electronics shop.

<p align="center">
  <img src="docs/assets/nirdhvani_3d_prototype_view.jpg" alt="NIRDHVANI Assembled Prototype" width="750">
</p>

### Hardware Parts List (~ ₹780 Total)
| Part Name | What it looks like / Model | Approx Cost | Why we need it |
| :--- | :--- | :---: | :--- |
| **ESP32 DevKit V1** | 30-pin Microcontroller with Micro-USB/USB-C | ₹280 | The main computing brain running the noise filter. |
| **Piezoelectric Disc** | 27mm brass disc with white ceramic center | ₹60 | The throat contact sensor that feels vocal vibrations. |
| **MCP6001 / TS321** | 5-pin SOT23 or 8-pin DIP Rail-to-Rail Op-Amp | ₹25 | Rail-to-rail buffer preserving bass without clipping at 3.3V. *(LM358 is low-cost fallback).* |
| **MAX4466 Module** | Small red/purple breakout board with mic & knob | ₹145 | The ambient microphone listening to outside noise. |
| **PAM8403 Amp Module** | Small green board with volume wheel or pins | ₹40 | Boosts audio signal so you can hear clearly in earphones. |
| **3.5mm Audio Jack** | Female stereo audio jack (PCB mount or wire) | ₹25 | Connects standard 3.5mm earphones. |
| **32Ω Earphones** | Standard 3.5mm wired in-ear headphones | ₹50 | Operator listening device. |
| **TP4056 USB-C Board** | Small blue charging module with battery protection | ₹25 | Safely charges the 3.7V battery via USB. |
| **18650 Li-ion Battery**| Cylindrical 3.7V rechargeable battery | ₹95 | Portable power supply (lasts 12+ hours). |
| **18650 Single Holder** | Plastic battery clip with red/black wires | ₹20 | Holds battery firmly in place. |
| **Resistors & Caps** | 10MΩ (1x), 100kΩ (2x), 10kΩ (1x), 0.1µF (2x), 10µF (1x) | ₹15 | Clean up and balance electrical voltages. |
| **Elastic Neck Strap** | 1-inch wide velcro elastic strap | ₹20 | Holds piezo disc snugly against neck. |
| **Perfboard & Wires** | Dotted copper prototyping board + jumper wires | ₹20 | For soldering components together. |

---

## 4. Step-by-Step Hardware Assembly Guide

<p align="center">
  <img src="docs/assets/nirdhvani_exploded_hardware_architecture.jpg" alt="NIRDHVANI Layer Architecture" width="750">
</p>

### Step 1: Making the Throat Sensor Neckband
1. Take the **27mm brass piezo disc**. Solder two thin flexible wires (red for center ceramic, black for brass rim).
2. Apply a thin dab of hot glue around the solder points to prevent wires from snapping off.
3. Attach the piezo disc to the center of your **elastic velcro neckband**. Ensure the smooth brass side faces inward so it touches the skin firmly next to your larynx.

---

### Step 2: Building the MCP6001 / Rail-to-Rail Buffer Circuit
Place the **MCP6001 / TS321 IC** (or LM358) onto your perfboard:

```
               +3.3V (Clean Analog Rail)
                 |
               [ R1: 100k ]
                 |-----+-------- V_BIAS (1.65V Virtual Ground)
                 |     |
               [ R2: 100k ]  [ C_BIAS: 10uF Capacitor ]
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
                                         | \  MCP6001 / TS321 (RRIO)
                            Non-Inv (+)  |  \
                     ------------------->|   \
                                         |    \________ Output ------> ESP32 GPIO34 (ADC1_CH6)
                                    +--->|    /
                                    |    |   /
                                    +----+--+ (Unity Gain Feedback)
```

1. **Power:** Connect VCC to ESP32 `3V3` and GND to ESP32 `GND`.
2. **Virtual Ground:** Split 3.3V using two 100kΩ resistors with a 10µF capacitor to make a rock-solid 1.65V center reference.
3. **High-Z Input:** Bias the non-inverting input through a 10MΩ resistor connected to the 1.65V reference. Connect the piezo disc through a 0.1µF DC decoupling capacitor.
4. **Buffer Output:** Tie inverting input to output for unity gain; feed output into ESP32 `GPIO34`.

---

### Step 3: Wiring the Ambient Microphone (MAX4466)
- **`VCC`** $\to$ ESP32 `3V3`.
- **`GND`** $\to$ ESP32 `GND`.
- **`OUT`** $\to$ ESP32 **GPIO35**.

---

### Step 4: Wiring the ESP32 Microcontroller

| ESP32 Pin | Connects To | Purpose |
| :--- | :--- | :--- |
| **`3V3`** | Buffer & MAX4466 power | Clean 3.3V Analog Power |
| **`GND`** | Common Ground | System Ground |
| **`GPIO34`** | Buffer Output | Throat speech sensor input ($d(n)$) |
| **`GPIO35`** | MAX4466 `OUT` | Ambient noise reference input ($x(n)$) |
| **`GPIO25`** | PAM8403 `L_IN` | Clean filtered audio DAC output ($e(n)$) |
| **`GPIO2`** | Built-in Blue LED | Glows solid when ANC is Active |
| **`GPIO4`** | External LED + 220Ω | Flashes when blast spike is clamped |
| **`GPIO18`** | Push button to GND | Toggles between raw audio & filtered ANC |

---

### Step 5: Wiring the Audio Amplifier & Earphone Jack
1. Connect PAM8403 `+5V`/`VDD` to 3.7V battery rail and `GND` to common ground.
2. Connect ESP32 `GPIO25` through a $1\mu\text{F}$ capacitor to PAM8403 `L_IN`.
3. Connect PAM8403 `L_OUT (+/-)` to 3.5mm female audio jack.

---

### Step 6: Power Subsystem & Battery Safety
1. Connect 18650 holder to TP4056 `B+` and `B-`.
2. Connect TP4056 `OUT+` to ESP32 `VIN` and `OUT-` to common `GND`.
3. Charge with any standard USB-C cable.

---

## 5. Throat Mic Mechanical Fitting & Calibration

1. **Anatomical Placement:** Place the piezo sensor 1 to 2 cm to the side of the Adam's apple (thyroid cartilage) directly over skin.
2. **Pressure Check:** The collar should feel snug like a necktie ($1.5 - 2.5\text{ N/cm}^2$).
3. **Gain Alignment:** Hum a low tone and adjust the MAX4466 ambient trimmer until ambient noise and throat channel levels match during loud room tests.

---

## 6. Step-by-Step Software Installation (Beginner Friendly)

### Option A: Using the Arduino IDE
1. Install [Arduino IDE](https://www.arduino.cc/en/software).
2. Add ESP32 support in Preferences (`https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`).
3. Open `firmware/esp32/main_esp32.cpp` as an `.ino` sketch.
4. Select board **DOIT ESP32 DEVKIT V1**, select your COM port, and click **Upload**.

---

### Option B: Running Python Simulation on PC
```bash
git clone https://github.com/gangasagar5928/NIRDHVANI.git
cd NIRDHVANI
pip install -r simulation/requirements.txt
python simulation/simulate_tactical_anc.py
```
View output graphs and WAV files in `simulation/output/`.

---

## 7. First-Time Power-On & Testing Guide
1. Power on ESP32; on-board Blue LED lights up solid (**ANC Enabled**).
2. Put on the neckband and earphones.
3. Turn on a speaker playing loud engine noise nearby. Speak normally—hear your voice clean and noise suppressed by **>24 dB**!

---

## 8. Troubleshooting & Common Fixes

| Issue | Likely Cause | Easy Fix |
| :--- | :--- | :--- |
| **No sound** | Wire loose on GPIO25 or PAM8403 | Check connection from GPIO25 $\to$ PAM8403 `L_IN`. |
| **Voice muffled** | Sensor loose on neck | Tighten neckband strap so brass disc touches skin firmly. |
| **Buzzing hum** | Ground loop | Connect all ground wires to one central point (Star Ground). |
| **Clipping on loud speech** | Using LM358 instead of MCP6001 | Swap op-amp to MCP6001 / TS321 for true rail-to-rail swing. |

---

## 9. Frequently Asked Questions (FAQ)

### Q: Is 24.9 dB ERLE simulation or hardware?
**A:** 26.90 dB is the theoretical simulation benchmark; 24.90 dB is with modeled hardware non-linearities (12-bit ADC DNL + 8-bit DAC). Physical chamber testing on hardware prototype is actively in progress.

### Q: Can I use LM358 if I don't have MCP6001?
**A:** Yes, LM358 works for basic speech, but keep volume moderate so peaks don't clip against the 2.1V upper swing limit.

---
*Maintained by NIRDHVANI Open Defence DSP Engineering Team.*
