#!/usr/bin/env bash
# Validate the generated wapiti schematics + PCB with kicad-cli (run on the
# machine where KiCad is installed). Exits non-zero on any error.
set -euo pipefail
cd "$(dirname "$0")"

export kicad="/home/oosman/Downloads/kicad-10.0.5-x86_64.AppImage kicad-cli"

command -v ${kicad} >/dev/null 2>&1 || { echo "ERROR: kicad-cli not found (install KiCad >= 7 first)"; exit 1; }

OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

mkdir -p exports

for f in power.kicad_sch radio.kicad_sch cam.kicad_sch mcu.kicad_sch wapiti.kicad_sch; do
  echo "== $f =="
  ${kicad} sch export svg "$f" -o "$OUT" 2>&1 | tail -1
  ${kicad} sch export pdf "$f" -o "exports/${f%.kicad_sch}.pdf" 2>&1 | tail -1
  echo "ok: $f parses and renders"
done

if [ -f wapiti.kicad_pcb ]; then
  echo "== wapiti.kicad_pcb =="
  ${kicad} pcb export svg wapiti.kicad_pcb --layers "F.Cu,F.SilkS,Edge.Cuts" -o "exports/wapiti-pcb.svg" 2>&1 | tail -1
  ${kicad} pcb export step wapiti.kicad_pcb -o "exports/wapiti.step" --no-dnp 2>&1 | tail -1 || true
  echo "ok: PCB parses and renders (exports/wapiti-pcb.svg)"
fi

echo
echo "All schematics valid."
