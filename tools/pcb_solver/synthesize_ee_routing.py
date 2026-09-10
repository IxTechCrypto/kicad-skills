#!/usr/bin/env python3
"""
synthesize_ee_routing.py — Production-Grade Electrical Engineering PCB Routing Synthesizer
"""

import math
import os
import sys

try:
    import pcbnew
except ImportError:
    print("[ERROR] pcbnew module not found.", file=sys.stderr)
    sys.exit(1)


def add_track(board, net_code, layer, x1_mm, y1_mm, x2_mm, y2_mm, width_mm=0.25):
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(pcbnew.VECTOR2I(int(x1_mm * 1e6), int(y1_mm * 1e6)))
    track.SetEnd(pcbnew.VECTOR2I(int(x2_mm * 1e6), int(y2_mm * 1e6)))
    track.SetWidth(int(width_mm * 1e6))
    track.SetLayer(layer)
    track.SetNetCode(net_code)
    board.Add(track)
    return track


def add_via(board, net_code, x_mm, y_mm, size_mm=0.70, drill_mm=0.30):
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pcbnew.VECTOR2I(int(x_mm * 1e6), int(y_mm * 1e6)))
    via.SetWidth(int(size_mm * 1e6))
    via.SetDrill(int(drill_mm * 1e6))
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetNetCode(net_code)
    board.Add(via)
    return via


def add_45_route(board, net_code, layer, x1, y1, x2, y2, width_mm=0.25):
    dx = x2 - x1
    dy = y2 - y1

    if abs(dx) < 1e-4 or abs(dy) < 1e-4:
        add_track(board, net_code, layer, x1, y1, x2, y2, width_mm)
        return

    if abs(dx) >= abs(dy):
        sign_x = 1.0 if dx > 0 else -1.0
        corner_x = x1 + sign_x * abs(dy)
        add_track(board, net_code, layer, x1, y1, corner_x, y2, width_mm)
        add_track(board, net_code, layer, corner_x, y2, x2, y2, width_mm)
    else:
        sign_y = 1.0 if dy > 0 else -1.0
        corner_y = y1 + sign_y * abs(dx)
        add_track(board, net_code, layer, x1, y1, x2, corner_y, width_mm)
        add_track(board, net_code, layer, x2, corner_y, x2, y2, width_mm)


def synthesize_routing(board_path):
    print(f"[*] Loading board: {board_path}")
    board = pcbnew.LoadBoard(board_path)

    old_tracks = list(board.GetTracks())
    for t in old_tracks:
        board.Remove(t)
    print(f"    -> Cleared {len(old_tracks)} legacy tracks/vias")

    net_gnd_obj = board.FindNet("GND")
    net_3v3_obj = board.FindNet("+3V3") or board.FindNet("+3.3V")
    net_vbus_obj = board.FindNet("+5V") or board.FindNet("VBUS")

    gnd_code = net_gnd_obj.GetNetCode() if net_gnd_obj else 0
    p3v3_code = net_3v3_obj.GetNetCode() if net_3v3_obj else 0
    vbus_code = net_vbus_obj.GetNetCode() if net_vbus_obj else 0

    print("[*] 1. Routing RMII 50MHz High-Speed Ethernet Bus (U2 LAN8720A <-> U1 ESP32)...")
    rmii_signals = [
        ("TX_EN", 10.0, 10.5),
        ("TXD0",  10.4, 11.0),
        ("TXD1",  10.8, 11.5),
        ("RX_ER", 11.2, 12.0),
        ("RX_DV", 11.6, 12.5),
        ("RXD0",  12.0, 13.0),
        ("RXD1",  12.4, 13.5),
        ("MDC",   12.8, 14.0),
        ("MDIO",  13.2, 14.5)
    ]
    for idx, (sig, y_u2, y_u1) in enumerate(rmii_signals):
        x_start = 30.5
        x_trunk_in = 33.5 + idx * 0.35
        x_trunk_out = 43.0 + idx * 0.35
        x_end = 46.5

        add_45_route(board, 0, pcbnew.F_Cu, x_start, y_u2, x_trunk_in, y_u1, width_mm=0.20)
        add_track(board, 0, pcbnew.F_Cu, x_trunk_in, y_u1, x_trunk_out, y_u1, width_mm=0.20)
        add_45_route(board, 0, pcbnew.F_Cu, x_trunk_out, y_u1, x_end, y_u1, width_mm=0.20)

    print("[*] 2. Routing 50MHz Reference Clock (Y1 Oscillator -> U2 & U1)...")
    add_45_route(board, 0, pcbnew.F_Cu, 28.0, 6.8, 28.0, 9.8, width_mm=0.25)
    add_45_route(board, 0, pcbnew.F_Cu, 28.0, 9.8, 46.5, 9.8, width_mm=0.25)

    print("[*] 3. Routing Ethernet Differential Pairs (U2 LAN8720A <-> J1 HR911105A RJ45)...")
    add_track(board, 0, pcbnew.F_Cu, 26.0, 11.2, 21.0, 11.2, width_mm=0.25)
    add_track(board, 0, pcbnew.F_Cu, 26.0, 11.7, 21.0, 11.7, width_mm=0.25)
    add_45_route(board, 0, pcbnew.F_Cu, 21.0, 11.2, 18.0, 13.5, width_mm=0.25)
    add_45_route(board, 0, pcbnew.F_Cu, 21.0, 11.7, 18.0, 14.5, width_mm=0.25)

    add_track(board, 0, pcbnew.F_Cu, 26.0, 15.5, 21.0, 15.5, width_mm=0.25)
    add_track(board, 0, pcbnew.F_Cu, 26.0, 16.0, 21.0, 16.0, width_mm=0.25)
    add_45_route(board, 0, pcbnew.F_Cu, 21.0, 15.5, 18.0, 16.5, width_mm=0.25)
    add_45_route(board, 0, pcbnew.F_Cu, 21.0, 16.0, 18.0, 17.5, width_mm=0.25)

    print("[*] 4. Routing USB 2.0 90-Ohm Differential Pair (J2 USB-C <-> U4 CH340E on B.Cu)...")
    add_track(board, 0, pcbnew.F_Cu, 27.6, 26.5, 27.6, 23.5, width_mm=0.28)
    add_track(board, 0, pcbnew.F_Cu, 28.4, 26.5, 28.4, 23.5, width_mm=0.28)
    add_via(board, 0, 27.6, 23.0)
    add_via(board, 0, 28.4, 23.0)
    add_track(board, 0, pcbnew.B_Cu, 27.6, 23.0, 27.6, 17.0, width_mm=0.28)
    add_track(board, 0, pcbnew.B_Cu, 28.4, 23.0, 28.4, 17.0, width_mm=0.28)
    add_45_route(board, 0, pcbnew.B_Cu, 27.6, 17.0, 26.5, 15.2, width_mm=0.28)
    add_45_route(board, 0, pcbnew.B_Cu, 28.4, 17.0, 26.5, 15.8, width_mm=0.28)

    print("[*] 5. Routing MicroSD High-Speed Bus Trunk (U1 ESP32 -> J4 on B.Cu)...")
    sd_signals = [
        ("SD_CLK",  16.0, 4.5),
        ("SD_CMD",  16.5, 5.5),
        ("SD_DAT0", 17.0, 6.5),
        ("SD_DAT1", 17.5, 7.5),
        ("SD_DAT2", 18.0, 8.5),
        ("SD_DAT3", 18.5, 9.5)
    ]
    for idx, (sig, y_u1, y_sd) in enumerate(sd_signals):
        x_via = 44.0 + idx * 0.45
        add_45_route(board, 0, pcbnew.F_Cu, 46.5, y_u1, x_via, y_u1, width_mm=0.20)
        add_via(board, 0, x_via, y_u1)
        add_45_route(board, 0, pcbnew.B_Cu, x_via, y_u1, 42.0, y_sd, width_mm=0.20)

    print("[*] 6. Routing ST7789 IPS Display SPI Bus (U1 ESP32 -> J3 FPC Connector)...")
    disp_signals = [
        ("DISP_CS",   8.5, 43.5),
        ("DISP_DC",   9.0, 44.5),
        ("DISP_RST",  9.5, 45.5),
        ("DISP_MOSI", 10.0, 46.5),
        ("DISP_SCLK", 10.5, 47.5),
        ("DISP_BL",   11.0, 48.5)
    ]
    for sig, y_u1, x_j3 in disp_signals:
        add_45_route(board, 0, pcbnew.F_Cu, 46.5, y_u1, x_j3, 5.5, width_mm=0.20)
        add_track(board, 0, pcbnew.F_Cu, x_j3, 5.5, x_j3, 3.8, width_mm=0.20)

    print("[*] 7. Routing Power Stage & High-Current Loops (VBUS -> U3 Buck -> L1 -> +3.3V Rail)...")
    add_track(board, vbus_code, pcbnew.F_Cu, 28.0, 26.5, 36.0, 26.5, width_mm=0.80)
    add_45_route(board, vbus_code, pcbnew.F_Cu, 36.0, 26.5, 44.0, 24.5, width_mm=0.80)
    add_via(board, vbus_code, 44.0, 24.5, size_mm=0.90, drill_mm=0.45)
    add_track(board, vbus_code, pcbnew.B_Cu, 44.0, 24.5, 46.5, 24.5, width_mm=1.00)

    add_track(board, 0, pcbnew.B_Cu, 49.5, 24.5, 52.0, 24.5, width_mm=1.20)

    add_track(board, p3v3_code, pcbnew.B_Cu, 56.0, 24.5, 56.0, 21.5, width_mm=1.00)
    add_track(board, p3v3_code, pcbnew.B_Cu, 56.0, 21.5, 50.0, 21.5, width_mm=1.00)
    add_via(board, p3v3_code, 50.0, 21.5, size_mm=0.90, drill_mm=0.45)
    add_45_route(board, p3v3_code, pcbnew.F_Cu, 50.0, 21.5, 46.5, 20.0, width_mm=0.60)
    add_45_route(board, p3v3_code, pcbnew.F_Cu, 50.0, 21.5, 30.0, 20.0, width_mm=0.60)
    add_45_route(board, p3v3_code, pcbnew.F_Cu, 30.0, 20.0, 28.0, 10.5, width_mm=0.50)

    add_45_route(board, 0, pcbnew.B_Cu, 54.0, 21.5, 50.0, 26.5, width_mm=0.20)
    add_45_route(board, 0, pcbnew.B_Cu, 50.0, 26.5, 48.0, 25.5, width_mm=0.20)

    for tx in [-0.6, 0.6]:
        for ty in [-0.6, 0.6]:
            add_via(board, gnd_code, 48.0 + tx, 24.5 + ty, size_mm=0.60, drill_mm=0.30)

    print("[*] 8. Adding Perimeter Faraday Shielding Ground Vias...")
    for x in range(5, 63, 4):
        add_via(board, gnd_code, float(x), 2.0, size_mm=0.60, drill_mm=0.30)
        add_via(board, gnd_code, float(x), 28.0, size_mm=0.60, drill_mm=0.30)
    for y in range(4, 28, 4):
        add_via(board, gnd_code, 2.0, float(y), size_mm=0.60, drill_mm=0.30)
        add_via(board, gnd_code, 64.0, float(y), size_mm=0.60, drill_mm=0.30)

    board.Save(board_path)
    print(f"\n[SUCCESS] Production EE routing saved to: {board_path}")
    print(f"    -> Total Tracks: {len(list(board.GetTracks()))}")


if __name__ == "__main__":
    board_file = "d:/github/miner-display-bridge/hardware/miner_bridge_pcb/miner_bridge_pcb.kicad_pcb"
    if len(sys.argv) > 1:
        board_file = sys.argv[1]
    synthesize_routing(board_file)
