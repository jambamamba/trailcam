#!/usr/bin/env python3
"""Generate the wapiti KiCad footprint library (wapiti.pretty).

Same approach as lugtrax (modeled on /repos/lora/hardware custom
footprints): through-hole module footprints with silkscreen pin names,
courtyard, and pad grids computed from the datasheet dimensions of the
wapiti BOM (project-plan §4/§5). Pad maps for multi-row LCC/BGA parts
are illustrative reductions - marked as such in each descr.

Footprints (single file each, KiCad 6+ s-expression format):
  Pack_Conn_5p           - smart-pack 5-pin connector (VPK, ID, TH, SCL, GND)
  Fuse_1206              - 1206 PTC resettable fuse (2-pad chip)
  Diode_SMA              - SS54 5 A schottky, DO-214AC (SMA) power OR-ing
  TVS_SOD-323            - SOD-323 TVS (VSYS clamp)
  R_0603 / C_0603        - 0603 chip two-pads
  L_1210                 - buck inductor 1210
  CP_Elec_6.3x7.7        - SMD electrolytic (5 F supercap ride-through)
  JST_PH_2p              - solar panel input 2-pin
  SMA_EdgeMount          - user-replaceable LTE antenna (edge SMA)
  SOT-23-5               - load switches EN_CAM / EN_MODEM / solar interlock
  SOT-23                 - IR-array MOSFET low-side switches
  SOT-23-8               - BQ27441 fuel gauge
  SOIC-8                 - 3.8 V buck
  EG915U                 - Quectel EG915U LTE Cat-1bis + GNSS LCC module
  NanoSIM_Push           - nano-SIM push-push (eSIM)
  ESP32-C6-WROOM-1       - C6 wake supervisor module, 19 castellated pads
  LGA-12_2x2mm           - LIS2DW12 accelerometer
  USB_C_Receptacle_16P   - USB-C 16-pin vertical SMD
  PinHeader_2x03_P2.54mm - 2x03 through-hole programming header
  Button_4x4mm           - 4x4 mm SMD tact switch (reset)
  Antenna_UMWiSE_1.6mm   - GNSS patch antenna pad (under lid RF membrane)
  SSC377Q_QFN            - camera SoC QFN 9x9 mm
  IMX415_Module          - 8.4 MP sensor module with lens (FPC stub)
  eMMC_153               - JEDEC 153-ball eMMC BGA 11.5x13 mm
  microSD_Push           - microSD push-push slot
  LCD_2in_FPC            - 2.0 in SPI TFT, FPC tail
  IR_Array_30x10         - IR LED array board 30x10 mm (940/850 nm)
  PIR_Dome               - AS312-class PIR with dome
  Radar_LD2410           - HLK-LD2410 24 GHz module (value SKU DNP)
"""

import os


def fp_header(name, descr, tags, attrs=("smd",)):
    return [
        '(footprint "%s" (version 20221018) (generator wapiti)' % name,
        '  (layer "F.Cu")',
        '  (descr "%s")' % descr,
        '  (tags "%s")' % tags,
        '  (attr %s)' % " ".join(attrs),
    ]


def ref_val(name, x, y):
    return [
        '  (fp_text reference "REF**" (at %s %s) (layer "F.SilkS")'
        % (x, y),
        "      (effects (font (size 1 1) (thickness 0.15)))",
        "  )",
        '  (fp_text value "%s" (at %s %s) (layer "F.Fab")' % (name, x, y + 3),
        "      (effects (font (size 1 1) (thickness 0.15)))",
        "  )",
    ]


def pad(num, shape, x, y, w, h, layers, drill=None, rot=0):
    d = " (drill %s)" % drill if drill else ""
    r = " (at %s %s %s)" % (x, y, rot) if rot else " (at %s %s)" % (x, y)
    return '  (pad "%s" %s %s (size %s %s)%s (layers %s))' % (
        num, shape, r, w, h, d, layers)


def rect_line(x1, y1, x2, y2, layer, width=0.12):
    return [
        '  (fp_line (start %s %s) (end %s %s)' % (x1, y1, x2, y2),
        "    (stroke (width %s) (type solid)) (layer %s))" % (width, layer),
    ]


def circle(center, end, layer, width=0.12):
    return [
        '  (fp_circle (center %s %s) (end %s %s)' % (center[0], center[1], end[0], end[1]),
        "    (stroke (width %s) (type solid)) (layer %s))" % (width, layer),
    ]


def fp_text_user(text, x, y, layer="F.Fab", size=0.8):
    return [
        '  (fp_text user "%s" (at %s %s) (layer "%s")' % (text, x, y, layer),
        "    (effects (font (size %s %s) (thickness 0.1))))" % (size, size),
    ]


def chip_fp(name, descr, tags, pads, body_w, body_h, pad_layers='"*.Cu" "*.Mask"'):
    """Simple 2-pad chip footprint. pads: [(num, x, y, w, h)]"""
    out = fp_header(name, descr, tags)
    out += ref_val(name, 0, -body_h / 2 - 1)
    # silk outline around the body
    out += rect_line(-body_w / 2 - 0.3, -body_h / 2 - 0.3,
                     body_w / 2 + 0.3, -body_h / 2 - 0.3, "F.SilkS")
    out += rect_line(-body_w / 2 - 0.3, body_h / 2 + 0.3,
                     body_w / 2 + 0.3, body_h / 2 + 0.3, "F.SilkS")
    # courtyard
    cx = max(abs(p[1]) + p[3] / 2 for p in pads) + 0.25
    cy = max(abs(p[2]) + p[4] / 2 for p in pads) + 0.25
    out += rect_line(-cx, -cy, cx, cy, "F.CrtYd", 0.05)
    for num, x, y, w, h in pads:
        out.append(pad(num, "rect" if num == "1" else "roundrect", x, y, w, h, pad_layers))
    out.append(")")
    return out


def gen_chip_families():
    fams = {}
    # 0603 passives
    for name, kind in (("R_0603", "Resistor"), ("C_0603", "Capacitor")):
        fams[name] = chip_fp(name, "%s 0603" % kind, kind.lower() + " 0603",
                             [("1", -0.75, 0, 0.9, 0.95), ("2", 0.75, 0, 0.9, 0.95)],
                             1.6, 0.8)
    # 1206 PTC fuse
    fams["Fuse_1206"] = chip_fp("Fuse_1206", "PTC resettable fuse 1206", "fuse ptc 1206",
                                [("1", -1.5, 0, 1.1, 1.6), ("2", 1.5, 0, 1.1, 1.6)],
                                3.2, 1.6)
    # SS54 5 A schottky, DO-214AC (SMA) - power OR-ing D1/D3/D4
    fams["Diode_SMA"] = chip_fp(
        "Diode_SMA", "SS54 5A schottky DO-214AC (SMA)", "diode schottky sma ss54",
        [("1", -1.8, 0, 1.8, 2.3), ("2", 1.8, 0, 1.8, 2.3)],
        4.3, 2.6)
    # SOD-323 TVS
    fams["TVS_SOD-323"] = chip_fp("TVS_SOD-323", "TVS diode SOD-323", "tvs diode sod323",
                                  [("1", -1.1, 0, 0.9, 1.0), ("2", 1.1, 0, 0.9, 1.0)],
                                  2.5, 1.3)
    # buck inductor 1210
    fams["L_1210"] = chip_fp("L_1210", "Power inductor 1210", "inductor 1210",
                             [("1", -1.5, 0, 1.1, 2.4), ("2", 1.5, 0, 1.1, 2.4)],
                             3.2, 2.5)
    return fams


def gen_cp_elec():
    name = "CP_Elec_6.3x7.7"
    out = fp_header(name, "SMD electrolytic 6.3x7.7mm (5F supercap ride-through)",
                    "capacitor electrolytic smd supercap")
    out += ref_val(name, 0, -6)
    out += circle((0, 0), (3.3, 0), "F.SilkS")
    out += circle((0, 0), (3.55, 0), "F.CrtYd", 0.05)
    out.append(pad("1", "rect", -2.4, 0, 1.6, 2.6, '"*.Cu" "*.Mask"'))
    out.append(pad("2", "roundrect", 2.4, 0, 1.6, 2.6, '"*.Cu" "*.Mask"'))
    out.append(")")
    return name, out


def gen_pack_conn():
    """Smart-pack 5-pin: VPK + pack-ID + thermistor + fuel-gauge SCL + GND.

    JST-PH-style 2.0 mm pitch through-hole header; keyed pin 1 = VPK.
    """
    name = "Pack_Conn_5p"
    out = fp_header(name, "Smart pack connector 5-pin 2.0mm (VPK ID TH SCL GND)",
                    "battery pack connector jst-ph 5p", attrs=("through_hole",))
    out += ref_val(name, 0, -6)
    n = 1
    for i in range(5):
        x = -4.0 + i * 2.0
        out.append(pad(str(n), "circle", x, 0, 1.4, 1.4, '"*.Cu" "*.Mask"', drill=0.7))
        n += 1
    # shroud outline
    out += rect_line(-6.2, -2.1, 6.2, 2.1, "F.SilkS")
    out += rect_line(-6.5, -2.4, 6.5, 2.4, "F.CrtYd", 0.05)
    out += fp_text_user("+", -4.0, -3.4, "F.SilkS", 1.5)
    out.append(")")
    return name, out


def gen_jst_ph_2p():
    """Solar panel input, 2-pin 2.0 mm pitch."""
    name = "JST_PH_2p"
    out = fp_header(name, "JST-PH 2-pin solar input 2.0mm", "jst ph solar 2p",
                    attrs=("through_hole",))
    out += ref_val(name, 0, -5)
    out.append(pad("1", "circle", -1.0, 0, 1.4, 1.4, '"*.Cu" "*.Mask"', drill=0.7))
    out.append(pad("2", "circle", 1.0, 0, 1.4, 1.4, '"*.Cu" "*.Mask"', drill=0.7))
    out += rect_line(-3.2, -2.1, 3.2, 2.1, "F.SilkS")
    out += rect_line(-3.5, -2.4, 3.5, 2.4, "F.CrtYd", 0.05)
    out.append(")")
    return name, out


def gen_sma_edge():
    """Edge-mount SMA receptacle: user-replaceable LTE antenna (CAM-14)."""
    name = "SMA_EdgeMount"
    out = fp_header(name, "SMA edge-mount receptacle (LTE antenna, user-replaceable)",
                    "sma antenna edge lte")
    out += ref_val(name, 0, -6)
    # center signal pad reaching the board edge
    out.append(pad("1", "rect", -1.6, 0, 3.2, 2.2, '"*.Cu" "*.Mask"'))
    # ground petals
    for y in (-3.0, 3.0):
        out.append(pad("2", "rect", -1.6, y, 3.2, 2.0, '"*.Cu" "*.Mask"'))
    out += rect_line(-4.0, -5.0, 2.6, 5.0, "F.SilkS")
    out += rect_line(-4.3, -5.3, 2.9, 5.3, "F.CrtYd", 0.05)
    out += fp_text_user("board edge ->", 4.6, 0, "F.Fab")
    out.append(")")
    return name, out

def gen_sot23_5():
    name = "SOT-23-5"
    out = fp_header(name, "SOT-23-5 load switch (EN_CAM/EN_MODEM/solar interlock)",
                    "load switch sot23-5")
    out += ref_val(name, 0, -3.5)
    xs = [-0.95, 0, 0.95]
    for i, x in enumerate(xs, 1):
        out.append(pad(str(i), "roundrect", x, 1.15, 0.6, 1.0, '"*.Cu" "*.Mask"'))
    for i, x in enumerate([-0.95, 0.95], 4):
        out.append(pad(str(i), "roundrect", x, -1.15, 0.6, 1.0, '"*.Cu" "*.Mask"'))
    out += rect_line(-1.6, -1.6, 1.6, 1.6, "F.CrtYd", 0.05)
    out += rect_line(-1.45, 1.6, 1.45, 1.6, "F.SilkS")
    out.append(")")
    return name, out


def gen_sot23():
    """SOT-23 N-MOSFET (IR-array low-side switches Q1/Q2)."""
    name = "SOT-23"
    out = fp_header(name, "SOT-23 N-MOSFET low-side IR switch", "mosfet sot23")
    out += ref_val(name, 0, -3.5)
    out.append(pad("1", "roundrect", -0.95, 1.1, 0.6, 1.0, '"*.Cu" "*.Mask"'))
    out.append(pad("2", "roundrect", 0.95, 1.1, 0.6, 1.0, '"*.Cu" "*.Mask"'))
    out.append(pad("3", "roundrect", 0, -1.1, 0.6, 1.0, '"*.Cu" "*.Mask"'))
    out += rect_line(-1.6, -1.6, 1.6, 1.6, "F.CrtYd", 0.05)
    out += rect_line(-1.45, 1.6, 1.45, 1.6, "F.SilkS")
    out.append(")")
    return name, out


def gen_sot23_8():
    """SOT-23-8 fuel gauge (BQ27441)."""
    name = "SOT-23-8"
    out = fp_header(name, "SOT-23-8 fuel gauge BQ27441", "fuel gauge bq27441 sot23-8")
    out += ref_val(name, 0, -3.5)
    for i in range(4):
        out.append(pad(str(i + 1), "roundrect", -0.975 + i * 0.65, 1.15,
                       0.45, 0.9, '"*.Cu" "*.Mask"'))
        out.append(pad(str(8 - i), "roundrect", -0.975 + i * 0.65, -1.15,
                       0.45, 0.9, '"*.Cu" "*.Mask"'))
    out += rect_line(-1.7, -1.7, 1.7, 1.7, "F.CrtYd", 0.05)
    out += rect_line(-1.5, 1.7, 1.5, 1.7, "F.SilkS")
    out.append(")")
    return name, out


def gen_soic8():
    """SOIC-8 buck (3.8 V V_SYS)."""
    name = "SOIC-8"
    out = fp_header(name, "SOIC-8 buck converter", "buck regulator soic8")
    out += ref_val(name, 0, -4.5)
    # pads along left/right edges, 1.27 pitch
    for i in range(4):
        out.append(pad(str(i + 1), "roundrect", -1.905, 2.7 - i * 1.27,
                       1.5, 0.6, '"*.Cu" "*.Mask"'))
        out.append(pad(str(8 - i), "roundrect", 1.905, 2.7 - i * 1.27,
                       1.5, 0.6, '"*.Cu" "*.Mask"'))
    out += rect_line(-2.95, -2.75, 2.95, 2.75, "F.CrtYd", 0.05)
    out += rect_line(-1.95, 3.4, 1.95, 3.4, "F.SilkS")
    out += rect_line(-1.95, -3.4, 1.95, -3.4, "F.SilkS")
    out += circle((-2.4, 3.2), (-2.0, 3.2), "F.SilkS")
    out.append(")")
    return name, out


def gen_eg915u():
    """Quectel EG915U LTE Cat-1bis + GNSS LCC module ~17.7 x 16.9 mm.
    Castellated edge pads, illustrative numbering (datasheet pin map at layout).
    """
    name = "EG915U"
    W, H = 17.7, 16.9
    pw, ph = 1.6, 2.0
    out = fp_header(name, "Quectel EG915U LTE Cat-1bis + GNSS LCC 17.7x16.9mm (illustrative)",
                    "quectel eg915 lte cat1bis gnss lcc")
    out += ref_val(name, 0, -H / 2 - 2)
    n = 1
    for i in range(11):  # left column
        y = H / 2 - 1.0 - i * (H - 2.0) / 10
        out.append(pad(str(n), "rect", -W / 2 + 0.8, y, pw, 1.0, '"*.Cu"'))
        n += 1
    for i in range(8):   # bottom row
        x = -W / 2 + 2.5 + i * (W - 5.0) / 7
        out.append(pad(str(n), "rect", x, -H / 2 + 0.8, 1.0, pw, '"*.Cu"'))
        n += 1
    for i in range(11):  # right column
        y = -H / 2 + 1.0 + i * (H - 2.0) / 10
        out.append(pad(str(n), "rect", W / 2 - 0.8, y, pw, 1.0, '"*.Cu"'))
        n += 1
    for i in range(8):   # top row
        x = -W / 2 + 2.5 + i * (W - 5.0) / 7
        out.append(pad(str(n), "rect", x, H / 2 - 0.8, 1.0, pw, '"*.Cu"'))
        n += 1
    out += rect_line(-W / 2 - 0.4, -H / 2, -W / 2 - 0.4, H / 2, "F.SilkS")
    out += rect_line(W / 2 + 0.4, -H / 2, W / 2 + 0.4, H / 2, "F.SilkS")
    out += rect_line(-W / 2, -H / 2 - 0.4, W / 2, -H / 2 - 0.4, "F.SilkS")
    out += rect_line(-W / 2, H / 2 + 0.4, W / 2, H / 2 + 0.4, "F.SilkS")
    out += rect_line(-W / 2 - 0.65, -H / 2 - 0.65, W / 2 + 0.65, H / 2 + 0.65,
                     "F.CrtYd", 0.05)
    out += fp_text_user("GNSS ant region (keep-out)", 0, H / 2 + 2.2)
    out.append(")")
    return name, out


def gen_esp32c6():
    """ESP32-C6-WROOM-1 18 x 25.5 mm module. 19 castellated pads numbered to
    match the schematic symbol: left 1-8, bottom 9-11, right 12-19.
    Antenna keep-out at the top edge.
    """
    name = "ESP32-C6-WROOM-1"
    W, H = 18.0, 25.5
    out = fp_header(name, "ESP32-C6-WROOM-1 module 18x25.5mm (wake supervisor)",
                    "esp32 c6 wroom module ble wifi")
    out += ref_val(name, 0, -H / 2 - 2)
    n = 1
    for i in range(8):   # left column 1-8
        y = H / 2 - 5.0 - i * (H - 8.0) / 7
        out.append(pad(str(n), "rect", -W / 2 + 1.0, y, 1.8, 1.0, '"*.Cu" "*.Mask"'))
        n += 1
    for i in range(3):   # bottom row 9-11
        x = -3.0 + i * 3.0
        out.append(pad(str(n), "rect", x, -H / 2 + 1.0, 1.0, 1.8, '"*.Cu" "*.Mask"'))
        n += 1
    for i in range(8):   # right column 12-19
        y = -H / 2 + 5.0 + i * (H - 8.0) / 7
        out.append(pad(str(n), "rect", W / 2 - 1.0, y, 1.8, 1.0, '"*.Cu" "*.Mask"'))
        n += 1
    out += rect_line(-W / 2, H / 2 - 5.0, W / 2, H / 2 - 0.5, "F.Fab", 0.05)
    out += fp_text_user("ANT KEEP-OUT", 0, H / 2 - 2.7)
    out += rect_line(-W / 2 - 0.4, -H / 2 - 0.4, W / 2 + 0.4, H / 2 + 0.4,
                     "F.CrtYd", 0.05)
    out.append(")")
    return name, out


def gen_nano_sim():
    name = "NanoSIM_Push"
    pads = [
        ("1", -2.6, 1.75, 1.4, 1.6),   # VDD (C1)
        ("2", 0, 1.75, 1.4, 1.6),      # RST (C2)
        ("3", 2.6, 1.75, 1.4, 1.6),    # CLK (C3)
        ("4", -2.6, -1.75, 1.4, 1.6),  # GND (C5)
        ("6", 0, -1.75, 1.4, 1.6),     # DATA (C7)
        ("5", 2.6, -1.75, 1.4, 1.6),   # VPP (C6, nc for eSIM)
    ]
    out = fp_header(name, "nano-SIM push-push 6-pad (eSIM)", "sim nano esim")
    out += ref_val(name, 0, -5)
    for num, x, y, w, h in pads:
        out.append(pad(num, "roundrect", x, y, w, h, '"*.Cu" "*.Mask"'))
    out += rect_line(-6, -3, 6, 3, "F.CrtYd", 0.05)
    out.append(")")
    return name, out


def gen_lga12():
    name = "LGA-12_2x2mm"
    out = fp_header(name, "ST LIS2DW12 LGA-12 2x2mm", "accelerometer lga12 lis2dw12")
    out += ref_val(name, 0, -2.8)
    n = 1
    for row in [0.65, 0]:
        for i in range(4):
            x = -0.75 + i * 0.5
            out.append(pad(str(n), "roundrect", x, row, 0.3, 0.35, '"*.Cu"'))
            n += 1
    for i in range(4):
        x = 0.75 - i * 0.5
        out.append(pad(str(n), "roundrect", x, -0.65, 0.3, 0.35, '"*.Cu"'))
        n += 1
    out += rect_line(-1.25, -1.25, 1.25, 1.25, "F.CrtYd", 0.05)
    out.append(")")
    return name, out


def gen_usb_c():
    name = "USB_C_Receptacle_16P"
    pads = []
    for i, x in enumerate([-3.35, -2.25, 2.25, 3.35]):
        pads.append(("S%d" % (i + 1), x, 3.2, 1.0, 1.6))
    for i in range(6):
        pads.append((str(i + 1), -1.75 + i * 0.7, 0, 0.5, 2.6))
    out = fp_header(name, "USB-C 2.0 receptacle (service: modem fw + C6 flashing)",
                    "usb type-c 16p")
    out += ref_val(name, 0, -6)
    for num, x, y, w, h in pads:
        out.append(pad(num, "roundrect", x, y, w, h, '"*.Cu" "*.Mask"'))
    out += rect_line(-4.5, -2.5, 4.5, 4.5, "F.CrtYd", 0.05)
    out.append(")")
    return name, out


def gen_pinheader():
    name = "PinHeader_2x03_P2.54mm"
    out = fp_header(name, "2x03 through-hole pin header 2.54mm (factory programming)",
                    "pin header 2x03", attrs=("through_hole",))
    out += ref_val(name, 0, -5)
    n = 1
    for row in [1.27, -1.27]:
        for col in [-2.54, 0, 2.54]:
            out.append(pad(str(n), "circle", col, row, 1.7, 1.7,
                           '"*.Cu" "*.Mask"', drill=1.0))
            n += 1
    out += rect_line(-3.8, -2.5, 3.8, 2.5, "F.CrtYd", 0.05)
    out.append(")")
    return name, out


def gen_button():
    name = "Button_4x4mm"
    pads = [("1", -2.25, 1.0, 1.3, 1.2), ("2", 2.25, 1.0, 1.3, 1.2),
            ("3", -2.25, -1.0, 1.3, 1.2), ("4", 2.25, -1.0, 1.3, 1.2)]
    out = fp_header(name, "SMD tact switch 4x4mm (reset)", "button tact 4x4")
    out += ref_val(name, 0, -3.5)
    for num, x, y, w, h in pads:
        out.append(pad(num, "roundrect", x, y, w, h, '"*.Cu" "*.Mask"'))
    out += rect_line(-2.6, -1.9, 2.6, 1.9, "F.CrtYd", 0.05)
    out.append(")")
    return name, out


def gen_antenna():
    name = "Antenna_UMWiSE_1.6mm"
    out = fp_header(name, "GNSS patch antenna pad 1.6mm feed (under lid RF membrane)",
                    "antenna gnss patch pcb")
    out += ref_val(name, 0, -4)
    out.append(pad("1", "rect", 0, 0, 1.6, 3.0, '"*.Cu" "*.Mask"'))
    out += rect_line(-2.5, -2.5, 2.5, 2.5, "F.CrtYd", 0.05)
    out += fp_text_user("RF MEMBRANE KEEP-OUT", 0, 3.5)
    out.append(")")
    return name, out

def gen_soc_qfn():
    """SSC377Q-class camera SoC, QFN 9x9 mm, 0.4 mm edge pads (illustrative
    22/side) + 7x7 thermal pad. Pad 1 marker bottom-left.
    """
    name = "SSC377Q_QFN"
    W = 9.0
    out = fp_header(name, "SSC377Q camera SoC QFN 9x9mm 0.4mm pads (illustrative)",
                    "soc qfn camera ssc377")
    out += ref_val(name, 0, -7)
    n = 1
    edge = W / 2 - 0.4
    for i in range(22):  # left 1-22
        y = -edge + 0.6 + i * (2 * edge - 1.2) / 21
        out.append(pad(str(n), "rect", -edge, y, 0.8, 0.4, '"*.Cu"'))
        n += 1
    for i in range(22):  # bottom 23-44
        x = -edge + 0.6 + i * (2 * edge - 1.2) / 21
        out.append(pad(str(n), "rect", x, -edge, 0.4, 0.8, '"*.Cu"'))
        n += 1
    for i in range(22):  # right 45-66
        y = edge - 0.6 - i * (2 * edge - 1.2) / 21
        out.append(pad(str(n), "rect", edge, y, 0.8, 0.4, '"*.Cu"'))
        n += 1
    for i in range(22):  # top 67-88
        x = edge - 0.6 - i * (2 * edge - 1.2) / 21
        out.append(pad(str(n), "rect", x, edge, 0.4, 0.8, '"*.Cu"'))
        n += 1
    out.append(pad("89", "rect", 0, 0, 6.5, 6.5, '"*.Cu"'))  # thermal
    out += rect_line(-W / 2 - 0.4, -W / 2 - 0.4, W / 2 + 0.4, W / 2 + 0.4,
                     "F.CrtYd", 0.05)
    out += circle((-W / 2 - 0.6, -W / 2 - 0.6), (-W / 2 - 0.2, -W / 2 - 0.6),
                  "F.SilkS")
    out.append(")")
    return name, out


def gen_imx415_module():
    """IMX415 8.4 MP sensor module with lens: 22x22 mm body, lens barrel dia
    ~14 mm, 8-pad 0.5 mm FPC tail at the bottom. Lens faces the front panel
    (chassis lens port; keep-out note on F.Fab).
    """
    name = "IMX415_Module"
    W = 22.0
    out = fp_header(name, "IMX415 8.4MP sensor module + lens, 22x22mm, 8-pad FPC",
                    "sensor camera imx415 module fpc")
    out += ref_val(name, 0, -13)
    for i in range(8):
        x = -1.75 + i * 0.5
        out.append(pad(str(i + 1), "rect", x, -W / 2 - 0.8, 0.3, 1.6, '"*.Cu"'))
    out += rect_line(-W / 2, -W / 2, W / 2, W / 2, "F.SilkS")
    out += circle((0, 0), (7.0, 0), "F.SilkS")
    out += rect_line(-W / 2 - 0.4, -W / 2 - 1.6, W / 2 + 0.4, W / 2 + 0.4,
                     "F.CrtYd", 0.05)
    out += fp_text_user("LENS -> front panel port", 0, W / 2 + 2.0)
    out.append(")")
    return name, out

def gen_emmc():
    """JEDEC 153-ball eMMC BGA 11.5x13 mm. Illustrative full A1..K15 ball
    grid (0.8 mm pitch); consult the datasheet ball map at layout.
    """
    name = "eMMC_153"
    W, H = 11.5, 13.0
    rows, cols = 15, 11
    out = fp_header(name, "eMMC 153-ball BGA 11.5x13mm (illustrative ball map)",
                    "emmc bga 153 storage")
    out += ref_val(name, 0, -9)
    letters = "ABCDEFGHIJK"
    for r in range(rows):
        y = (rows - 1) * 0.4 - r * 0.8
        for c in range(cols):
            out.append(pad("%s%d" % (letters[c], r + 1), "circle",
                           (cols - 1) * 0.4 - c * 0.8, y, 0.35, 0.35, '"*.Cu"'))
    out += rect_line(-W / 2 - 0.3, -H / 2 - 0.3, W / 2 + 0.3, H / 2 + 0.3,
                     "F.CrtYd", 0.05)
    out += circle((-W / 2 - 0.5, -H / 2 - 0.5), (-W / 2 - 0.1, -H / 2 - 0.5),
                  "F.SilkS")
    out.append(")")
    return name, out


def gen_microsd():
    """microSD push-push slot ~15x14.5 mm: 8 contact pads along the top edge
    (illustrative) + 2 shell tabs. Symbol uses pads 1-6.
    """
    name = "microSD_Push"
    out = fp_header(name, "microSD push-push slot 15x14.5mm (overflow recording)",
                    "microsd slot push-push storage")
    out += ref_val(name, 0, -10)
    labels = ["1", "2", "3", "4", "5", "6", "7", "8"]
    for i, lab in enumerate(labels):
        out.append(pad(lab, "roundrect", -3.85 + i * 1.1, -6.0, 0.7, 1.6,
                       '"*.Cu" "*.Mask"'))
    for i, x in enumerate((-6.8, 6.8)):
        out.append(pad("S%d" % (i + 1), "rect", x, 3.5, 1.6, 2.4,
                       '"*.Cu" "*.Mask"'))
    out += rect_line(-7.5, -7.25, 7.5, 7.25, "F.SilkS")
    out += rect_line(-7.8, -7.55, 7.8, 7.55, "F.CrtYd", 0.05)
    out += fp_text_user("card ejection -> rear edge", 0, 9.0)
    out.append(")")
    return name, out


def gen_lcd_fpc():
    """2.0 in SPI TFT: glass ~38x25 mm, 14-pad 0.5 mm FPC tail at the bottom;
    schematic symbol uses pads 1-7.
    """
    name = "LCD_2in_FPC"
    W, H = 38.0, 25.0
    out = fp_header(name, "2.0in SPI TFT 38x25mm glass, 14-pad 0.5mm FPC (uses 1-7)",
                    "lcd tft spi 2in fpc display")
    out += ref_val(name, 0, -16)
    for i in range(14):
        x = -3.25 + i * 0.5
        out.append(pad(str(i + 1), "rect", x, -H / 2 - 0.8, 0.3, 1.6, '"*.Cu"'))
    out += rect_line(-W / 2, -H / 2, W / 2, H / 2, "F.SilkS")
    out += rect_line(-W / 2 - 0.4, -H / 2 - 1.6, W / 2 + 0.4, H / 2 + 0.4,
                     "F.CrtYd", 0.05)
    out += fp_text_user("active area -> status window", 0, H / 2 + 2.0)
    out.append(")")
    return name, out

def gen_ir_array():
    """IR LED array board 30x10 mm (24 emitters): 2 solder pads at the rear
    edge, emissive face toward the front panel.
    """
    name = "IR_Array_30x10"
    W, H = 30.0, 10.0
    out = fp_header(name, "IR LED array 30x10mm x24 emitters (940nm no-glow / 850nm)",
                    "ir led array 940nm 850nm illuminator")
    out += ref_val(name, 0, -8)
    out.append(pad("1", "rect", -11.5, 0, 2.0, 3.0, '"*.Cu" "*.Mask"'))
    out.append(pad("2", "roundrect", 11.5, 0, 2.0, 3.0, '"*.Cu" "*.Mask"'))
    out += rect_line(-W / 2, -H / 2, W / 2, H / 2, "F.SilkS")
    out += rect_line(-W / 2 - 0.4, -H / 2 - 0.4, W / 2 + 0.4, H / 2 + 0.4,
                     "F.CrtYd", 0.05)
    for x in (-9, -6, -3, 0, 3, 6, 9):
        out += circle((x, 0), (x + 1.2, 0), "F.Fab", 0.05)
    out += fp_text_user("emitters -> front panel", 0, H / 2 + 2.0)
    out.append(")")
    return name, out


def gen_pir_dome():
    """AS312-class digital PIR: 3 through-hole pins + white fresnel dome
    dia ~11 mm looking through the chassis PIR window.
    """
    name = "PIR_Dome"
    out = fp_header(name, "AS312 digital PIR, dome dia 11mm, 3-pin TH",
                    "pir as312 motion sensor dome", attrs=("through_hole",))
    out += ref_val(name, 0, -8)
    out.append(pad("1", "circle", -2.0, 0, 1.4, 1.4, '"*.Cu" "*.Mask"', drill=0.8))
    out.append(pad("2", "circle", 0, 0, 1.4, 1.4, '"*.Cu" "*.Mask"', drill=0.8))
    out.append(pad("3", "circle", 2.0, 0, 1.4, 1.4, '"*.Cu" "*.Mask"', drill=0.8))
    out += circle((0, 0), (5.5, 0), "F.SilkS")
    out += circle((0, 0), (5.8, 0), "F.CrtYd", 0.05)
    out += fp_text_user("dome -> PIR window", 0, 7.0)
    out.append(")")
    return name, out


def gen_radar():
    """HLK-LD2410 24 GHz module ~22x16.5 mm, 5-pin 2.54 mm header
    (5V GND TX RX OUT; symbol uses 1-4). Value SKU: DNP candidate.
    """
    name = "Radar_LD2410"
    W, H = 22.0, 16.5
    out = fp_header(name, "HLK-LD2410 24GHz radar module 22x16.5mm (value SKU DNP)",
                    "radar 24ghz ld2410 mmwave DNP")
    out += ref_val(name, 0, -11)
    labels = ["1", "2", "3", "4", "5"]
    for i, lab in enumerate(labels):
        out.append(pad(lab, "circle", -5.08 + i * 2.54, -H / 2 + 2.0, 1.7, 1.7,
                       '"*.Cu" "*.Mask"', drill=1.0))
    out += rect_line(-W / 2, -H / 2, W / 2, H / 2, "F.SilkS")
    out += rect_line(-W / 2 - 0.4, -H / 2 - 0.4, W / 2 + 0.4, H / 2 + 0.4,
                     "F.CrtYd", 0.05)
    out += rect_line(-W / 2 + 1, H / 2 - 7, W / 2 - 1, H / 2 - 1, "F.Fab", 0.05)
    out += fp_text_user("radar patch -> front (keep-out)", 0, H / 2 + 2.0)
    out += fp_text_user("DNP (wapiti-lite)", 0, -H / 2 - 2.0, "F.SilkS")
    out.append(")")
    return name, out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    libdir = os.path.join(here, "wapiti.pretty")
    os.makedirs(libdir, exist_ok=True)

    fps = {}
    fps.update(gen_chip_families())
    fps.update([gen_cp_elec(), gen_pack_conn(), gen_jst_ph_2p(),
                gen_sma_edge(), gen_sot23_5(), gen_sot23(), gen_sot23_8(),
                gen_soic8(), gen_eg915u(), gen_esp32c6(), gen_nano_sim(),
                gen_lga12(), gen_usb_c(), gen_pinheader(), gen_button(),
                gen_antenna(), gen_soc_qfn(), gen_imx415_module(),
                gen_emmc(), gen_microsd(), gen_lcd_fpc(), gen_ir_array(),
                gen_pir_dome(), gen_radar()])

    for name, lines in fps.items():
        path = os.path.join(libdir, "%s.kicad_mod" % name)
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
        print("wrote %s" % path)
    print("done: %d footprints" % len(fps))


if __name__ == "__main__":
    main()

