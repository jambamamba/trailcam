#!/usr/bin/env python3
"""Generate KiCad 7/10 schematics for the wapiti trail camera (wapiti).

Emitter style copied from the lugtrax hardware pipeline (see
/repos/utils/share/docs/kicad-skill.md): all symbols embedded inline
(wapiti: prefix), every wire endpoint computed from pin tips via tip()
helpers, nets that would cross symbol bodies use labels at pin tips.

Produces (from hardware/):
  wapiti.kicad_sch   - root sheet with four child sheets
  power.kicad_sch    - pack sled + AA tray + reserve cell, supercap, buck,
                       solar input with charge-interlock switch, fuel gauge
  radio.kicad_sch    - EG915U LTE Cat-1bis + GNSS, eSIM, SMA LTE antenna,
                       GNSS patch antenna, USB-C service port
  cam.kicad_sch      - SSC377Q SoC + IMX415 sensor + eMMC + microSD +
                       2in LCD + dual IR LED arrays on MOSFET switches
  mcu.kicad_sch      - ESP32-C6 co-processor + LIS2DW12 + PIR + mmWave
                       radar + status LED + USB-C + programming header

Validate with:  kicad-cli sch export svg <file> -o /tmp/out
"""

import os
import uuid


def u():
    return str(uuid.uuid4())


def fmt(v):
    s = "%.6f" % float(v)
    s = s.rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def rot_pt(x, y, rot):
    if rot == 90:
        return (-y, x)
    if rot == 180:
        return (-x, -y)
    if rot == 270:
        return (y, -x)
    return (x, y)


# ---------------------------------------------------------------------------
# Symbol library (wapiti: prefix). Pin tuples: (num, name, x, y, angle, len, type)
# where (x, y) is the CONNECTION TIP offset from the symbol origin.
# ---------------------------------------------------------------------------

def sym_resistor(sid):
    return {"id": sid, "hide_num": True, "pins": [
        ("1", "~", -2.54, 0, 0, 2.54, "passive"),
        ("2", "~", 2.54, 0, 180, 2.54, "passive")],
        "body": [("rect", (-1.016, -1.27, 1.016, 1.27))]}


def sym_capacitor(sid, polarized=False):
    pins = [("1", "+" if polarized else "~", 0, 2.54, 270, 2.54, "passive"),
            ("2", "~", 0, -2.54, 90, 2.54, "passive")]
    body = [("rect", (-1.524, -0.762, 1.524, 0.762))]
    if polarized:
        body.append(("poly", [(1.27, 0.635), (1.27, -0.635), (0.635, 0), (1.905, 0)]))
        body.append(("poly", [(0.635, -1.905), (1.905, -1.905)]))
    return {"id": sid, "hide_num": True, "pins": pins, "body": body}


def sym_diode(sid):
    return {"id": sid, "hide_num": True, "pins": [
        ("1", "A", -3.81, 0, 0, 2.54, "passive"),
        ("2", "K", 3.81, 0, 180, 2.54, "passive")],
        "body": [
            ("poly", [(-1.27, 1.27), (-1.27, -1.27), (1.27, 0), (-1.27, 1.27)]),
            ("rect", (1.27, -1.27, 1.905, 1.27))]}


def sym_tvs(sid):
    return {"id": sid, "hide_num": True, "pins": [
        ("1", "~", 0, 2.54, 270, 2.54, "passive"),
        ("2", "~", 0, -2.54, 90, 2.54, "passive")],
        "body": [
            ("rect", (-1.27, -0.762, 1.27, 0.762)),
            ("poly", [(-0.762, 0.762), (-0.762, -0.762), (-1.905, -0.762)]),
            ("poly", [(0.762, 0.762), (0.762, -0.762), (1.905, -0.762)])]}


def sym_fuse(sid):
    return {"id": sid, "hide_num": True, "pins": [
        ("1", "~", -2.54, 0, 0, 2.54, "passive"),
        ("2", "~", 2.54, 0, 180, 2.54, "passive")],
        "body": [("rect", (-0.635, -1.905, 0.635, 1.905))]}


def sym_battery(sid):
    return {"id": sid, "hide_num": True, "pins": [
        ("1", "+", 0, 3.81, 270, 2.54, "passive"),
        ("2", "-", 0, -3.81, 90, 2.54, "passive")],
        "body": [
            ("rect", (-2.54, -2.54, 2.54, 2.54)),
            ("poly", [(1.016, 1.016), (1.016, 2.794)]),
            ("poly", [(0.127, 1.905), (1.905, 1.905)]),
            ("poly", [(0.127, -1.905), (1.905, -1.905)])]}


def sym_load_switch(sid):
    """4-pin load switch: VIN(1) EN(2) VOUT(3) GND(4)."""
    return {"id": sid, "hide_num": False, "pins": [
        ("1", "VIN", -5.08, 0, 0, 2.54, "power_in"),
        ("2", "EN", -2.54, -5.08, 270, 2.54, "input"),
        ("3", "VOUT", 5.08, 0, 180, 2.54, "power_out"),
        ("4", "GND", 0, -5.08, 90, 2.54, "power_in")],
        "body": [("rect", (-2.54, -2.54, 2.54, 2.54))]}


def sym_buck(sid):
    """Buck regulator: VIN(1) EN(2) SW(3) GND(4) FB(5). SW drives an
    external inductor to V_SYS; FB senses the V_SYS divider."""
    return {"id": sid, "hide_num": False, "pins": [
        ("1", "VIN", -5.08, 2.54, 0, 2.54, "power_in"),
        ("2", "EN", -5.08, 0, 0, 2.54, "input"),
        ("3", "SW", -5.08, -2.54, 0, 2.54, "power_out"),
        ("4", "GND", 0, -5.08, 90, 2.54, "power_in"),
        ("5", "FB", 5.08, -2.54, 180, 2.54, "input")],
        "body": [("rect", (-2.54, -2.54, 2.54, 2.54))]}


def sym_inductor(sid):
    return {"id": sid, "hide_num": True, "pins": [
        ("1", "~", -2.54, 0, 0, 2.54, "passive"),
        ("2", "~", 2.54, 0, 180, 2.54, "passive")],
        "body": [
            ("poly", [(-1.27, -1.27), (-1.27, 1.27)]),
            ("poly", [(0, -1.27), (0, 1.27)]),
            ("poly", [(1.27, -1.27), (1.27, 1.27)])]}


def sym_conn2(sid):
    """Generic 2-pin connector (solar input, SMA bulkhead)."""
    return {"id": sid, "hide_num": False, "pins": [
        ("1", "1", -2.54, 0, 0, 2.54, "passive"),
        ("2", "2", 2.54, 0, 180, 2.54, "passive")],
        "body": [("rect", (-1.27, -1.905, 1.27, 1.905))]}


def sym_gauge(sid):
    """BQ27441-class fuel gauge: VDD GND SDA SCL INT BAT SRN."""
    return {"id": sid, "hide_num": False, "pins": [
        ("1", "VDD", -5.08, 7.62, 0, 2.54, "power_in"),
        ("2", "GND", -5.08, 5.08, 0, 2.54, "power_in"),
        ("3", "SDA", 5.08, 5.08, 180, 2.54, "bidirectional"),
        ("4", "SCL", 5.08, 2.54, 180, 2.54, "input"),
        ("5", "INT", 5.08, 0, 180, 2.54, "output"),
        ("6", "BAT", 5.08, -2.54, 180, 2.54, "passive"),
        ("7", "SRN", 5.08, -5.08, 180, 2.54, "passive")],
        "body": [("rect", (-2.54, -3.81, 2.54, 5.08))]}


def sym_modem(sid):
    """EG915U-class LTE Cat-1bis module with GNSS + USB service port."""
    return {"id": sid, "hide_num": False, "pins": [
        ("1", "VCC", -10.16, 10.16, 0, 2.54, "power_in"),
        ("2", "GND", -10.16, 7.62, 0, 2.54, "power_in"),
        ("3", "TXD", 10.16, 10.16, 180, 2.54, "output"),
        ("4", "RXD", 10.16, 7.62, 180, 2.54, "input"),
        ("5", "PWRKEY", 10.16, 5.08, 180, 2.54, "input"),
        ("6", "RI", 10.16, 2.54, 180, 2.54, "output"),
        ("7", "USIM_VDD", 10.16, 0, 180, 2.54, "power_out"),
        ("8", "USIM_DATA", 10.16, -2.54, 180, 2.54, "bidirectional"),
        ("9", "USIM_CLK", 10.16, -5.08, 180, 2.54, "output"),
        ("10", "USIM_RST", 10.16, -7.62, 180, 2.54, "output"),
        ("11", "USIM_GND", 10.16, -10.16, 180, 2.54, "power_in"),
        ("12", "ANT_LTE", 0, 12.7, 270, 2.54, "passive"),
        ("13", "ANT_GNSS", 5.08, 12.7, 270, 2.54, "passive"),
        ("14", "GND2", 0, -12.7, 90, 2.54, "power_in"),
        ("15", "USB_DP", -10.16, 2.54, 0, 2.54, "bidirectional"),
        ("16", "USB_DM", -10.16, 0, 0, 2.54, "bidirectional"),
        ("17", "RESET_N", -10.16, -2.54, 0, 2.54, "input")],
        "body": [("rect", (-7.62, -10.16, 7.62, 10.16))]}


def sym_sim(sid):
    """eSIM pads: VDD RST CLK GND VPP DATA."""
    return {"id": sid, "hide_num": False, "pins": [
        ("1", "VDD", -5.08, 5.08, 0, 2.54, "power_in"),
        ("2", "RST", -5.08, 2.54, 0, 2.54, "input"),
        ("3", "CLK", -5.08, 0, 0, 2.54, "input"),
        ("4", "GND", -5.08, -2.54, 0, 2.54, "power_in"),
        ("5", "VPP", -5.08, -5.08, 0, 2.54, "power_in"),
        ("6", "DATA", 5.08, 0, 180, 2.54, "bidirectional")],
        "body": [("rect", (-2.54, -6.35, 2.54, 6.35))]}


def sym_mcu(sid):
    """ESP32-C6-WROOM-1 co-processor (wake supervisor + BLE/Wi-Fi)."""
    return {"id": sid, "hide_num": False, "pins": [
        ("1", "3V3", -10.16, 10.16, 0, 2.54, "power_in"),
        ("2", "EN", -10.16, 7.62, 0, 2.54, "input"),
        ("3", "GPIO4/PIR", -10.16, 5.08, 0, 2.54, "input"),
        ("4", "GPIO5/RADAR", -10.16, 2.54, 0, 2.54, "input"),
        ("5", "GPIO6/SDA", -10.16, 0, 0, 2.54, "bidirectional"),
        ("6", "GPIO7/SCL", -10.16, -2.54, 0, 2.54, "bidirectional"),
        ("7", "GPIO9/BOOT", -10.16, -5.08, 0, 2.54, "bidirectional"),
        ("8", "GPIO10/GINT", -10.16, -7.62, 0, 2.54, "input"),
        ("9", "GPIO18/SOCEN", -10.16, -10.16, 0, 2.54, "output"),
        ("10", "GPIO19/PERST", 10.16, 10.16, 180, 2.54, "output"),
        ("11", "GPIO20/RX", 10.16, 7.62, 180, 2.54, "input"),
        ("12", "GPIO21/TX", 10.16, 5.08, 180, 2.54, "output"),
        ("13", "USB_D-", 10.16, 2.54, 180, 2.54, "bidirectional"),
        ("14", "USB_D+", 10.16, 0, 180, 2.54, "bidirectional"),
        ("15", "GPIO2/SOLAR", 10.16, -2.54, 180, 2.54, "output"),
        ("16", "GPIO15/NC", 10.16, -5.08, 180, 2.54, "bidirectional"),
        ("17", "GPIO13/LED", 10.16, -7.62, 180, 2.54, "output"),
        ("18", "GND", 0, -12.7, 90, 2.54, "power_in"),
        ("19", "GND2", 10.16, -12.7, 180, 2.54, "power_in")],
        "body": [("rect", (-7.62, -10.16, 7.62, 10.16))]}


def sym_accel(sid):
    """LIS2DW12-class 3-axis accelerometer."""
    return {"id": sid, "hide_num": False, "pins": [
        ("1", "VDD", -5.08, 2.54, 0, 2.54, "power_in"),
        ("2", "GND", -5.08, 0, 0, 2.54, "power_in"),
        ("3", "SDA", 5.08, 2.54, 180, 2.54, "bidirectional"),
        ("4", "SCL", 5.08, 0, 180, 2.54, "bidirectional"),
        ("5", "INT1", 5.08, -2.54, 180, 2.54, "output")],
        "body": [("rect", (-2.54, -2.54, 2.54, 3.81))]}


def sym_usb(sid):
    """USB-C receptacle (service)."""
    return {"id": sid, "hide_num": False, "pins": [
        ("1", "VBUS", -5.08, 2.54, 0, 2.54, "power_out"),
        ("2", "D-", -5.08, 0, 0, 2.54, "bidirectional"),
        ("3", "D+", -5.08, -2.54, 0, 2.54, "bidirectional"),
        ("4", "GND", -5.08, -5.08, 0, 2.54, "power_in"),
        ("5", "CC1", 5.08, 2.54, 180, 2.54, "passive"),
        ("6", "CC2", 5.08, 0, 180, 2.54, "passive")],
        "body": [("rect", (-2.54, -5.08, 2.54, 3.81))]}


def sym_header(sid):
    """2x03 programming header."""
    return {"id": sid, "hide_num": False, "pins": [
        ("1", "3V3", -5.08, 2.54, 0, 2.54, "power_in"),
        ("2", "EN", -5.08, 0, 0, 2.54, "input"),
        ("3", "TX", -5.08, -2.54, 0, 2.54, "input"),
        ("4", "RX", 5.08, 2.54, 180, 2.54, "output"),
        ("5", "GND", 5.08, 0, 180, 2.54, "power_in"),
        ("6", "IO9", 5.08, -2.54, 180, 2.54, "bidirectional")],
        "body": [("rect", (-2.54, -3.81, 2.54, 3.81))]}


def sym_switch(sid):
    return {"id": sid, "hide_num": True, "pins": [
        ("1", "~", -3.81, 0, 0, 2.54, "passive"),
        ("2", "~", 3.81, 0, 180, 2.54, "passive")],
        "body": [
            ("rect", (-1.905, -0.762, -0.254, 0.762)),
            ("rect", (0.254, -0.762, 1.905, 0.762))]}


def sym_antenna(sid):
    return {"id": sid, "hide_num": True, "pins": [
        ("1", "~", 0, -2.54, 90, 2.54, "passive")],
        "body": [
            ("poly", [(-2.54, 0), (2.54, 0)]),
            ("poly", [(-1.27, 0.762), (1.27, 0.762)]),
            ("poly", [(-0.635, 1.524), (0.635, 1.524)])]}


def sym_soc(sid):
    """SSC377Q-class camera SoC (reduced functional pin set, 25 pins)."""
    return {"id": sid, "hide_num": False, "pins": [
        ("1", "VDD", -10.16, 10.16, 0, 2.54, "power_in"),
        ("2", "GND", -10.16, 7.62, 0, 2.54, "power_in"),
        ("3", "CSI_P", -10.16, 5.08, 0, 2.54, "output"),
        ("4", "CSI_N", -10.16, 2.54, 0, 2.54, "output"),
        ("5", "CAM_SDA", -10.16, 0, 0, 2.54, "bidirectional"),
        ("6", "CAM_SCL", -10.16, -2.54, 0, 2.54, "output"),
        ("7", "SENS_CLK", -10.16, -5.08, 0, 2.54, "output"),
        ("8", "STANDBY", -10.16, -7.62, 0, 2.54, "output"),
        ("9", "UART_RX", -10.16, -10.16, 0, 2.54, "input"),
        ("10", "UART_TX", 10.16, 10.16, 180, 2.54, "output"),
        ("11", "IR_940", 10.16, 7.62, 180, 2.54, "output"),
        ("12", "IR_850", 10.16, 5.08, 180, 2.54, "output"),
        ("13", "LCD_SCK", 10.16, 2.54, 180, 2.54, "output"),
        ("14", "LCD_MOSI", 10.16, 0, 180, 2.54, "output"),
        ("15", "LCD_DC", 10.16, -2.54, 180, 2.54, "output"),
        ("16", "LCD_RST", 10.16, -5.08, 180, 2.54, "output"),
        ("17", "LCD_BKL", 10.16, -7.62, 180, 2.54, "output"),
        ("18", "EMMC_CMD", 10.16, -10.16, 180, 2.54, "output"),
        ("19", "EMMC_CLK", 0, 12.7, 270, 2.54, "output"),
        ("20", "EMMC_DAT", 5.08, 12.7, 270, 2.54, "bidirectional"),
        ("21", "SD_CD", -5.08, 12.7, 270, 2.54, "input"),
        ("22", "SD_CLK", -5.08, -12.7, 90, 2.54, "output"),
        ("23", "SD_CMD", 0, -12.7, 90, 2.54, "bidirectional"),
        ("24", "SD_DAT", 5.08, -12.7, 90, 2.54, "bidirectional"),
        ("25", "GND2", 0, -15.24, 90, 2.54, "power_in")],
        "body": [("rect", (-7.62, -10.16, 7.62, 10.16))]}


def sym_sensor(sid):
    """IMX415-class 8.4 MP sensor module (sensor + lens on FPC stub)."""
    return {"id": sid, "hide_num": False, "pins": [
        ("1", "VDD", -5.08, 5.08, 0, 2.54, "power_in"),
        ("2", "GND", -5.08, 2.54, 0, 2.54, "power_in"),
        ("3", "CSI_P", 5.08, 5.08, 180, 2.54, "output"),
        ("4", "CSI_N", 5.08, 2.54, 180, 2.54, "output"),
        ("5", "SDA", 5.08, 0, 180, 2.54, "bidirectional"),
        ("6", "SCL", 5.08, -2.54, 180, 2.54, "input"),
        ("7", "CLKIN", 5.08, -5.08, 180, 2.54, "input"),
        ("8", "STANDBY", -5.08, 0, 0, 2.54, "input")],
        "body": [("rect", (-2.54, -3.81, 2.54, 5.08))]}


def sym_emmc(sid):
    """8 GB eMMC (reduced pins: VCC GND CMD CLK DAT RST)."""
    return {"id": sid, "hide_num": False, "pins": [
        ("1", "VCC", -5.08, 5.08, 0, 2.54, "power_in"),
        ("2", "GND", -5.08, 2.54, 0, 2.54, "power_in"),
        ("3", "CMD", 5.08, 5.08, 180, 2.54, "bidirectional"),
        ("4", "CLK", 5.08, 2.54, 180, 2.54, "input"),
        ("5", "DAT", 5.08, 0, 180, 2.54, "bidirectional"),
        ("6", "RST", 5.08, -2.54, 180, 2.54, "input")],
        "body": [("rect", (-2.54, -3.81, 2.54, 5.08))]}


def sym_sdcard(sid):
    """microSD push-push slot (VDD GND CMD CLK DAT CD)."""
    return {"id": sid, "hide_num": False, "pins": [
        ("1", "VDD", -5.08, 5.08, 0, 2.54, "power_in"),
        ("2", "GND", -5.08, 2.54, 0, 2.54, "power_in"),
        ("3", "CMD", 5.08, 5.08, 180, 2.54, "bidirectional"),
        ("4", "CLK", 5.08, 2.54, 180, 2.54, "input"),
        ("5", "DAT", 5.08, 0, 180, 2.54, "bidirectional"),
        ("6", "CD", 5.08, -2.54, 180, 2.54, "output")],
        "body": [("rect", (-2.54, -3.81, 2.54, 5.08))]}


def sym_ledarr(sid):
    """IR LED array (anode/cathode pair, driven low-side via MOSFET)."""
    return {"id": sid, "hide_num": True, "pins": [
        ("1", "A", -3.81, 0, 0, 2.54, "passive"),
        ("2", "K", 3.81, 0, 180, 2.54, "passive")],
        "body": [
            ("rect", (-2.54, -1.905, 2.54, 1.905)),
            ("poly", [(-0.635, 0.635), (-0.635, -0.635), (0.635, 0), (-0.635, 0.635)])]}


def sym_mosfet(sid):
    """N-MOSFET low-side switch: G(1) D(2) S(3)."""
    return {"id": sid, "hide_num": False, "pins": [
        ("1", "G", -5.08, 0, 0, 2.54, "input"),
        ("2", "D", 0, 5.08, 270, 2.54, "passive"),
        ("3", "S", 0, -5.08, 90, 2.54, "passive")],
        "body": [("rect", (-1.27, -2.54, 1.27, 2.54))]}


def sym_lcd(sid):
    """2.0in SPI LCD (VDD GND SCK MOSI DC RST BKL)."""
    return {"id": sid, "hide_num": False, "pins": [
        ("1", "VDD", -5.08, 7.62, 0, 2.54, "power_in"),
        ("2", "GND", -5.08, 5.08, 0, 2.54, "power_in"),
        ("3", "SCK", -5.08, 2.54, 0, 2.54, "input"),
        ("4", "MOSI", -5.08, 0, 0, 2.54, "input"),
        ("5", "DC", -5.08, -2.54, 0, 2.54, "input"),
        ("6", "RST", -5.08, -5.08, 0, 2.54, "input"),
        ("7", "BKL", 5.08, 0, 180, 2.54, "input")],
        "body": [("rect", (-2.54, -6.35, 2.54, 6.35))]}


def sym_pir(sid):
    """Digital PIR (AS312-class): VDD OUT GND."""
    return {"id": sid, "hide_num": False, "pins": [
        ("1", "VDD", -5.08, 2.54, 0, 2.54, "power_in"),
        ("2", "OUT", 5.08, 0, 180, 2.54, "output"),
        ("3", "GND", -5.08, -2.54, 0, 2.54, "power_in")],
        "body": [("rect", (-2.54, -1.905, 2.54, 1.905))]}


def sym_radar(sid):
    """24 GHz mmWave radar (LD2410-class, optional populate)."""
    return {"id": sid, "hide_num": False, "pins": [
        ("1", "VCC", -5.08, 5.08, 0, 2.54, "power_in"),
        ("2", "GND", -5.08, 2.54, 0, 2.54, "power_in"),
        ("3", "OUT", 5.08, 5.08, 180, 2.54, "output"),
        ("4", "EN", 5.08, 2.54, 180, 2.54, "input")],
        "body": [("rect", (-2.54, -2.54, 2.54, 3.81))]}


SYMBOLS = {s["id"]: s for s in [
    sym_resistor("R"), sym_capacitor("C"), sym_capacitor("CP", polarized=True),
    sym_diode("D"), sym_tvs("TVS"), sym_fuse("F"), sym_battery("BT"),
    sym_load_switch("LS"), sym_buck("BUCK"), sym_inductor("L"),
    sym_conn2("CONN2"), sym_gauge("GAUGE"), sym_modem("MODEM"), sym_sim("SIM"),
    sym_mcu("MCU"), sym_accel("ACCEL"), sym_usb("USB"), sym_header("HDR"),
    sym_switch("SW"), sym_antenna("ANT"), sym_soc("SOC"), sym_sensor("SENSOR"),
    sym_emmc("EMMC"), sym_sdcard("SDCARD"), sym_ledarr("LEDARR"),
    sym_mosfet("MOSFET"), sym_lcd("LCD"), sym_pir("PIR"), sym_radar("RADAR"),
]}

FOOTPRINTS = {
    "BT": "wapiti:Pack_Conn_5p",
    "F": "wapiti:Fuse_1206",
    "D": "wapiti:Diode_SMA",
    "TVS": "wapiti:TVS_SOD-323",
    "R": "wapiti:R_0603",
    "C": "wapiti:C_0603",
    "CP": "wapiti:CP_Elec_6.3x7.7",
    "LS": "wapiti:SOT-23-5",
    "BUCK": "wapiti:SOIC-8",
    "L": "wapiti:L_1210",
    "CONN2": "wapiti:JST_PH_2p",
    "GAUGE": "wapiti:SOT-23-8",
    "MODEM": "wapiti:EG915U",
    "SIM": "wapiti:NanoSIM_Push",
    "MCU": "wapiti:ESP32-C6-WROOM-1",
    "ACCEL": "wapiti:LGA-12_2x2mm",
    "USB": "wapiti:USB_C_Receptacle_16P",
    "HDR": "wapiti:PinHeader_2x03_P2.54mm",
    "SW": "wapiti:Button_4x4mm",
    "ANT": "wapiti:Antenna_UMWiSE_1.6mm",
    "SOC": "wapiti:SSC377Q_QFN",
    "SENSOR": "wapiti:IMX415_Module",
    "EMMC": "wapiti:eMMC_153",
    "SDCARD": "wapiti:microSD_Push",
    "LCD": "wapiti:LCD_2in_FPC",
    "LEDARR": "wapiti:IR_Array_30x10",
    "MOSFET": "wapiti:SOT-23",
    "PIR": "wapiti:PIR_Dome",
    "RADAR": "wapiti:Radar_LD2410",
}

# Value-SKU cost-down: RADAR (and only it) is DNP on wapiti-lite; the Pro
# reference design generated here populates it. Flip by adding ("U4","RADAR")
# to DNP_REFS and regenerating (mirrors the lugtrax LT-2 convention).
DNP_REFS = set()

PIN_TYPE_ORDER = ["passive", "power_in", "power_out", "input", "output", "bidirectional"]


def pin_sort_key(p):
    return (PIN_TYPE_ORDER.index(p[6]) if p[6] in PIN_TYPE_ORDER else 99, int(p[0]))


# ---------------------------------------------------------------------------
# Render helpers (same as lugtrax/lora)
# ---------------------------------------------------------------------------

def render_body(body, ind):
    out = []
    for item in body:
        if item[0] == "rect":
            x1, y1, x2, y2 = item[1]
            out.append("%s(rectangle (start %s %s) (end %s %s)"
                       % (ind, fmt(x1), fmt(y1), fmt(x2), fmt(y2)))
            out.append("%s  (stroke (width 0.254) (type default))" % ind)
            out.append("%s  (fill (type none))" % ind)
            out.append("%s)" % ind)
        elif item[0] == "poly":
            pts = item[1]
            out.append("%s(polyline" % ind)
            out.append("%s  (pts" % ind)
            for px, py in pts:
                out.append("%s    (xy %s %s)" % (ind, fmt(px), fmt(py)))
            out.append("%s  )" % ind)
            out.append("%s  (stroke (width 0.254) (type default))" % ind)
            out.append("%s  (fill (type none))" % ind)
            out.append("%s)" % ind)
    return out


def render_lib_symbol(sym):
    out = []
    name = "wapiti:%s" % sym["id"]
    head = '    (symbol "%s"' % name
    if sym["hide_num"]:
        head += " (pin_numbers hide)"
    head += " (pin_names (offset 0)) (in_bom yes) (on_board yes)"
    out.append(head)
    out.append('      (property "Reference" "%s" (at 0 5.08 0)' % sym["id"])
    out.append("        (effects (font (size 1.27 1.27)))")
    out.append("      )")
    out.append('      (property "Value" "%s" (at 0 -5.08 0)' % sym["id"])
    out.append("        (effects (font (size 1.27 1.27)))")
    out.append("      )")
    out.append('      (property "Footprint" "" (at 0 0 0)')
    out.append("        (effects (font (size 1.27 1.27)) hide)")
    out.append("      )")
    out.append('      (property "Datasheet" "" (at 0 0 0)')
    out.append("        (effects (font (size 1.27 1.27)) hide)")
    out.append("      )")
    short = sym["id"]
    out.append('      (symbol "%s_0_1"' % short)
    out.extend(render_body(sym["body"], "        "))
    out.append("      )")
    out.append('      (symbol "%s_1_1"' % short)
    for num, pname, px, py, pang, plen, ptype in sorted(sym["pins"], key=pin_sort_key):
        out.append('        (pin %s line (at %s %s %s) (length %s)'
                   % (ptype, fmt(px), fmt(py), pang, fmt(plen)))
        out.append('          (name "%s" (effects (font (size 1.27 1.27))))' % pname)
        out.append('          (number "%s" (effects (font (size 1.016 1.016))))' % num)
        out.append("        )")
    out.append("      )")
    out.append("    )")
    return out


def placed_symbol(sym, ref, value, sx, sy, rot, root_uuid, project, dnp=False):
    pins = []
    xs, ys = [], []
    for num, pname, px, py, pang, plen, ptype in sym["pins"]:
        rx, ry = rot_pt(px, py, rot)
        ax, ay = sx + rx, sy + ry
        pins.append((num, ax, ay))
        xs.append(ax)
        ys.append(ay)
    cx = (min(xs) + max(xs)) / 2.0
    out = []
    out.append('  (symbol (lib_id "wapiti:%s") (at %s %s %s) (unit 1)'
               % (sym["id"], fmt(sx), fmt(sy), rot))
    out.append("    (in_bom yes) (on_board yes) (dnp %s)" % ("yes" if dnp else "no"))
    out.append("    (uuid %s)" % u())
    out.append('    (property "Reference" "%s" (at %s %s %s)'
               % (ref, fmt(cx), fmt(min(ys) - 3.81), rot))
    out.append("      (effects (font (size 1.27 1.27)))")
    out.append("    )")
    out.append('    (property "Value" "%s" (at %s %s %s)'
               % (value, fmt(cx), fmt(max(ys) + 3.81), rot))
    out.append("      (effects (font (size 1.27 1.27)))")
    out.append("    )")
    fp = FOOTPRINTS.get(sym["id"], "")
    out.append('    (property "Footprint" "%s" (at %s %s 0)' % (fp, fmt(sx), fmt(sy)))
    out.append("      (effects (font (size 1.27 1.27)) hide)")
    out.append("    )")
    out.append('    (property "Datasheet" "" (at %s %s 0)' % (fmt(sx), fmt(sy)))
    out.append("      (effects (font (size 1.27 1.27)) hide)")
    out.append("    )")
    for num, ax, ay in pins:
        out.append('    (pin "%s" (uuid %s))' % (num, u()))
    out.append("    (instances")
    out.append('      (project "%s"' % project)
    out.append('        (path "/%s" (reference "%s") (unit 1))' % (root_uuid, ref))
    out.append("      )")
    out.append("    )")
    out.append("  )")
    return out, {n: (ax, ay) for (n, ax, ay) in pins}


def render_schematic(out_path, title, project, placements, wires,
                     labels, junctions, texts, no_connects, rev="0.1"):
    root_uuid = u()
    L = []
    L.append("(kicad_sch (version 20230121) (generator eeschema)")
    L.append("")
    L.append("  (uuid %s)" % root_uuid)
    L.append("")
    L.append('  (paper "A4")')
    L.append("")
    L.append("  (title_block")
    L.append('    (title "%s")' % title)
    L.append('    (date "2026-10-04")')
    L.append('    (rev "%s")' % rev)
    L.append('    (company "wapiti")')
    L.append("  )")
    L.append("")
    L.append("  (lib_symbols")
    used = []
    for ref, sid, at, value in placements:
        if sid not in used:
            used.append(sid)
    for sid in used:
        L.extend(render_lib_symbol(SYMBOLS[sid]))
    L.append("  )")
    L.append("")
    for x, y in junctions:
        L.append("  (junction (at %s %s) (diameter 1.016) (color 0 0 0 0)" % (fmt(x), fmt(y)))
        L.append("    (uuid %s)" % u())
        L.append("  )")
        L.append("")
    for x1, y1, x2, y2 in wires:
        L.append("  (wire (pts (xy %s %s) (xy %s %s))" % (fmt(x1), fmt(y1), fmt(x2), fmt(y2)))
        L.append("    (stroke (width 0) (type solid))")
        L.append("    (uuid %s)" % u())
        L.append("  )")
        L.append("")
    for txt, x, y, rot, size in texts:
        L.append('  (text "%s" (at %s %s %s)' % (txt, fmt(x), fmt(y), rot))
        L.append("    (effects (font (size %s %s)))" % (fmt(size), fmt(size)))
        L.append("    (uuid %s)" % u())
        L.append("  )")
        L.append("")
    for name, x, y, rot in labels:
        L.append('  (label "%s" (at %s %s %s) (fields_autoplaced)' % (name, fmt(x), fmt(y), rot))
        L.append("    (effects (font (size 1.27 1.27)) (justify left bottom))")
        L.append("    (uuid %s)" % u())
        L.append("  )")
        L.append("")
    all_pins = {}
    for ref, sid, at, value in placements:
        sx, sy, rot = at
        dnp = (ref, sid) in DNP_REFS
        block, pins = placed_symbol(SYMBOLS[sid], ref, value, sx, sy, rot, root_uuid, project, dnp=dnp)
        L.extend(block)
        L.append("")
        all_pins[ref] = pins
    for x, y in no_connects:
        L.append("  (no_connect (at %s %s) (uuid %s))" % (fmt(x), fmt(y), u()))
        L.append("")
    L.append("  (sheet_instances")
    L.append('    (path "/" (page "1"))')
    L.append("  )")
    L.append(")")
    L.append("")
    with open(out_path, "w") as f:
        f.write("\n".join(L))
    return out_path, all_pins


class Sheet:
    """Tip lookup + wiring helpers (lugtrax conventions)."""

    def __init__(self, placements):
        self.place = placements
        self.tips = {}
        for ref, sid, at, value in placements:
            sx, sy, rot = at
            for pnum, pname, px, py, pang, plen, ptype in SYMBOLS[sid]["pins"]:
                rx, ry = rot_pt(px, py, rot)
                self.tips[(ref, str(pnum))] = (sx + rx, sy + ry)

    def tip(self, ref, num):
        return self.tips[(ref, str(num))]

    def chain(self, pins):
        """Orthogonal wire chain tip-to-tip: A -> B -> C... L-shaped via (B.x, A.y)."""
        wires = []
        pts = [self.tip(r, n) for r, n in pins]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            if abs(y1 - y2) < 1e-6 or abs(x1 - x2) < 1e-6:
                wires.append((x1, y1, x2, y2))
            else:
                wires.append((x1, y1, x2, y1))
                wires.append((x2, y1, x2, y2))
        return wires

    def label(self, name, ref, num, rot=0):
        x, y = self.tip(ref, num)
        return (name, x, y, rot)


# ---------------------------------------------------------------------------
# POWER sheet. Series chains wired; everything else net labels at pin tips.
# ---------------------------------------------------------------------------

POWER_PLACE = [
    ("BT1", "BT", (30, 60, 0), "2S NMC smart pack"),
    ("BT2", "BT", (30, 78, 0), "12xAA Li-FeS2 6S2P"),
    ("BT3", "BT", (30, 94, 0), "CR2032 reserve"),
    ("C1", "CP", (52, 94, 0), "5F supercap"),
    ("F1", "F", (55, 63.81, 0), "2A PTC"),
    ("F2", "F", (55, 81.81, 0), "2A PTC"),
    ("D1", "D", (75, 63.81, 0), "SS54"),
    ("D3", "D", (75, 81.81, 0), "SS54"),
    ("D2", "TVS", (110, 25, 0), "SMBJ18A"),
    ("J1", "CONN2", (95, 40, 0), "solar 7W"),
    ("U4", "LS", (120, 40, 0), "solar interlock"),
    ("D4", "D", (145, 40, 0), "SS54"),
    ("U1", "BUCK", (145, 60, 0), "3.8V buck"),
    ("L1", "L", (165, 57.46, 0), "4.7uH"),
    ("C2", "CP", (185, 57.46, 0), "100u/10V"),
    ("U2", "LS", (145, 75, 0), "cam rail"),
    ("U3", "LS", (175, 75, 0), "modem rail"),
    ("R7", "R", (130, 47, 90), "100k EN"),
    ("R5", "R", (160, 45, 90), "1M FB hi"),
    ("R6", "R", (175, 45, 90), "523k FB lo"),
    ("R8", "R", (135, 47, 90), "100k EN pd"),
    ("R10", "R", (165, 47, 90), "100k EN pd"),
    ("R9", "R", (105, 30, 0), "100k SOLAR pd"),
    ("U5", "GAUGE", (120, 88, 0), "BQ27441 fuel gauge"),
    ("R4", "R", (95, 88, 0), "100k NTC"),
]

POWER = Sheet(POWER_PLACE)

pw, pj, pl = [], [], []

# Series chains (same-row direct wires)
pw += POWER.chain([("BT1", "1"), ("F1", "1")])
pw += POWER.chain([("F1", "2"), ("D1", "1")])
pw += POWER.chain([("BT2", "1"), ("F2", "1")])
pw += POWER.chain([("F2", "2"), ("D3", "1")])
pw += POWER.chain([("U1", "3"), ("L1", "1")])

# Raw-rail labels on every tip of each wired component (lugtrax discipline)
for net, ref, num in [
    ("V_PACK_RAW", "BT1", "1"), ("V_PACK_RAW", "F1", "1"),
    ("V_PACK_RAW", "F1", "2"), ("V_PACK_RAW", "D1", "1"),
    ("V_AA_RAW", "BT2", "1"), ("V_AA_RAW", "F2", "1"),
    ("V_AA_RAW", "F2", "2"), ("V_AA_RAW", "D3", "1"),
    ("VSYS_RAW", "D1", "2"), ("VSYS_RAW", "D3", "2"),
    ("VSYS_RAW", "D4", "2"), ("VSYS_RAW", "C1", "1"),
    ("VSYS_RAW", "U1", "1"), ("VSYS_RAW", "D2", "1"),
    ("VSYS_SW", "U1", "3"), ("VSYS_SW", "L1", "1"),
    ("V_SYS", "L1", "2"), ("V_SYS", "C2", "1"), ("V_SYS", "U2", "1"),
    ("V_SYS", "U3", "1"), ("V_SYS", "U5", "1"), ("V_SYS", "R5", "1"),
    ("V_SYS", "R7", "1"),
    ("EN_BUCK", "U1", "2"), ("EN_BUCK", "R7", "2"),
    ("FB", "U1", "5"), ("FB", "R5", "2"), ("FB", "R6", "1"),
    ("V_CAM", "U2", "3"),
    ("V_MODEM", "U3", "3"),
    ("EN_CAM", "U2", "2"), ("EN_CAM", "R8", "1"),
    ("EN_MODEM", "U3", "2"), ("EN_MODEM", "R10", "1"),
    ("SOLAR_IN", "J1", "1"), ("SOLAR_IN", "U4", "1"),
    ("SOLAR_SW", "U4", "3"), ("SOLAR_SW", "D4", "1"),
    ("SOLAR_OK", "U4", "2"), ("SOLAR_OK", "R9", "1"),
    ("V_RES", "BT3", "1"),
    ("PACK_TEMP", "R4", "1"),
    ("SDA", "U5", "3"), ("SCL", "U5", "4"),
    ("GAUGE_INT", "U5", "5"),
    ("V_PACK_RAW", "U5", "6"),
    ("SRN", "U5", "7"),
    ("GND", "BT1", "2"), ("GND", "BT2", "2"), ("GND", "BT3", "2"),
    ("GND", "C1", "2"), ("GND", "C2", "2"), ("GND", "D2", "2"),
    ("GND", "U1", "4"), ("GND", "U2", "4"), ("GND", "U3", "4"),
    ("GND", "U4", "4"), ("GND", "R4", "2"), ("GND", "R6", "2"),
    ("GND", "R8", "2"), ("GND", "R9", "2"), ("GND", "R10", "2"),
    ("GND", "U5", "2"), ("GND", "J1", "2"),
]:
    pl.append(POWER.label(net, ref, num))

POWER_WIRES, POWER_JUNCTIONS, POWER_LABELS = pw, pj, pl
POWER_NO_CONNECT = []

POWER_TEXTS = [
    ("wapiti POWER - smart pack / 12xAA Li-FeS2 / reserve cell + solar interlock", 25, 20, 0, 2.54),
    ("BT1 smart pack (pack-ID + fuel gauge via SDA/SCL); BT2 12xAA Li-FeS2 6S2P tray (natively -40C).", 25, 27, 0, 1.27),
    ("D1/D3/D4 SS54 OR-ing into VSYS_RAW; C1 5F supercap = LTE TX burst + mitten-swap ride-through.", 25, 31, 0, 1.27),
    ("U1 buck -> V_SYS 3.8V. U2/U3 load switches: EN_CAM / EN_MODEM from C6, 100k pull-downs (R8/R10).", 25, 100, 0, 1.27),
    ("Solar (J1) charges ONLY via U4 interlock: C6 asserts SOLAR_OK when pack temp > 0C (PWR-08).", 25, 104, 0, 1.27),
    ("U5 BQ27441 fuel gauge + pack thermistor R4: weather-adjusted forecast inputs.", 25, 108, 0, 1.27),
    ("BT3 CR2032 reserve rail V_RES feeds GNSS anti-theft + RTC during pack swaps.", 25, 112, 0, 1.27),
]

# ---------------------------------------------------------------------------
# RADIO sheet. Labels everywhere; antennas are label-linked (tips face away).
# ---------------------------------------------------------------------------

RADIO_PLACE = [
    ("U1", "MODEM", (80, 55, 0), "EG915U LTE Cat-1bis + GNSS"),
    ("U2", "SIM", (125, 65, 0), "eSIM multi-IMSI"),
    ("C3", "CP", (55, 55, 0), "100u/10V"),
    ("C4", "C", (55, 65, 0), "100n"),
    ("R11", "R", (45, 38, 0), "10k PWRKEY"),
    ("J2", "CONN2", (105, 35, 0), "SMA LTE"),
    ("ANT2", "ANT", (120, 35, 0), "GNSS patch"),
    ("J3", "USB", (55, 90, 0), "USB-C service"),
]

RADIO = Sheet(RADIO_PLACE)

rw, rj, rl = [], [], []

# Antennas: modem top pins point up, antenna pins point down - labels avoid
# wires crossing the modem body (lugtrax convention).
rl.append(RADIO.label("LTE_ANT", "U1", "12", rot=270))
rl.append(RADIO.label("LTE_ANT", "J2", "1"))
rl.append(RADIO.label("GNSS_ANT", "U1", "13", rot=270))
rl.append(RADIO.label("GNSS_ANT", "ANT2", "1"))

for net, ref, num in [
    ("V_MODEM", "U1", "1"), ("V_MODEM", "C3", "1"), ("V_MODEM", "C4", "1"),
    ("GND", "U1", "2"), ("GND", "U1", "11"), ("GND", "U1", "14"),
    ("GND", "C3", "2"), ("GND", "C4", "2"),
    ("GND", "U2", "4"), ("GND", "R11", "2"), ("GND", "J2", "2"),
    ("GND", "J3", "4"),
    ("PWRKEY", "U1", "5"), ("PWRKEY", "R11", "1"),
    ("MODEM_TX", "U1", "3"), ("MODEM_RX", "U1", "4"), ("RI", "U1", "6"),
    ("SIM_VDD", "U1", "7"), ("SIM_VDD", "U2", "1"),
    ("SIM_DATA", "U1", "8"), ("SIM_DATA", "U2", "6"),
    ("SIM_CLK", "U1", "9"), ("SIM_CLK", "U2", "3"),
    ("SIM_RST", "U1", "10"), ("SIM_RST", "U2", "2"),
    ("USB_DP", "U1", "15"), ("USB_DP", "J3", "3"),
    ("USB_DM", "U1", "16"), ("USB_DM", "J3", "2"),
    ("PERST", "U1", "17"),
]:
    rl.append(RADIO.label(net, ref, num))

RADIO_WIRES, RADIO_JUNCTIONS, RADIO_LABELS = rw, rj, rl
RADIO_NO_CONNECT = [RADIO.tip("U2", "5"), RADIO.tip("J3", "1"),
                    RADIO.tip("J3", "5"), RADIO.tip("J3", "6")]

RADIO_TEXTS = [
    ("wapiti RADIO - EG915U LTE Cat-1bis + GNSS, eSIM multi-IMSI, SMA LTE antenna", 40, 25, 0, 2.54),
    ("Cat-1bis (5M UL) is the photo-delivery class; LTE-M variant is an S6 study (deep rural).", 40, 32, 0, 1.27),
    ("J2 = user-replaceable SMA (CAM-14 / competitive-analysis row 16).", 40, 36, 0, 1.27),
    ("GNSS patch ANT2 under the lid RF membrane (0.8 mm plastic-only; chassis keep-out).", 40, 84, 0, 1.27),
    ("J3 USB-C service: modem firmware + C6 flashing (shared USB_DP/USB_DM).", 40, 88, 0, 1.27),
    ("PWRKEY (10k R11) + RESET_N (PERST from C6 GPIO19); RI reserved for ring wake.", 40, 92, 0, 1.27),
]

# ---------------------------------------------------------------------------
# CAM sheet. SoC + sensor + storage + LCD + IR arrays on MOSFET low-side
# switches (gate pulldowns keep LEDs dark until the SoC asserts).
# ---------------------------------------------------------------------------

CAM_PLACE = [
    ("U1", "SOC", (85, 60, 0), "SSC377Q"),
    ("U2", "SENSOR", (130, 42, 0), "IMX415 module"),
    ("U3", "EMMC", (130, 72, 0), "eMMC 8GB"),
    ("J1", "SDCARD", (55, 95, 0), "microSD"),
    ("U4", "LCD", (50, 40, 0), "LCD 2in SPI"),
    ("D1", "LEDARR", (30, 30, 0), "IR 940nm x24"),
    ("D2", "LEDARR", (30, 45, 0), "IR 850nm x24"),
    ("Q1", "MOSFET", (55, 30, 0), "IR940 switch"),
    ("Q2", "MOSFET", (55, 45, 0), "IR850 switch"),
    ("C7", "C", (60, 60, 0), "10u"),
    ("C8", "C", (60, 70, 0), "100n"),
    ("R14", "R", (42, 22, 0), "100k gate pd"),
    ("R15", "R", (42, 52, 0), "100k gate pd"),
]

CAM = Sheet(CAM_PLACE)

cw, cj, cl = [], [], []

# IR strings: anodes on V_CAM (label), cathodes to MOSFET drains (labels).
cl.append(CAM.label("V_CAM", "D1", "1"))
cl.append(CAM.label("IR940_K", "D1", "2"))
cl.append(CAM.label("IR940_K", "Q1", "2"))
cl.append(CAM.label("V_CAM", "D2", "1"))
cl.append(CAM.label("IR850_K", "D2", "2"))
cl.append(CAM.label("IR850_K", "Q2", "2"))

for net, ref, num in [
    ("V_CAM", "U1", "1"), ("V_CAM", "C7", "1"), ("V_CAM", "C8", "1"),
    ("V_CAM", "U3", "1"), ("V_CAM", "J1", "1"), ("V_CAM", "U4", "1"),
    ("V_CAM", "U2", "1"),
    ("CSI_P", "U1", "3"), ("CSI_P", "U2", "3"),
    ("CSI_N", "U1", "4"), ("CSI_N", "U2", "4"),
    ("CAM_SDA", "U1", "5"), ("CAM_SDA", "U2", "5"),
    ("CAM_SCL", "U1", "6"), ("CAM_SCL", "U2", "6"),
    ("SENS_CLK", "U1", "7"), ("SENS_CLK", "U2", "7"),
    ("STANDBY", "U1", "8"), ("STANDBY", "U2", "8"),
    ("IR_940", "U1", "11"), ("IR_940", "Q1", "1"), ("IR_940", "R14", "1"),
    ("IR_850", "U1", "12"), ("IR_850", "Q2", "1"), ("IR_850", "R15", "1"),
    ("LCD_SCK", "U1", "13"), ("LCD_SCK", "U4", "3"),
    ("LCD_MOSI", "U1", "14"), ("LCD_MOSI", "U4", "4"),
    ("LCD_DC", "U1", "15"), ("LCD_DC", "U4", "5"),
    ("LCD_RST", "U1", "16"), ("LCD_RST", "U4", "6"),
    ("LCD_BKL", "U1", "17"), ("LCD_BKL", "U4", "7"),
    ("EMMC_CMD", "U1", "18"), ("EMMC_CMD", "U3", "3"),
    ("EMMC_CLK", "U1", "19"), ("EMMC_CLK", "U3", "4"),
    ("EMMC_DAT", "U1", "20"), ("EMMC_DAT", "U3", "5"),
    ("SD_CD", "U1", "21"), ("SD_CD", "J1", "6"),
    ("SD_CLK", "U1", "22"), ("SD_CLK", "J1", "4"),
    ("SD_CMD", "U1", "23"), ("SD_CMD", "J1", "3"),
    ("SD_DAT", "U1", "24"), ("SD_DAT", "J1", "5"),
    ("UART_RX", "U1", "9"), ("UART_TX", "U1", "10"),
    ("GND", "U1", "2"), ("GND", "U1", "25"), ("GND", "U2", "2"),
    ("GND", "U3", "2"), ("GND", "U3", "6"), ("GND", "J1", "2"),
    ("GND", "U4", "2"), ("GND", "Q1", "3"), ("GND", "Q2", "3"),
    ("GND", "C7", "2"), ("GND", "C8", "2"),
    ("GND", "R14", "2"), ("GND", "R15", "2"),
]:
    cl.append(CAM.label(net, ref, num))

CAM_WIRES, CAM_JUNCTIONS, CAM_LABELS = cw, cj, cl
CAM_NO_CONNECT = []

CAM_TEXTS = [
    ("wapiti CAM - SSC377Q + IMX415 (4K) + eMMC/microSD + 2in LCD + dual IR arrays", 40, 15, 0, 2.54),
    ("IR_940 (no-glow, 80ft) and IR_850 (low-glow, 96ft) are app-selectable (CAM-05).", 40, 22, 0, 1.27),
    ("Gate pulldowns R14/R15 keep both arrays dark through boot until the SoC asserts.", 40, 100, 0, 1.27),
    ("SD + eMMC share nothing: eMMC = OS + buffer, microSD = overflow (UHS-I, no U3-only quirk).", 40, 104, 0, 1.27),
    ("UART_RX/TX link to the C6 wake supervisor (mcu sheet); USB service is on the radio sheet.", 40, 108, 0, 1.27),
]

# ---------------------------------------------------------------------------
# MCU sheet. C6 = always-on wake supervisor (heartbeat owner, PIR watcher,
# rail switches, fuel-gauge host) + BLE/Wi-Fi pairing radio.
# ---------------------------------------------------------------------------

MCU_PLACE = [
    ("U1", "MCU", (80, 60, 0), "ESP32-C6-WROOM-1"),
    ("U2", "ACCEL", (135, 62, 0), "LIS2DW12"),
    ("U3", "PIR", (135, 82, 0), "AS312 PIR"),
    ("U4", "RADAR", (105, 88, 0), "LD2410 24GHz"),
    ("C9", "C", (55, 60, 0), "10u"),
    ("C10", "C", (55, 70, 0), "100n"),
    ("R20", "R", (60, 40, 90), "10k EN"),
    ("R21", "R", (100, 40, 90), "10k SDA"),
    ("R22", "R", (110, 40, 90), "10k SCL"),
    ("R25", "R", (150, 45, 0), "1k"),
    ("D3", "LEDARR", (165, 45, 0), "status LED"),
    ("SW1", "SW", (45, 45, 0), "reset"),
    ("J1", "HDR", (145, 25, 0), "prog 2x03"),
    ("J2", "USB", (55, 92, 0), "USB-C service"),
]

MCU = Sheet(MCU_PLACE)

mw, mj, ml = [], [], []

for net, ref, num in [
    ("V_MCU", "U1", "1"), ("V_MCU", "C9", "1"), ("V_MCU", "C10", "1"),
    ("V_MCU", "R20", "1"), ("V_MCU", "R21", "1"), ("V_MCU", "R22", "1"),
    ("V_MCU", "J1", "1"), ("V_MCU", "U2", "1"), ("V_MCU", "U3", "1"),
    ("V_MCU", "U4", "1"), ("V_MCU", "U4", "4"),
    ("GND", "U1", "18"), ("GND", "U1", "19"), ("GND", "U2", "2"),
    ("GND", "U3", "3"), ("GND", "U4", "2"), ("GND", "C9", "2"),
    ("GND", "C10", "2"), ("GND", "J1", "5"), ("GND", "J2", "4"),
    ("GND", "SW1", "2"), ("GND", "R25", "2"), ("GND", "D3", "2"),
    ("EN", "U1", "2"), ("EN", "R20", "2"), ("EN", "J1", "2"), ("EN", "SW1", "1"),
    ("SDA", "U1", "5"), ("SDA", "U2", "3"), ("SDA", "R21", "2"),
    ("SCL", "U1", "6"), ("SCL", "U2", "4"), ("SCL", "R22", "2"),
    ("GAUGE_INT", "U1", "8"),
    ("PIR_OUT", "U1", "3"), ("PIR_OUT", "U3", "2"),
    ("RADAR_OUT", "U1", "4"), ("RADAR_OUT", "U4", "3"),
    ("EN_CAM", "U1", "9"),
    ("PERST", "U1", "10"),
    ("UART_RX", "U1", "11"), ("UART_TX", "U1", "12"),
    ("UART_RX", "J1", "3"), ("UART_TX", "J1", "4"),
    ("USB_DP", "U1", "14"), ("USB_DP", "J2", "3"),
    ("USB_DM", "U1", "13"), ("USB_DM", "J2", "2"),
    ("SOLAR_OK", "U1", "15"),
    ("BOOT", "U1", "7"), ("BOOT", "J1", "6"),
    ("LED_STAT", "U1", "17"), ("LED_STAT", "R25", "1"), ("LED_STAT", "D3", "1"),
    ("ACCEL_INT", "U1", "16"), ("ACCEL_INT", "U2", "5"),
]:
    ml.append(MCU.label(net, ref, num))

MCU_WIRES, MCU_JUNCTIONS, MCU_LABELS = mw, mj, ml
MCU_NO_CONNECT = [MCU.tip("U1", "16"), MCU.tip("J2", "1"),
                  MCU.tip("J2", "5"), MCU.tip("J2", "6")]

MCU_TEXTS = [
    ("wapiti MCU - ESP32-C6 wake supervisor + BLE/Wi-Fi pairing + sensors", 45, 15, 0, 2.54),
    ("C6 owns the heartbeat (HB-01..08): it watches PIR/radar, wakes the SoC rail", 45, 22, 0, 1.27),
    ("(EN_CAM via GPIO18), hosts the fuel gauge on I2C, and gates solar charging", 45, 26, 0, 1.27),
    ("(SOLAR_OK, pack-temp interlock < 0C = PWR-08). BLE pairs the app (PR-03).", 45, 30, 0, 1.27),
    ("U4 mmWave radar is populated on the Pro reference (value SKU: DNP + regen).", 45, 96, 0, 1.27),
    ("J2 USB-C service shares USB_DP/DM with the modem (radio sheet); CC 5.1k on layout.", 45, 100, 0, 1.27),
    ("J1 2x03: 3V3, EN, TX, RX, GND, IO9(BOOT) for factory programming.", 45, 104, 0, 1.27),
]


# ---------------------------------------------------------------------------
# Root sheet
# ---------------------------------------------------------------------------

def render_root(out_path, project):
    root_uuid = u()
    L = []
    L.append("(kicad_sch (version 20260306) (generator eeschema)")
    L.append('  (generator_version "10.0")')
    L.append("")
    L.append("  (uuid %s)" % root_uuid)
    L.append("")
    L.append('  (paper "A4")')
    L.append("")
    L.append("  (title_block")
    L.append('    (title "wapiti trail camera - root")')
    L.append('    (date "2026-10-04")')
    L.append('    (rev "0.1")')
    L.append('    (company "wapiti")')
    L.append("  )")
    L.append("")
    sheets = [
        ("power", 25.4, 25.4, 190.5, 63.5),
        ("radio", 25.4, 102.87, 190.5, 58.42),
        ("cam", 25.4, 175.26, 190.5, 58.42),
        ("mcu", 25.4, 236.22, 190.5, 55.0),
    ]
    page = 2
    for name, sx, sy, w, h in sheets:
        sheet_uuid = u()
        L.append("  (sheet")
        L.append("    (at %s %s) (size %s %s)" % (fmt(sx), fmt(sy), fmt(w), fmt(h)))
        L.append("    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)")
        L.append("    (fields_autoplaced yes)")
        L.append("    (stroke (width 0.1524) (type solid))")
        L.append("    (fill (color 0 0 0 0))")
        L.append("    (uuid %s)" % sheet_uuid)
        L.append('    (property "Sheetname" "%s"' % name)
        L.append("      (at %s %s 0) (show_name no) (do_not_autoplace no)" % (fmt(sx), fmt(sy)))
        L.append("      (effects (font (size 1.27 1.27)) (justify left bottom))")
        L.append("    )")
        L.append('    (property "Sheetfile" "%s.kicad_sch"' % name)
        L.append("      (at %s %s 0) (show_name no) (do_not_autoplace no)" % (fmt(sx), fmt(sy + h)))
        L.append("      (effects (font (size 1.27 1.27)) (justify left top))")
        L.append("    )")
        L.append("    (instances")
        L.append('      (project "%s"' % project)
        L.append('        (path "/%s"' % root_uuid)
        L.append('          (page "%d")' % page)
        L.append("        )")
        L.append("      )")
        L.append("    )")
        L.append("  )")
        L.append("")
        page += 1
    L.append("  (sheet_instances")
    L.append('    (path "/" (page "1"))')
    L.append("  )")
    L.append(")")
    L.append("")
    with open(out_path, "w") as f:
        f.write("\n".join(L))
    return out_path


# ---------------------------------------------------------------------------
# S-expression structural self-check
# ---------------------------------------------------------------------------

def sexp_parse(text):
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


def main():
    here = os.path.dirname(os.path.abspath(__file__))

    sheets = [
        ("power", "wapiti Power: pack/AA/reserve + supercap + buck + solar interlock + gauge",
         POWER_PLACE, POWER_WIRES, POWER_LABELS, POWER_JUNCTIONS, POWER_TEXTS, POWER_NO_CONNECT),
        ("radio", "wapiti Radio: EG915U LTE Cat-1bis + GNSS + eSIM + SMA",
         RADIO_PLACE, RADIO_WIRES, RADIO_LABELS, RADIO_JUNCTIONS, RADIO_TEXTS, RADIO_NO_CONNECT),
        ("cam", "wapiti Camera: SSC377Q + IMX415 + storage + LCD + IR arrays",
         CAM_PLACE, CAM_WIRES, CAM_LABELS, CAM_JUNCTIONS, CAM_TEXTS, CAM_NO_CONNECT),
        ("mcu", "wapiti MCU: ESP32-C6 supervisor + PIR + radar + accel",
         MCU_PLACE, MCU_WIRES, MCU_LABELS, MCU_JUNCTIONS, MCU_TEXTS, MCU_NO_CONNECT),
    ]
    for name, title, place, wires, labels, junctions, texts, noconn in sheets:
        path, pins = render_schematic(
            os.path.join(here, "%s.kicad_sch" % name), title, "wapiti",
            place, wires, labels, junctions, texts, noconn)
        sexp_parse(open(path).read())
        print("wrote %s (%d pins placed)" % (path, sum(len(v) for v in pins.values())))

    root = render_root(os.path.join(here, "wapiti.kicad_sch"), "wapiti")
    sexp_parse(open(root).read())
    print("wrote %s" % root)
    print("done.")


if __name__ == "__main__":
    main()

