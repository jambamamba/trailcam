#!/usr/bin/env python3
"""Generate wapiti.kicad_pcb - wapiti reference board, 100 x 65 mm.

Same approach as lugtrax: a minimal but valid KiCad board with footprints
instantiated from wapiti.pretty (paths only; KiCad resolves the library at
load), board outline, F.Cu ground plane, and mounting holes. Zone keep-outs
are marked on F.Fab (antenna, front-panel optics).

Refdes prefixes disambiguate the per-sheet schematic numbering:
  P* = power sheet, R* = radio, C* = cam, M* = mcu (MD3 = status LED).
Front panel = top edge (y=0): lens, IR arrays, PIR dome, radar patch.
Antenna corner = top-right: SMA (RJ2) + GNSS patch (ANT2) under the lid
RF membrane (chassis keep-out, see chassis/gen_chassis_stl.py).

Usage: python3 gen_pcb.py
"""

import os


def u():
    import uuid
    return str(uuid.uuid4())


BOARD_W, BOARD_H = 100.0, 65.0

# (ref, footprint, x, y, rot) - layout checked for courtyard overlap
PLACEMENTS = [
    # --- POWER (left): packs, supercap, protection, buck, rail switches
    ("BT1", "wapiti:Pack_Conn_5p", 7, 18, 0),
    ("BT2", "wapiti:Pack_Conn_5p", 7, 30, 0),
    ("BT3", "wapiti:Pack_Conn_5p", 7, 42, 0),
    ("C1", "wapiti:CP_Elec_6.3x7.7", 40, 50, 0),
    ("F1", "wapiti:Fuse_1206", 41, 34, 0),
    ("D1", "wapiti:Diode_SMA", 51, 34, 0),
    ("D2", "wapiti:TVS_SOD-323", 55, 34, 0),
    ("D3", "wapiti:Diode_SMA", 61, 30, 0),
    ("D4", "wapiti:Diode_SMA", 67, 30, 0),
    ("PJ1", "wapiti:JST_PH_2p", 4, 48, 0),
    ("PU1", "wapiti:SOIC-8", 42, 20, 0),
    ("L1", "wapiti:L_1210", 52, 30, 0),
    ("C2", "wapiti:C_0603", 48, 30, 0),
    ("PU2", "wapiti:SOT-23-5", 54, 26, 0),
    ("PU3", "wapiti:SOT-23-5", 58, 26, 0),
    ("PU4", "wapiti:SOT-23-5", 50, 26, 0),
    ("R8", "wapiti:R_0603", 46, 26, 0),
    ("R9", "wapiti:R_0603", 48, 20, 0),
    ("R10", "wapiti:R_0603", 48, 26, 0),
    ("R4", "wapiti:R_0603", 44, 16, 0),
    ("R7", "wapiti:R_0603", 44, 28, 0),
    ("R5", "wapiti:R_0603", 46, 28, 0),
    ("R6", "wapiti:R_0603", 50, 28, 0),
    ("PU5", "wapiti:SOT-23-8", 46, 34, 0),
    # --- RADIO (center/right): EG915U, eSIM, SMA, GNSS patch, USB-C
    ("RU1", "wapiti:EG915U", 66, 42, 0),
    ("RU2", "wapiti:NanoSIM_Push", 74, 54, 0),
    ("C3", "wapiti:C_0603", 52, 36, 0),
    ("C4", "wapiti:C_0603", 52, 44, 0),
    ("R11", "wapiti:R_0603", 52, 48, 0),
    ("RJ2", "wapiti:SMA_EdgeMount", 96, 6, 90),
    ("ANT2", "wapiti:Antenna_UMWiSE_1.6mm", 88, 8, 0),
    ("RJ3", "wapiti:USB_C_Receptacle_16P", 8, 60, 0),
    # --- CAM (top/center): LCD, IR arrays, SoC, sensor, storage
    ("CU4", "wapiti:LCD_2in_FPC", 26, 20, 90),
    ("CD1", "wapiti:IR_Array_30x10", 60, 7, 0),
    ("CD2", "wapiti:IR_Array_30x10", 60, 18, 0),
    ("CU1", "wapiti:SSC377Q_QFN", 46, 42, 0),
    ("CU2", "wapiti:IMX415_Module", 25, 50, 0),
    ("CU3", "wapiti:eMMC_153", 42, 58, 0),
    ("CJ1", "wapiti:microSD_Push", 58, 58, 0),
    ("CQ1", "wapiti:SOT-23", 72, 1, 0),
    ("CQ2", "wapiti:SOT-23", 78, 1, 0),
    ("R14", "wapiti:R_0603", 84, 2, 0),
    ("R15", "wapiti:R_0603", 81, 2, 0),
    ("C7", "wapiti:C_0603", 54, 44, 0),
    ("C8", "wapiti:C_0603", 54, 48, 0),
    # --- MCU (right): C6 supervisor, sensors, prog header
    ("MU1", "wapiti:ESP32-C6-WROOM-1", 92, 46, 0),
    ("MU2", "wapiti:LGA-12_2x2mm", 98, 14, 0),
    ("MU3", "wapiti:PIR_Dome", 74, 6, 0),
    ("MU4", "wapiti:Radar_LD2410", 88, 22, 0),
    ("C9", "wapiti:C_0603", 57, 30, 0),
    ("C10", "wapiti:C_0603", 56, 26, 0),
    ("R20", "wapiti:R_0603", 71, 30, 0),
    ("R21", "wapiti:R_0603", 73, 30, 0),
    ("R22", "wapiti:R_0603", 75, 30, 0),
    ("R25", "wapiti:R_0603", 75, 58, 0),
    ("MD3", "wapiti:R_0603", 68, 64, 0),
    ("SW1", "wapiti:Button_4x4mm", 8, 52, 0),
    ("MJ1", "wapiti:PinHeader_2x03_P2.54mm", 95, 62, 0),
]

DNP_REFS = set()   # Pro reference populates everything; ("MU4",) for lite

MOUNTING_HOLES = [(4, 4), (96, 4), (4, 61), (96, 61)]


def gen_pcb():
    L = []
    L.append("(kicad_pcb (version 20221018) (generator wapiti)")
    L.append("")
    L.append("  (general")
    L.append("    (thickness 1.0)")
    L.append("  )")
    L.append('  (paper "A4")')
    L.append("  (layers")
    L.append('    (0 "F.Cu" signal)')
    L.append('    (31 "B.Cu" signal)')
    L.append('    (34 "B.Paste" signal)')
    L.append('    (35 "F.Paste" signal)')
    L.append('    (36 "B.SilkS" user "B.Silkscreen")')
    L.append('    (37 "F.SilkS" user "F.Silkscreen")')
    L.append('    (38 "B.Mask" user)')
    L.append('    (39 "F.Mask" user)')
    L.append('    (40 "Dwgs.User" user)')
    L.append('    (41 "Cmts.User" user)')
    L.append('    (42 "B.CrtYd" user)')
    L.append('    (43 "F.CrtYd" user)')
    L.append('    (44 "B.Fab" user)')
    L.append('    (45 "F.Fab" user)')
    L.append("  )")
    L.append('  (setup (pad_to_mask_clearance 0))')
    L.append('  (net 0 "")')
    L.append("")

    # Board outline (Edge.Cuts)
    for (x1, y1, x2, y2) in [
        (0, 0, BOARD_W, 0), (BOARD_W, 0, BOARD_W, BOARD_H),
        (BOARD_W, BOARD_H, 0, BOARD_H), (0, BOARD_H, 0, 0),
    ]:
        L.append('  (gr_line (start %s %s) (end %s %s) (layer "Edge.Cuts")'
                 ' (width 0.1) (tstamp %s))' % (x1, y1, x2, y2, u()))

    # Mounting holes
    for i, (x, y) in enumerate(MOUNTING_HOLES, 1):
        L.append('  (footprint "MountingHole:MountingHole_2.7mm" (layer "F.Cu")')
        L.append("    (at %s %s)" % (x, y))
        L.append("    (attr through_hole)")
        L.append('    (fp_text reference "H%d" (at 0 -3) (layer "F.SilkS")' % i)
        L.append("      (effects (font (size 1 1) (thickness 0.15))))")
        L.append('    (pad "" thru_hole circle (at 0 0) (size 4.5 4.5)'
                 ' (drill 2.7) (layers "*.Cu" "*.Mask"))')
        L.append("  )")

    # Footprint placements
    for ref, fp, x, y, rot in PLACEMENTS:
        rotstr = " (at %s %s %s)" % (x, y, rot) if rot else " (at %s %s)" % (x, y)
        L.append('  (footprint "%s" (layer "F.Cu")' % fp)
        L.append(rotstr)
        if ref in DNP_REFS:
            L.append("    (attr smd dnp)")
        else:
            L.append("    (attr smd)")
        L.append('    (fp_text reference "%s" (at 0 -4) (layer "F.SilkS")' % ref)
        L.append("      (effects (font (size 1 1) (thickness 0.15))))")
        L.append('    (fp_text value "%s" (at 0 4) (layer "F.Fab")' % ref)
        L.append("      (effects (font (size 1 1) (thickness 0.15))))")
        L.append("  )")

    # F.Cu ground plane (stub net; nets assigned at layout time in KiCad)
    L.append('  (zone (net 0) (net_name "") (layer "F.Cu") (tstamp %s)' % u())
    L.append("    (hatch edge 0.5)")
    L.append("    (connect_pads (clearance 0.3))")
    L.append("    (min_thickness 0.25)")
    L.append('    (fill yes (thermal_gap 0.5) (thermal_bridge_width 0.5))')
    L.append("    (polygon")
    L.append("      (pts")
    L.append("        (xy 0 0) (xy %s 0) (xy %s %s) (xy 0 %s)"
             % (BOARD_W, BOARD_W, BOARD_H, BOARD_H))
    L.append("      )")
    L.append("    )")
    L.append("  )")

    # Front-panel optics zone (top edge) + antenna corner keep-out (F.Fab)
    L.append('  (gr_rect (start 40 0) (end 100 14) (layer "F.Fab") (width 0.2)'
             ' (tstamp %s))' % u())
    L.append('  (gr_text "FRONT-PANEL OPTICS: IR arrays, PIR, radar, GNSS patch'
             ' + SMA keep-out (chassis 4.13)" (at 70 16.5) (layer "F.Fab")'
             ' (tstamp %s)' % u())
    L.append('    (effects (font (size 1.2 1.2) (thickness 0.2))))')

    L.append(")")
    L.append("")

    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "wapiti.kicad_pcb")
    with open(path, "w") as f:
        f.write("\n".join(L))
    print("wrote %s (%d footprints, %d mounting holes)"
          % (path, len(PLACEMENTS), len(MOUNTING_HOLES)))


KICAD_PRO = """{
  "board": {
    "3dviewports": [], "design_settings": {}, "layer_presets": [],
    "viewports": []
  },
  "boards": [],
  "cvpcb": {"equivalence_files": []},
  "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
  "meta": {"filename": "wapiti.kicad_pro", "version": 1},
  "net_settings": {"classes": []},
  "pcbnew": {
    "last_paths": {"gencad": "", "step": "exports/wapiti.step"},
    "page_layout_descr_file": ""
  },
  "schematic": {
    "legacy_lib_dir": "", "legacy_lib_list": []
  },
  "sheets": [],
  "text_variables": {}
}
"""

FP_LIB_TABLE = """(fp_lib_table
  (lib (name "wapiti")(type "KiCad")(uri "${KIPRJMOD}/wapiti.pretty")(options "")(descr "wapiti trail camera footprints"))
)
"""


def gen_sidecars():
    here = os.path.dirname(os.path.abspath(__file__))
    for name, content in (("wapiti.kicad_pro", KICAD_PRO),
                          ("fp-lib-table", FP_LIB_TABLE)):
        with open(os.path.join(here, name), "w") as f:
            f.write(content)
        print("wrote %s" % os.path.join(here, name))


if __name__ == "__main__":
    gen_pcb()
    gen_sidecars()
