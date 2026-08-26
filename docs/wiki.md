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
   - [Step 2: Building the LM358 Buffer Circuit](#step-2-building-the-lm358-buffer-circuit)
   - [Step 3: Wiring the Ambient Microphone](#step-3-wiring-the-ambient-microphone)
   - [Step 4: Wiring the ESP32 Microcontroller](#step-4-wiring-the-esp32-microcontroller)
   - [Step 5: Wiring the Audio Amplifier & Earphone Jack](#step-5-wiring-the-audio-amplifier--earphone-jack)
   - [Step 6: Power Subsystem & Battery Safety](#step-6-power-subsystem--battery-safety)
5. [Step-by-Step Software Installation (Beginner Friendly)](#5-step-by-step-software-installation-beginner-friendly)
6. [First-Time Power-On & Testing Guide](#6-first-time-power-on--testing-guide)
7. [Troubleshooting & Common Fixes](#7-troubleshooting--common-fixes)
8. [Frequently Asked Questions (FAQ)](#8-frequently-asked-questions-faq)

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
[ Your Throat ] ---> Vibrations ---> [ Piezo Contact Disc ] ---> [ LM358 Buffer ] ---> [ ESP32 ADC Ch0 ]
                                                                                              |
[ Engine/Guns ] ---> Airborne Sound ---> [ Ambient Mic ] ----------------------------> [ ESP32 ADC Ch1 ]
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
3. **The Buffer protects the sound:** Because the piezo disc generates very delicate electrical signals, passing it directly to a computer chip loses all bass (your voice sounds tinny). We use an **LM358 chip** as an electrical cushion ("high impedance buffer") so full rich vocal tones are saved.
4. **The Filter removes background rumble:** A mathematical algorithm called **NLMS** compares the outside noise to what leaked into the neckband and cancels it out in less than 4 milliseconds.
5. **The Limiter guards your hearing:** Any blast louder than 85 dB is instantly flattened by a soft mathematical clamp.

---

## 3. Required Parts & Tools (Shopping List)

You do **not** need expensive lab equipment. Everything can be bought online from sites like Robu.in, Amazon, or your local hobby electronics shop.

<p align="center">
  <img src="assets/nirdhvani_3d_prototype_view.jpg" alt="NIRDHVANI Assembled Prototype" width="750">
</p>

### Hardware Parts List (~ ₹765 Total)
| Part Name | What it looks like / Model | Approx Cost | Why we need it |
| :--- | :--- | :---: | :--- |
| **ESP32 DevKit V1** | 30-pin Microcontroller with Micro-USB/USB-C | ₹280 | The main computing brain running the noise filter. |
| **Piezoelectric Disc** | 27mm brass disc with white ceramic center | ₹60 | The throat contact sensor that feels vocal vibrations. |
| **LM358 IC** | 8-pin dual op-amp chip | ₹15 | Electrical buffer cushion preserving speech bass. |
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

### Tools Needed
- **Soldering Iron (25W - 35W) + Solder Wire & Flux**
- **Wire Stripper / Small Cutter**
- **Hot Glue Gun / Double-Sided Foam Tape** (for insulating sensors)
- **Computer with USB cable** (Windows, Mac, or Linux)

---

## 4. Step-by-Step Hardware Assembly Guide

<p align="center">
  <img src="assets/nirdhvani_exploded_hardware_architecture.jpg" alt="NIRDHVANI Layer Architecture" width="750">
</p>

### Step 1: Making the Throat Sensor Neckband
1. Take the **27mm brass piezo disc**. Solder two thin flexible wires (red for center ceramic, black for brass rim).
2. Apply a thin dab of hot glue around the solder points to prevent wires from snapping off.
3. Attach the piezo disc to the center of your **elastic velcro neckband**. Ensure the smooth brass side faces inward so it touches the skin firmly next to your Adam's apple (thyroid cartilage).

---

### Step 2: Building the LM358 Buffer Circuit
Place the 8-pin **LM358 IC** onto your perfboard and wire according to this simple pin layout:

```
                  LM358 Dual Op-Amp (Top View)
                           +---v---+
           Output (Pin 1) -| 1   8 |- VCC (+3.3V)
      Inverting - (Pin 2) -| 2   7 |- Output 2 (Unused)
  Non-Inverting + (Pin 3) -| 3   6 |- Inverting 2 (Unused)
              GND (Pin 4) -| 4   5 |- Non-Inverting 2 (Unused)
                           +-------+
```

1. **Power Pins:**
   - Connect **Pin 8 (VCC)** to ESP32 `3V3` pin.
   - Connect **Pin 4 (GND)** to ESP32 `GND` pin.
2. **Make the 1.65V Bias (Virtual Ground):**
   - Connect two $100\text{ k}\Omega$ resistors in series between `3V3` and `GND`.
   - The middle point between them is now $1.65\text{ V}$.
   - Connect a $10\mu\text{F}$ capacitor from this middle point to `GND` (positive leg to middle point).
3. **Connect the Piezo Sensor:**
   - Connect the Piezo Black wire to `GND`.
   - Connect the Piezo Red wire through a $0.1\mu\text{F}$ ceramic capacitor to **Pin 3 (Non-Inverting +)**.
   - Connect a $10\text{ M}\Omega$ resistor between **Pin 3** and the **1.65V middle point** you made in step 2.
4. **Unity Gain Feedback:**
   - Connect a short wire from **Pin 1 (Output)** directly to **Pin 2 (Inverting -)**.
5. **Output to ESP32:**
   - Connect **Pin 1 (Output)** to ESP32 **GPIO34**.

---

### Step 3: Wiring the Ambient Microphone (MAX4466)
The MAX4466 module has 3 pins:
- **`VCC`** $\to$ Connect to ESP32 `3V3` pin.
- **`GND`** $\to$ Connect to ESP32 `GND` pin.
- **`OUT`** $\to$ Connect to ESP32 **GPIO35**.
*(Tip: On the back of the MAX4466 board, use a small screwdriver to set the tiny yellow gain dial to the middle position).*

---

### Step 4: Wiring the ESP32 Microcontroller

| ESP32 Pin | Connects To | Purpose |
| :--- | :--- | :--- |
| **`3V3`** | Power rails of LM358 and MAX4466 | Regulated 3.3V Analog Power |
| **`GND`** | Ground rails of LM358, MAX4466, PAM8403, and Battery | Common Ground |
| **`GPIO34`** | LM358 Pin 1 (Output) | Throat speech sensor input ($d(n)$) |
| **`GPIO35`** | MAX4466 `OUT` pin | Ambient noise reference input ($x(n)$) |
| **`GPIO25`** | PAM8403 Left Input (`L_IN`) | Clean filtered audio DAC output ($e(n)$) |
| **`GPIO2`** | Built-in Blue LED | Glows solid when ANC is Active |
| **`GPIO4`** | External LED (optional) + 220Ω to GND | Flashes when blast spike is clamped |
| **`GPIO18`** | Push button to GND | Toggles between raw audio & filtered ANC |

---

### Step 5: Wiring the Audio Amplifier & Earphone Jack
1. **PAM8403 Module:**
   - **`+5V` / `VDD`** $\to$ Connect to battery positive (`+3.7V` or ESP32 `VIN` pin).
   - **`GND`** $\to$ Connect to Common `GND`.
   - **`L_IN`** $\to$ Connect to ESP32 **GPIO25** through a $1\mu\text{F}$ capacitor.
   - **`L_OUT (+)` and `L_OUT (-)`** $\to$ Connect to 3.5mm female audio jack (Left and Ground pins).
2. Plug your earphones into the 3.5mm jack.

---

### Step 6: Power Subsystem & Battery Safety
1. Connect the **18650 Battery Holder** to the **TP4056 Charger Board**:
   - Red wire $\to$ `B+` pad on TP4056.
   - Black wire $\to$ `B-` pad on TP4056.
2. Connect the output of the TP4056 to your system:
   - `OUT+` $\to$ Connect to ESP32 `VIN` pin (or 5V rail).
   - `OUT-` $\to$ Connect to Common `GND`.
3. To charge the unit, simply plug a standard USB-C cable into the TP4056 module. The red LED indicates charging; blue indicates full.

---

## 5. Step-by-Step Software Installation (Beginner Friendly)

### Option A: Using the Arduino IDE (Recommended for Beginners)

1. **Download and Install Arduino IDE:**
   - Download the free IDE from [arduino.cc](https://www.arduino.cc/en/software).
2. **Add ESP32 Board Support:**
   - Open Arduino IDE $\to$ Click `File` $\to$ `Preferences`.
   - In "Additional Boards Manager URLs", paste:
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Click `Tools` $\to$ `Board` $\to$ `Boards Manager...`, search for `esp32` and click **Install**.
3. **Open the Firmware Project:**
   - Copy `firmware/esp32/main_esp32.cpp`, `firmware/include/nlms_filter.h`, and `firmware/src/nlms_filter.c` into a new folder called `NIRDHVANI_Firmware`.
   - Rename `main_esp32.cpp` to `NIRDHVANI_Firmware.ino`.
   - Open `NIRDHVANI_Firmware.ino` in Arduino IDE.
4. **Select Board & Port:**
   - Plug the ESP32 into your computer via USB.
   - Click `Tools` $\to$ `Board` $\to$ `ESP32 Arduino` $\to$ Select **"DOIT ESP32 DEVKIT V1"** (or ESP32 Dev Module).
   - Click `Tools` $\to$ `Port` $\to$ Select the COM port where your ESP32 is connected (e.g. `COM3` or `COM5`).
5. **Upload Firmware:**
   - Click the **Upload Arrow (➔)** at top left.
   - Wait until you see `Leaving... Hard resetting via RTS pin...` and `Done uploading`.

---

### Option B: Using Python Simulation on Computer (No Hardware Required)

Want to see how the system cleans noise before building hardware? You can run the entire simulation on your PC:

1. Open PowerShell or Terminal:
   ```bash
   git clone https://github.com/gangasagar5928/NIRDHVANI.git
   cd NIRDHVANI
   ```
2. Install Python dependencies:
   ```bash
   pip install -r simulation/requirements.txt
   ```
3. Run the simulation:
   ```bash
   python simulation/simulate_tactical_anc.py
   ```
4. Check the `simulation/output/` folder! You will find generated audio files (`1_clean_throat_speech.wav`, `4_processed_anc_output.wav`) and the waveform analysis plot.

---

## 6. First-Time Power-On & Testing Guide

```
[ Power On ] ---> Blue LED Lights Up ---> Strap Neckband ---> Speak Normally ---> Hear Clean Voice in Earphones
```

1. Put the neckband on with the piezo disc contacting your throat skin firmly on either side of the larynx.
2. Plug your earphones into the 3.5mm jack.
3. Power on the ESP32. The on-board Blue LED will light up solid, indicating **ANC Active**.
4. Speak normally while turning on a loud speaker playing tank engine noise or helicopter rotor sounds nearby.
5. Notice that your voice is loud and clear in the earphones, while the ambient room noise is suppressed by over **27 dB**!

---

## 7. Troubleshooting & Common Fixes

| Issue | Likely Cause | Easy Fix |
| :--- | :--- | :--- |
| **No audio in earphones** | Earphone jack disconnected or PAM8403 power wire loose | Check wiring from ESP32 GPIO25 $\to$ PAM8403 `L_IN` and ensure battery is charged. |
| **Voice sounds muffled or quiet** | Piezo disc is not in firm contact with throat skin | Tighten the elastic neckband slightly so the disc presses snugly against the skin. |
| **High buzzing/humming sound** | Ground loop or unshielded long wires | Connect all `GND` wires to a single common point on the perfboard (Star Grounding). |
| **Noise is not being cancelled** | Ambient mic (MAX4466) gain is too high or too low | Turn the small yellow potentiometer on the back of the MAX4466 until ambient noise matches speech level. |
| **ESP32 not recognized on PC** | Missing CH340 or CP2102 USB driver | Download and install standard CP2102 or CH340 USB driver for your computer. |

---

## 8. Frequently Asked Questions (FAQ)

### Q: Why not use normal noise-cancelling headphones?
**A:** Commercial headphones (like Sony or Bose) use external airborne mics to cancel noise *into your ears*. They do **not** clean up your outgoing voice when you speak inside a 130 dB combat vehicle. NIRDHVANI cleans your transmitted voice so command headquarters can understand you clearly.

### Q: Does the throat mic hurt or shock the neck?
**A:** Absolutely not. The piezo sensor is 100% passive—it generates minuscule millivolt signals from skin motion and never emits any electrical current into the body.

### Q: How long does the battery last?
**A:** A single standard 2600mAh 18650 Li-ion battery powers the entire NIRDHVANI unit (ESP32 + op-amp + PAM8403 amp) for over **12 hours** of continuous tactical communication.

---
*Maintained by NIRDHVANI Open Defence DSP Engineering Team.*
