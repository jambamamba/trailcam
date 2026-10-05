#!/usr/bin/env python3
"""Verify wapiti generated schematics: structural parse + expected net checks.

Copied from the lugtrax hardware pipeline (see /repos/utils/share/docs/kicad-skill.md):
union-find over pin tips, wires and labels; every net name in EXPECTED must
connect exactly the listed pins (ref.pin), and no pin may be floating (unless
listed in allowed_nc).
"""

import os
import sys


# ---------------------------------------------------------------------------
# S-expression parser (same minimal tokenizer as lugtrax/lora)
# ---------------------------------------------------------------------------

def parse(text):
    import re
    toks = re.findall(r'\(|\)|"[^"]*"|[^\s()]+', text)
    pos = 0

    def node():
        nonlocal pos
        tok = toks[pos]
        if tok == "(":
            pos += 1
            items = []
            while toks[pos] != ")":
                items.append(node())
            pos += 1
            return items
        if tok == ")":
            raise ValueError("unbalanced")
        pos += 1
        if tok.startswith('"') and tok.endswith('"'):
            return tok[1:-1]
        return tok

    root = node()
    if pos != len(toks):
        raise ValueError("trailing tokens")
    return root


def deep_find_all(node, name):
    out = []
    if isinstance(node, list):
        if node and node[0] == name:
            out.append(node)
        for item in node:
            out.extend(deep_find_all(item, name))
    return out


class DSU:
    def __init__(self):
        self.p = {}

    def find(self, k):
        while self.p[k] != k:
            self.p[k] = self.p[self.p[k]]
            k = self.p[k]
        return k

    def union(self, a, b):
        if a not in self.p:
            self.p[a] = a
        if b not in self.p:
            self.p[b] = b
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def fnum(v):
    return float(v)


def key(x, y):
    return (round(fnum(x), 3), round(fnum(y), 3))


def rot_pt_single(x, y, rot):
    if rot == 90:
        return (-y, x)
    if rot == 180:
        return (-x, -y)
    if rot == 270:
        return (y, -x)
    return (x, y)


def extract(path):
    text = open(path).read()
    tree = parse(text)
    dsu = DSU()

    # Pin tips: from lib symbol definitions + placed instances
    lib_pins = {}
    for libsym in deep_find_all(tree, "symbol"):
        if len(libsym) > 1 and isinstance(libsym[1], str) and libsym[1].startswith("wapiti:"):
            sid = libsym[1][7:]
            units = [u for u in libsym[2:] if isinstance(u, list) and u and u[0] == "symbol"]
            for unit in units:
                if not (len(unit) > 1 and isinstance(unit[1], str) and unit[1].endswith("_1_1")):
                    continue
                for pin in [p for p in unit[2:] if isinstance(p, list) and p and p[0] == "pin"]:
                    at = [a for a in pin[2:] if isinstance(a, list) and a and a[0] == "at"]
                    num = [n for n in pin[2:] if isinstance(n, list) and n and n[0] == "number"]
                    if at and num:
                        ax, ay, ang = at[0][1:4]
                        lib_pins.setdefault(sid, {})[num[0][1]] = (fnum(ax), fnum(ay), fnum(ang))

    placed = []  # (ref, sid, at)
    for sym in deep_find_all(tree, "symbol"):
        if not (len(sym) > 1 and isinstance(sym[0], str) and sym[0] == "symbol"):
            continue
        if not any(isinstance(x, list) and x and x[0] == "lib_id" for x in sym[1:]):
            continue
        lib_id = [x for x in sym[1:] if isinstance(x, list) and x and x[0] == "lib_id"][0][1]
        sid = lib_id.split(":")[1] if ":" in lib_id else lib_id
        at = [x for x in sym[1:] if isinstance(x, list) and x and x[0] == "at"][0]
        props = {}
        for pr in [x for x in sym[1:] if isinstance(x, list) and x and x[0] == "property"]:
            props[pr[1]] = pr[2]
        ref = props.get("Reference", "?")
        sx, sy, rot = fnum(at[1]), fnum(at[2]), fnum(at[3])
        placed.append((ref, sid, (sx, sy, rot)))
        for pin in [x for x in sym[1:] if isinstance(x, list) and x and x[0] == "pin"]:
            pnum = pin[1]
            px, py, pang = lib_pins[sid][pnum]
            rx, ry = rot_pt_single(px, py, rot)
            k = key(sx + rx, sy + ry)
            dsu.union(("pin", ref, pnum), k)

    # Wires
    for wire in deep_find_all(tree, "wire"):
        pts = [p for p in wire[1:] if isinstance(p, list) and p and p[0] == "pts"][0]
        (x1, y1), (x2, y2) = [(fnum(p[1]), fnum(p[2])) for p in pts[1:]]
        ka, kb = key(x1, y1), key(x2, y2)
        dsu.union(ka, kb)

    # Labels attach to their tip
    label_net = {}
    for lab in deep_find_all(tree, "label"):
        at = [a for a in lab[1:] if isinstance(a, list) and a and a[0] == "at"][0]
        name = lab[1]
        k = key(at[1], at[2])
        if k in dsu.p:
            label_net[dsu.find(k)] = name

    return dsu, label_net, placed


def net_of(dsu, label_net, ref, num):
    k = ("pin", ref, str(num))
    if k not in dsu.p:
        return None
    root = dsu.find(k)
    return label_net.get(root)


# ---------------------------------------------------------------------------
# Expected nets: file -> {net: [(ref, pin), ...]}
# ---------------------------------------------------------------------------

EXPECTED = {
    "power.kicad_sch": {
        "V_PACK_RAW": [("BT1", "1"), ("F1", "1"), ("F1", "2"), ("D1", "1"), ("U5", "6")],
        "V_AA_RAW": [("BT2", "1"), ("F2", "1"), ("F2", "2"), ("D3", "1")],
        "VSYS_RAW": [("D1", "2"), ("D3", "2"), ("D4", "2"), ("C1", "1"), ("U1", "1"), ("D2", "1")],
        "VSYS_SW": [("U1", "3"), ("L1", "1")],
        "V_SYS": [("L1", "2"), ("C2", "1"), ("U2", "1"), ("U3", "1"), ("U5", "1"),
                  ("R5", "1"), ("R7", "1")],
        "EN_BUCK": [("U1", "2"), ("R7", "2")],
        "FB": [("U1", "5"), ("R5", "2"), ("R6", "1")],
        "V_CAM": [("U2", "3")],
        "V_MODEM": [("U3", "3")],
        "EN_CAM": [("U2", "2"), ("R8", "1")],
        "EN_MODEM": [("U3", "2"), ("R10", "1")],
        "SOLAR_IN": [("J1", "1"), ("U4", "1")],
        "SOLAR_SW": [("U4", "3"), ("D4", "1")],
        "SOLAR_OK": [("U4", "2"), ("R9", "1")],
        "V_RES": [("BT3", "1")],
        "PACK_TEMP": [("R4", "1")],
        "SDA": [("U5", "3")],
        "SCL": [("U5", "4")],
        "GAUGE_INT": [("U5", "5")],
        "SRN": [("U5", "7")],
        "GND": [("BT1", "2"), ("BT2", "2"), ("BT3", "2"), ("C1", "2"), ("C2", "2"),
                ("D2", "2"), ("U1", "4"), ("U2", "4"), ("U3", "4"), ("U4", "4"),
                ("R4", "2"), ("R6", "2"), ("R8", "2"), ("R9", "2"), ("R10", "2"),
                ("U5", "2"), ("J1", "2")],
    },
    "radio.kicad_sch": {
        "V_MODEM": [("U1", "1"), ("C3", "1"), ("C4", "1")],
        "GND": [("U1", "2"), ("U1", "11"), ("U1", "14"), ("C3", "2"), ("C4", "2"),
                ("U2", "4"), ("R11", "2"), ("J2", "2"), ("J3", "4")],
        "PWRKEY": [("U1", "5"), ("R11", "1")],
        "MODEM_TX": [("U1", "3")],
        "MODEM_RX": [("U1", "4")],
        "RI": [("U1", "6")],
        "SIM_VDD": [("U1", "7"), ("U2", "1")],
        "SIM_DATA": [("U1", "8"), ("U2", "6")],
        "SIM_CLK": [("U1", "9"), ("U2", "3")],
        "SIM_RST": [("U1", "10"), ("U2", "2")],
        "LTE_ANT": [("U1", "12"), ("J2", "1")],
        "GNSS_ANT": [("U1", "13"), ("ANT2", "1")],
        "USB_DP": [("U1", "15"), ("J3", "3")],
        "USB_DM": [("U1", "16"), ("J3", "2")],
        "PERST": [("U1", "17")],
    },
    "cam.kicad_sch": {
        "V_CAM": [("U1", "1"), ("C7", "1"), ("C8", "1"), ("U3", "1"), ("J1", "1"),
                  ("U4", "1"), ("D1", "1"), ("D2", "1"), ("U2", "1")],
        "CSI_P": [("U1", "3"), ("U2", "3")],
        "CSI_N": [("U1", "4"), ("U2", "4")],
        "CAM_SDA": [("U1", "5"), ("U2", "5")],
        "CAM_SCL": [("U1", "6"), ("U2", "6")],
        "SENS_CLK": [("U1", "7"), ("U2", "7")],
        "STANDBY": [("U1", "8"), ("U2", "8")],
        "IR_940": [("U1", "11"), ("Q1", "1"), ("R14", "1")],
        "IR940_K": [("D1", "2"), ("Q1", "2")],
        "IR_850": [("U1", "12"), ("Q2", "1"), ("R15", "1")],
        "IR850_K": [("D2", "2"), ("Q2", "2")],
        "LCD_SCK": [("U1", "13"), ("U4", "3")],
        "LCD_MOSI": [("U1", "14"), ("U4", "4")],
        "LCD_DC": [("U1", "15"), ("U4", "5")],
        "LCD_RST": [("U1", "16"), ("U4", "6")],
        "LCD_BKL": [("U1", "17"), ("U4", "7")],
        "EMMC_CMD": [("U1", "18"), ("U3", "3")],
        "EMMC_CLK": [("U1", "19"), ("U3", "4")],
        "EMMC_DAT": [("U1", "20"), ("U3", "5")],
        "SD_CD": [("U1", "21"), ("J1", "6")],
        "SD_CLK": [("U1", "22"), ("J1", "4")],
        "SD_CMD": [("U1", "23"), ("J1", "3")],
        "SD_DAT": [("U1", "24"), ("J1", "5")],
        "UART_RX": [("U1", "9")],
        "UART_TX": [("U1", "10")],
        "GND": [("U1", "2"), ("U1", "25"), ("U2", "2"), ("U3", "2"), ("U3", "6"),
                ("J1", "2"), ("U4", "2"), ("Q1", "3"), ("Q2", "3"), ("C7", "2"),
                ("C8", "2"), ("R14", "2"), ("R15", "2")],
    },
    "mcu.kicad_sch": {
        "V_MCU": [("U1", "1"), ("C9", "1"), ("C10", "1"), ("R20", "1"), ("R21", "1"),
                  ("R22", "1"), ("J1", "1"), ("U2", "1"), ("U3", "1"), ("U4", "1"),
                  ("U4", "4")],
        "GND": [("U1", "18"), ("U1", "19"), ("U2", "2"), ("U3", "3"), ("U4", "2"),
                ("C9", "2"), ("C10", "2"), ("J1", "5"), ("J2", "4"), ("SW1", "2"),
                ("R25", "2"), ("D3", "2")],
        "EN": [("U1", "2"), ("R20", "2"), ("J1", "2"), ("SW1", "1")],
        "SDA": [("U1", "5"), ("U2", "3"), ("R21", "2")],
        "SCL": [("U1", "6"), ("U2", "4"), ("R22", "2")],
        "GAUGE_INT": [("U1", "8")],
        "PIR_OUT": [("U1", "3"), ("U3", "2")],
        "RADAR_OUT": [("U1", "4"), ("U4", "3")],
        "EN_CAM": [("U1", "9")],
        "PERST": [("U1", "10")],
        "UART_RX": [("U1", "11"), ("J1", "3")],
        "UART_TX": [("U1", "12"), ("J1", "4")],
        "USB_DP": [("U1", "14"), ("J2", "3")],
        "USB_DM": [("U1", "13"), ("J2", "2")],
        "SOLAR_OK": [("U1", "15")],
        "BOOT": [("U1", "7"), ("J1", "6")],
        "LED_STAT": [("U1", "17"), ("R25", "1"), ("D3", "1")],
        "ACCEL_INT": [("U1", "16"), ("U2", "5")],
    },
}

ALLOWED_NC = {
    "power.kicad_sch": [],
    "radio.kicad_sch": [("U2", "5"),           # eSIM VPP
                        ("J3", "1"), ("J3", "5"), ("J3", "6")],  # VBUS + CC
    "cam.kicad_sch": [],
    "mcu.kicad_sch": [("J2", "1"), ("J2", "5"), ("J2", "6")],    # VBUS + CC
}


def check_file(path, expected, allowed_nc):
    dsu, label_net, placed = extract(path)
    errors = []

    # every expected pin on its net
    for net, pins in expected.items():
        for ref, num in pins:
            got = net_of(dsu, label_net, ref, num)
            if got != net:
                errors.append("%s: %s.%s expected net %s, got %s" % (path, ref, num, net, got))

    # floating check via generator symbol table
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gen_schematic as G
    for ref, sid, _ in placed:
        sym = G.SYMBOLS.get(sid)
        if not sym:
            continue
        for p in sym["pins"]:
            pnum = p[0]
            if (ref, pnum) in [(r, str(n)) for r, n in allowed_nc]:
                continue
            got = net_of(dsu, label_net, ref, pnum)
            if got is None:
                errors.append("%s: %s.%s is floating (no net)" % (path, ref, pnum))
    return errors


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    all_errors = []
    for fname, expected in EXPECTED.items():
        path = os.path.join(here, fname)
        if not os.path.exists(path):
            print("MISSING: %s" % path)
            all_errors.append("%s missing" % fname)
            continue
        errs = check_file(path, expected, ALLOWED_NC.get(fname, []))
        all_errors.extend(errs)
        status = "OK" if not errs else "FAIL (%d)" % len(errs)
        print("== %s: %s" % (fname, status))
        for e in errs:
            print("   ", e)
    if all_errors:
        print("\n%d problem(s)" % len(all_errors))
        sys.exit(1)
    print("\nAll schematic net checks passed.")


if __name__ == "__main__":
    main()

