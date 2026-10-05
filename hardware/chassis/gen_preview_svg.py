#!/usr/bin/env python3
"""Render SVG previews of the wapiti chassis from the generated STLs.

Pure Python (no Blender needed). Painter's algorithm over the STL triangles
with simple Lambert shading. Opens in any browser / Inkscape.

Run:  python3 gen_preview_svg.py     (after gen_chassis_stl.py)
Out:  ./out/preview.svg       isometric: base + lid up +45, drawer pulled -Y
      ./out/preview-plan.svg  top-down view of the base interior
      ./out/preview-side.svg  +X side view (strap slots)
"""

import math
import os
import struct

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
CANVAS_W, CANVAS_H = 1000, 700
MARGIN = 12.0


def load_stl(path):
    data = open(path, "rb").read()
    n = struct.unpack("<I", data[80:84])[0]
    tris = []
    for i in range(n):
        off = 84 + i * 50
        v = []
        for k in range(3):
            x, y, z = struct.unpack("<3f", data[off + 12 + k * 12: off + 24 + k * 12])
            v.append((x, y, z))
        tris.append(v)
    return tris


def iso(p):
    """Isometric projection. View axis is (1,1,1): larger x+y+z is CLOSER
    to the camera (paint far first)."""
    x, y, z = p
    sx = (x - y) * math.cos(math.radians(30))
    sy = (x + y) * math.sin(math.radians(30)) - z
    return sx, sy


def plan(p):
    """Top-down view: screen-up = +y (USB wall +Y at top, drawer mouth -Y at
    bottom). Depth is z only: camera above, larger z is closer."""
    x, y, z = p
    return x, -y


def right(p):
    """Side view (+X looking -X): screen-up = +z, screen-right = -y (drawer
    mouth -Y at right). Depth is x only: camera looks from +X, larger x is
    closer. Shows the side-wall strap slots."""
    x, y, z = p
    return -y, -z


def depth_iso(t):
    return sum(t[0]) / 3.0 + sum(t[1]) / 3.0 + sum(t[2]) / 3.0


def depth_plan(t):
    return (t[0][2] + t[1][2] + t[2][2]) / 3.0


def depth_right(t):
    return (t[0][0] + t[1][0] + t[2][0]) / 3.0


def shade(tri):
    ax, ay, az = tri[0]
    bx, by, bz = tri[1]
    cx, cy, cz = tri[2]
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    l = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    nz /= l
    return max(0.25, min(1.0, 0.35 + 0.65 * abs(nz)))


def fit_bounds(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1 = min(xs) - MARGIN, max(xs) + MARGIN
    y0, y1 = min(ys) - MARGIN, max(ys) + MARGIN
    vw, vh = x1 - x0, y1 - y0
    ar = CANVAS_W / CANVAS_H
    if vw / vh < ar:
        grow = ar * vh - vw
        x0 -= grow / 2.0
        vw += grow
    else:
        grow = (1.0 / ar) * vw - vh
        y0 -= grow / 2.0
        vh += grow
    return x0, y0, vw, vh


def write_svg(path, title, bounds, shells):
    x0, y0, vw, vh = bounds
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="%.2f %.2f %.2f %.2f">' % (CANVAS_W, CANVAS_H, x0, y0, vw, vh),
           '<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#101014"/>'
           % (x0, y0, vw, vh),
           '<text x="%.2f" y="%.2f" fill="#9aa" font-size="14">%s</text>'
           % (x0 + 10, y0 + 20, title)]
    for tris, proj, depth_fn, color in shells:
        parts = []
        for t in sorted(tris, key=depth_fn):
            pts = [proj(v) for v in t]
            d = shade(t)
            c = tuple(int(255 * ch * d) for ch in color)
            parts.append('<polygon points="%s" fill="rgb(%d,%d,%d)" stroke="none"/>'
                         % (" ".join("%.1f,%.1f" % p for p in pts), *c))
        out.append("\n".join(parts))
    out.append("</svg>")
    open(path, "w").write("\n".join(out))
    print("wrote %s" % path)


def main():
    base = load_stl(os.path.join(OUT, "wapiti-base.stl"))
    lid = load_stl(os.path.join(OUT, "wapiti-lid.stl"))
    tray = load_stl(os.path.join(OUT, "wapiti-tray.stl"))

    # isometric: base at origin, lid +45 mm in z, drawer pulled 25 mm -Y
    LIFT, PULL = 45.0, 25.0
    pts = []
    for tris, oz, oy in ((base, 0.0, 0.0), (lid, LIFT, 0.0), (tray, 0.0, -PULL)):
        for t in tris:
            for v in t:
                pts.append(iso((v[0], v[1] + oy, v[2] + oz)))
    bounds = fit_bounds(pts)
    write_svg(os.path.join(OUT, "preview.svg"),
              "wapiti chassis - base + lid (+45 z) + drawer pulled -Y (25 mm)",
              bounds,
              [(base, lambda v: iso((v[0], v[1], v[2])), depth_iso, (0.35, 0.38, 0.45)),
               (tray, lambda v: iso((v[0], v[1] - PULL, v[2])), depth_iso, (0.95, 0.45, 0.15)),
               (lid, lambda v: iso((v[0], v[1], v[2] + LIFT)), depth_iso, (0.30, 0.33, 0.38))])

    # plan view: base only, so the interior layout is inspectable
    pts = [plan(v) for t in base for v in t]
    write_svg(os.path.join(OUT, "preview-plan.svg"),
              "wapiti base, top-down (USB wall +Y top, drawer mouth -Y bottom)",
              fit_bounds(pts),
              [(base, plan, depth_plan, (0.35, 0.38, 0.45))])

    # right view: base only — strap slots visible in the near +X wall
    pts = [right(v) for t in base for v in t]
    write_svg(os.path.join(OUT, "preview-side.svg"),
              "wapiti base, +X side view (strap slots y -11..11, z 22..25.5; "
              "drawer mouth -Y at right)",
              fit_bounds(pts),
              [(base, right, depth_right, (0.35, 0.38, 0.45))])


if __name__ == "__main__":
    main()
