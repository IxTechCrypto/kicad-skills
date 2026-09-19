---
name: kicad-highspeed
description: Hardware engineering rules for high-speed digital buses, Ethernet (RMII/RGMII), magnetics, USB 2.0/3.0 differential pairs (90Ω/100Ω), return path continuity, via antipad keepouts, and EMI suppression.
---

# KiCad High-Speed Digital & Signal Integrity Engineering Pack

This pack governs high-speed digital buses, fast microcontrollers, Ethernet interfaces (RMII/RGMII), USB differential pairs, SPI display links, and electromagnetic compatibility (EMC).

---

## 1. Controlled Impedance Stackups & Trace Geometry

All high-speed traces reference an unbroken ground plane on the immediately adjacent layer (e.g. L1 signal over L2 solid ground):

| Interface | Signal Type | Target Differential $Z_{\text{diff}}$ | Single-Ended $Z_0$ | Length Matching Tolerance | Typical Geometry (JLC04161H Stackup) |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **USB 2.0 (High Speed)** | Diff Pair (D+ / D-) | **$90\,\Omega \pm 10\%$** | $45\,\Omega$ | Intra-pair $\le 1.25\,\text{mm}$ (50 mils) | $W = 0.20\,\text{mm}, S = 0.15\,\text{mm}, H = 0.10\,\text{mm}$ |
| **Ethernet 100Base-TX** | Diff Pair (TX± / RX±) | **$100\,\Omega \pm 10\%$** | $50\,\Omega$ | Intra-pair $\le 0.50\,\text{mm}$ (20 mils) | $W = 0.18\,\text{mm}, S = 0.20\,\text{mm}, H = 0.10\,\text{mm}$ |
| **Single-Ended Clocks** | Clock / RF Microstrip | N/A | **$50\,\Omega \pm 10\%$** | N/A | $W = 0.36\,\text{mm}, H = 0.20\,\text{mm}$ |
| **RMII (50 MHz Clock)** | Synchronous Bus | N/A | **$50\,\Omega \pm 10\%$** | Match to $\text{REF\_CLK} \le 5\,\text{mm}$ | $W = 0.36\,\text{mm}$, direct point-to-point |

---

## 2. Return Path Continuity & The Antipad Keepout Rule

At frequencies above $100\,\text{kHz}$, return currents flow through the reference plane directly underneath the signal trace to minimize loop inductance ($L \propto \text{Area}$).

1. **Never Route Over Plane Splits:**
   * Crossing a ground or power plane split forces return current around the perimeter of the void, creating a loop antenna that causes massive radiated EMI and signal distortion.
   * If a signal must transition reference planes, place a ground stitching via adjacent to the signal via within $< 1.0\,\text{mm}$.
2. **Via Antipad Clearance Void Keepout (Phil Salmony Rule):**
   * Through-hole component pins and power vias create circular clearance holes (antipads) in internal ground planes.
   * **Fringing Field Rule:** Signal traces must maintain at least **$3 \times H$** (dielectric height) lateral clearance from adjacent-layer via antipad cutouts. Running over or near an antipad cuts the ground return path.

---

## 3. Ethernet Interface & Magnetics Isolation (RMII / RGMII)

When routing Ethernet controllers (e.g. LAN8720A, RTL8211, IP101G):
1. **PHY to Magnetics (Analog Differential Side):**
   * Keep differential pairs ($TX+, TX-$ and $RX+, RX-$) as short as possible ($< 25\,\text{mm}$).
   * Route pairs with $100\,\Omega$ differential impedance. Maintain symmetry around obstacles; never split a differential pair around a via or component.
2. **Chassis Ground vs. Signal Ground Split:**
   * The area between the magnetics (transformer) and the RJ45 connector must be an isolated **Chassis Ground (SHIELD)** zone.
   * Do NOT route digital signal traces into or across the chassis ground boundary.
   * Tie chassis ground to digital ground through a high-voltage safety capacitor ($1\text{--}2\,\text{nF} / 2\text{--}3\,\text{kV}$) and a high-value bleeding resistor ($1\,\text{M}\Omega$).
3. **RMII 50 MHz Clock Discipline:**
   * 50 MHz `REF_CLK` must have a series termination resistor ($22\text{--}33\,\Omega$) placed $< 5\,\text{mm}$ from the driver pin to suppress ringing.
   * Guard the clock line with continuous ground copper or maintain $3W$ isolation from all other signals.

---

## 4. Crosstalk Suppression & Differential Pair Skew

1. **Reconciled Crosstalk Spacing:**
   $$\text{Edge-to-Edge Spacing } S \ge \max(2 \times W, \; 3 \times H)$$
   * For critical clock lines or sensitive analog/ADC lines, escalate to $5W$ spacing or place coplanar ground guard traces with stitching vias every $5\,\text{mm}$.
2. **Intra-Pair Skew Matching:**
   * Keep differential trace lengths equalized to within $\le 5\,\text{mils}$ ($0.127\,\text{mm}$).
   * Place serpentine accordion tuning loops immediately adjacent to the corner or obstacle that introduced the length mismatch.
3. **Layer Transitions:**
   * Minimize via transitions on differential pairs. When transitioning layers, place a pair of ground stitching vias adjacent to the signal via pair.
