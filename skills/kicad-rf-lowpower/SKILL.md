---
name: kicad-rf-lowpower
description: Hardware engineering rules for RF circuits (LoRa, sub-GHz, 2.4GHz), antenna keepouts, 50Ω coplanar waveguides, solar MPPT battery management, ultra-low-power deep sleep leakage budgeting, and outdoor environmental DFM.
---

# KiCad RF & Low-Power / Solar IoT Engineering Pack

This pack governs sub-GHz RF transceivers (LoRa SX1262/SX1276), 2.4 GHz modules (ESP32, nRF52), solar-powered energy harvesting (MPPT), lithium battery management, and ultra-low-leakage electronics.

---

## 1. RF Antenna Geometry & Sacred Keepouts

```
   ┌────────────────────────────────────────────────────────┐
   │             SACRED RF ANTENNA KEEPOUT ZONE             │
   │  [Antenna Element]  (Zero copper on ALL layers L1..L4) │
   │                     (Zero components, zero traces)     │
   └───────────────────────────┬────────────────────────────┘
                               │ 50Ω Coplanar Waveguide (CPWG)
   ┌───────────────────────────┴────────────────────────────┐
   │ Solid Ground Plane (L1 Ground Pour + L2 Continuous GND)│
   │ Stitched Faraday Via Fence (pitch <= λ/20 ≈ 3.0mm)     │
   └────────────────────────────────────────────────────────┘
```

1. **4-Layer Sacred Antenna Keepout:**
   * PCB trace antennas, ceramic chip antennas, and quarter-wave monopoles require an unbroken clearance void.
   * **Rule:** Remove ALL copper on ALL layers (L1 through L4) beneath the antenna element and extend the void $\ge 5.0\,\text{mm}$ laterally in all directions. No vias, no traces, no testpoints, no metal mounting screws.
2. **50Ω Coplanar Waveguide with Ground (CPWG):**
   * Feed RF energy from the matching network / transceiver to the antenna or SMA/U.FL connector via a 50Ω CPWG.
   * Route RF trace with continuous top-layer ground copper pours on both sides.
   * Stitch top-layer RF ground pours to L2 ground plane with vias spaced $\le 2.0\text{--}3.0\,\text{mm}$ apart to prevent spurious parallel-plate waveguide modes.
3. **RF Matching Network (Pi / T Network):**
   * Place matching inductors and capacitors (0402 / 0201 high-Q parts) immediately adjacent to the transceiver RF pin ($< 2.0\,\text{mm}$).
   * Ground pads of shunt matching elements must have direct, dedicated vias to L2 ground with zero shared traces.

---

## 2. Solar MPPT & Lithium Battery Power Management

When designing solar-powered IoT controllers (e.g. Meshtastic solar nodes):
1. **Solar Input & MPPT Regulator Topology:**
   * Solar panels exhibit high source impedance and fluctuating $V_{\text{MPP}}$ ($4.5\text{--}21\,\text{V}$).
   * Place solar input buffer capacitors ($10\text{--}47\,\mu\text{F}$) directly at the MPPT IC pins (e.g. CN3791, BQ25895, SPV1040).
   * Keep the high-frequency buck/boost switching loop ($C_{\text{IN}} \to \text{FET} \to L \to C_{\text{OUT}}$) tight ($< 15\,\text{mm}^2$ loop area).
2. **Lithium Battery Protection (1S Li-Ion / LiFePO4):**
   * Dual-MOSFET protection IC (e.g. DW01A + 8205A) must have Kelvin sense traces directly to battery terminal pads.
   * Route high-current charging paths ($1\text{--}2\,\text{A}$) using $\ge 1.0\,\text{mm}$ traces.
   * Provide a reverse-polarity protection P-channel MOSFET on the battery input to prevent catastrophic failure on inverted cell insertion.

---

## 3. Ultra-Low Deep Sleep Leakage Budgeting ($< 20\,\mu\text{A}$)

To survive months on solar/battery, static sleep current must be minimized:
1. **Pull-Up / Pull-Down Resistor Discipline:**
   * Never leave low-value pull-ups ($4.7\,\text{k}\Omega$) on lines that rest at logic LOW during deep sleep ($3.3\,\text{V} / 4.7\,\text{k}\Omega = 702\,\mu\text{A}$ continuous drain!).
   * Use $\ge 100\,\text{k}\Omega$ or internal MCU pull-downs configured at sleep entry.
2. **Peripheral Power Gating (High-Side Load Switching):**
   * Sensors, displays (e.g. E-ink, ST7789), GPS modules, and external flash memory draw quiescent leakage even when idle.
   * Place a low-$R_{\text{DS(on)}}$ P-channel MOSFET or integrated load switch (e.g. TPS22918) to completely disconnect peripheral $V_{\text{CC}}$ during sleep.
3. **Floating Analog & ADC Inputs:**
   * Voltage divider resistor networks monitoring battery voltage must be switched through an N-MOSFET, or use high-value resistors ($1\,\text{M}\Omega / 1\,\text{M}\Omega$) paralleled with a $100\,\text{nF}$ filter cap to avoid continuous milliamp bleed.

---

## 4. Outdoor Environmental DFM & Enclosure Sealing

1. **Conformal Coating Keepouts:**
   * Mark clear keepout boundaries on silkscreen and fabrication drawings for U.FL connectors, battery holders, tactile buttons, and DIP switches where conformal coating must not ingress.
2. **Moisture & Condensation Spacing:**
   * Outdoor humidity degrades surface insulation resistance (SIR). Enforce minimum $0.30\,\text{mm}$ trace-to-trace spacing on high-voltage battery rails.
