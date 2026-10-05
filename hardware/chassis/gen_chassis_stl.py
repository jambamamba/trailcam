#!/usr/bin/env python3
"""Generate the wapiti chassis as STL + OBJ (pure Python, no CAD needed).

Two-shell + drawer chassis matching project-plan §4 (power) and §4.13
(mitten-swap wedge) for the 100x65 PCB. Geometry is CONSTRUCTIVE (no
booleans): panels are emitted as sub-boxes tiled around their openings,
bosses/posts as tubes, so meshes are watertight-enough for slicers and
clean in Blender/CAD.

  wapiti-base.stl - floor + walls (+Y USB-C cutout, -Y drawer mouth,
                    rear wall strap slots for tree webbing)
                    + 4 PCB boss tubes + drawer rails/guides + 4 screw posts
  wapiti-lid.stl  - top plate (lens port + seat boss, PIR dome hole, IR
                    windows, LCD window, GNSS + radar 0.8 mm membranes,
                    button hole, LED pipe, SMA bulkhead hole,
                    1/4-20 tripod boss)
                    + skirt + 4 screw bosses
  wapiti-tray.stl - hi-vis battery drawer: rails floor, smart-pack insert
                    (2S NMC, pack-ID + BQ27441), full-width paddle lever
                    with grip groove. 12xAA / LTO sleds are alternate
                    inserts for the same rails (§4.13).

Overall assembled: 108 x 74 x 33 mm (paddle stands 3 mm proud of the -Y
face). z=0 at the floor bottom. Board: 100x65 on 17.5 mm bosses (board
bottom z=19.5); drawer bay under the board, slides out the -Y (rear) wall
on side rails - one motion, mitten-operable.

PCB (px,py) -> chassis (px-50, py-32.5).

Run:  python3 gen_chassis_stl.py
Out:  ./out/wapiti-base.{stl,obj}  ./out/wapiti-lid.{stl,obj}
      ./out/wapiti-tray.{stl,obj}
"""

import math
import os
import struct

# ---- parameters (mm) -------------------------------------------------------
WALL = 2.0
OUTER_W, OUTER_L, OUTER_H = 108.0, 74.0, 33.0
FLOOR_T = 2.0
BOARD_W, BOARD_L, BOARD_T = 100.0, 65.0, 1.6
BOSS_H = 17.5                       # board bottom z = 19.5
LID_T = 2.0
LID_Z0 = 28.0                       # lid plate 28..30, lens boss to 33
WALL_TOP = LID_Z0
SKIRT = 2.0

# drawer bay (under the board, slides out -Y)
BAY_X = 48.0                        # bay interior x -48..48
BAY_Z1 = 18.8                       # bay ceiling (pack top 17 + clearance)
RAIL_Z1 = 3.2                       # drawer rides on rails 2..3.2
GUIDE_Z0 = 12.0                     # upper guides keep the tray aligned
TRAY_X = 47.0                       # tray outer half-width
TRAY_Y0, TRAY_Y1 = -35.0, 19.5      # tray body span (mouth..rear wall)
BAY_END_Y = 21.25                   # bay rear wall outer face

# smart-pack insert (2S NMC, pack-ID + fuel gauge on the 5-pin connector)
PACK_X0, PACK_X1 = -35.0, 35.0
PACK_Y0, PACK_Y1 = -28.0, 12.0
PACK_Z0, PACK_Z1 = 5.0, 17.0

# paddle lever: full drawer width, 3 mm proud of the -Y face, grip groove
PADDLE_X = 47.0
PADDLE_Y0, PADDLE_Y1 = -40.0, -35.5
PADDLE_Z0, PADDLE_Z1 = 3.0, 18.5
GRV_Z0, GRV_Z1 = 8.5, 12.5          # grip groove (mitten pull)

# USB-C service port exits the +Y wall (nominal; align at layout)
USB_CX, USB_W, USB_H = -42.0, 7.5, 4.0
USB_Z0 = 21.0
# SW1 reset button through the lid: PCB (8,52) -> (-42, 19.5)
BTN_X, BTN_Y, BTN_R = -42.0, 19.5, 2.3
# Status LED light pipe: PCB (68,64) -> (18, 31.5)
LED_X, LED_Y, LED_R = 18.0, 31.5, 1.6
# Front-panel optics (all face +Z / the lid):
LENS_X, LENS_Y, LENS_R = -25.0, 17.5, 8.0        # IMX415 (25,50)
PIR_X, PIR_Y, PIR_R = 24.0, -26.5, 5.75          # AS312 (74,6)
SMA_X, SMA_Y, SMA_R = 46.0, -26.5, 3.5           # RJ2 (96,6)
LCD_WIN = (-34.0, -19.0, -14.0, -5.0)            # CU4 (26,20) active area
GNSS_WIN = (32.0, -29.0, 42.0, -20.0)            # ANT2 (88,8) RF membrane
RADAR_WIN = (28.0, -20.0, 48.0, -1.0)            # MU4 (88,22) 24 GHz window
IR_WIN_1 = (-4.0, -30.0, 17.0, -21.0)            # CD1 (60,7)
IR_WIN_2 = (-4.0, -19.0, 17.0, -10.0)            # CD2 (60,18)
# tree mount: strap slots through both side walls (webbing wraps the tree
# vertically) + a 1/4-20 tripod boss on the lid for bracket mounts
# (project-plan §5.3 "tree mount 1/4-20 + strap")
STRAP_W = 22.0                      # webbing slot width (y span)
STRAP_H = 3.5                       # webbing slot height (z span)
STRAP_Y0, STRAP_Y1 = -11.0, 11.0    # centered; clear of corner posts
STRAP_Z0 = 22.0                     # slot z span (upper wall, above the bay)
TRIPOD_X, TRIPOD_Y = -30.0, 27.0    # lid boss, clear of SW1 hole + lens port
TRIPOD_R_OUT, TRIPOD_R_IN = 6.5, 2.5  # 1/4-20 UNC minor dia ~5.35 -> pilot 5.0
TRIPOD_PILOT_R = 2.5
TRIPOD_H = 4.5                      # boss height above the lid
# mounting: PCB holes (4,4),(96,4),(4,61),(96,61) -> chassis
BOSSES = [(-46.0, -28.5), (46.0, -28.5), (-46.0, 28.5), (46.0, 28.5)]
BOSS_R, BOSS_DRILL_R = 2.8, 1.05
# lid screws: posts merge into the wall corners on purpose
POSTS = [(-49.5, -34.5), (49.5, -34.5), (-49.5, 34.5), (49.5, 34.5)]
POST_R, POST_DRILL_R = 3.0, 1.35
LID_POST_R = 2.4
GRID = 1.5

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)


# ---------------------------------------------------------------------------
# mesh kernel
# ---------------------------------------------------------------------------

def box_tris(x0, y0, z0, x1, y1, z1):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    tris = []
    for a, b, c, d in quads:
        tris.append((v[a], v[b], v[c]))
        tris.append((v[a], v[c], v[d]))
    return tris


def tube_tris(cx, cy, z0, z1, r_out, r_in, n=36):
    """Vertical tube: outer wall, inner wall, top annulus, bottom annulus."""
    tris = []
    for i in range(n):
        a0 = 2 * math.pi * i / n
        a1 = 2 * math.pi * (i + 1) / n
        c0, s0, c1, s1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
        o0 = (cx + r_out * c0, cy + r_out * s0)
        o1 = (cx + r_out * c1, cy + r_out * s1)
        i0 = (cx + r_in * c0, cy + r_in * s0)
        i1 = (cx + r_in * c1, cy + r_in * s1)
        A, B, C, D = (*o0, z0), (*o1, z0), (*o1, z1), (*o0, z1)
        tris += [(A, B, C), (A, C, D)]            # outer wall
        A, B, C, D = (*i0, z0), (*i1, z0), (*i1, z1), (*i0, z1)
        tris += [(A, C, B), (A, D, C)]            # inner wall (reversed)
        A, B, C, D = (*o0, z0), (*o1, z0), (*i1, z0), (*i0, z0)
        tris += [(A, C, B), (A, D, C)]            # bottom annulus
        A, B, C, D = (*o0, z1), (*o1, z1), (*i1, z1), (*i0, z1)
        tris += [(A, B, C), (A, C, D)]            # top annulus
    return tris


def merge(*parts):
    out = []
    for p in parts:
        out.extend(p)
    return out


def plate_grid_with_holes(x0, y0, x1, y1, z0, z1, holes):
    """Horizontal plate from GRID cells. holes: ('c',cx,cy,r) round or
    ('r',x0,y0,x1,y1) rectangular openings; a cell is skipped when its
    center falls inside a hole."""
    tris = []
    nx = max(1, int(round((x1 - x0) / GRID)))
    ny = max(1, int(round((y1 - y0) / GRID)))
    dx = (x1 - x0) / nx
    dy = (y1 - y0) / ny
    for i in range(nx):
        for j in range(ny):
            ax, ay = x0 + i * dx, y0 + j * dy
            bx, by = ax + dx, ay + dy
            mcx, mcy = (ax + bx) / 2, (ay + by) / 2
            skip = False
            for h in holes:
                if h[0] == 'c':
                    _, hx, hy, r = h
                    if (mcx - hx) ** 2 + (mcy - hy) ** 2 <= r * r:
                        skip = True
                        break
                else:  # rect
                    _, hx0, hy0, hx1, hy1 = h
                    if hx0 <= mcx <= hx1 and hy0 <= mcy <= hy1:
                        skip = True
                        break
            if not skip:
                tris += box_tris(ax, ay, z0, bx, by, z1)
    return tris


# ---------------------------------------------------------------------------
# base shell
# ---------------------------------------------------------------------------

def base_solid():
    s = []
    # floor
    s += box_tris(-OUTER_W / 2, -OUTER_L / 2, 0,
                  OUTER_W / 2, OUTER_L / 2, FLOOR_T)
    zt = WALL_TOP
    # +Y wall with USB-C cutout
    ux0, ux1 = USB_CX - USB_W / 2, USB_CX + USB_W / 2
    s += box_tris(-OUTER_W / 2, OUTER_L / 2 - WALL, FLOOR_T, ux0, OUTER_L / 2, zt)
    s += box_tris(ux0, OUTER_L / 2 - WALL, FLOOR_T, ux1, OUTER_L / 2, USB_Z0)
    s += box_tris(ux0, OUTER_L / 2 - WALL, USB_Z0 + USB_H, ux1, OUTER_L / 2, zt)
    s += box_tris(ux1, OUTER_L / 2 - WALL, FLOOR_T, OUTER_W / 2, OUTER_L / 2, zt)
    # -Y wall with drawer mouth (x -47..47, z 2..18.8)
    s += box_tris(-OUTER_W / 2, -OUTER_L / 2, 0, OUTER_W / 2, -OUTER_L / 2 + WALL, FLOOR_T)
    s += box_tris(-OUTER_W / 2, -OUTER_L / 2, BAY_Z1, OUTER_W / 2, -OUTER_L / 2 + WALL, zt)
    s += box_tris(-OUTER_W / 2, -OUTER_L / 2, FLOOR_T, -PADDLE_X, -OUTER_L / 2 + WALL, BAY_Z1)
    s += box_tris(PADDLE_X, -OUTER_L / 2, FLOOR_T, OUTER_W / 2, -OUTER_L / 2 + WALL, BAY_Z1)
    # ±X walls with strap slots (y -11..11, z 22..25.5): webbing wraps the
    # tree vertically through both slots; slot lips carry the load
    for sgn in (-1, 1):
        xw0 = OUTER_W / 2 - WALL if sgn > 0 else -OUTER_W / 2
        xw1 = OUTER_W / 2 if sgn > 0 else -OUTER_W / 2 + WALL
        s += box_tris(xw0, -OUTER_L / 2 + WALL, FLOOR_T, xw1, STRAP_Y0, zt)
        s += box_tris(xw0, STRAP_Y0, FLOOR_T, xw1, STRAP_Y1, STRAP_Z0)
        s += box_tris(xw0, STRAP_Y0, STRAP_Z0 + STRAP_H, xw1, STRAP_Y1, zt)
        s += box_tris(xw0, STRAP_Y1, FLOOR_T, xw1, OUTER_L / 2 - WALL, zt)
    # drawer bay: side walls + rear end wall (bay interior x -48..48, y ..21.25)
    bw = 1.75
    s += box_tris(-BAY_X - bw, -33.0, FLOOR_T, -BAY_X, BAY_END_Y, BAY_Z1)
    s += box_tris(BAY_X, -33.0, FLOOR_T, BAY_X + bw, BAY_END_Y, BAY_Z1)
    s += box_tris(-BAY_X, BAY_END_Y - bw, FLOOR_T, BAY_X + bw, BAY_END_Y, BAY_Z1)
    # drawer rails (bottom, tray rides on them) + lead-in steps at the mouth
    for sgn in (-1, 1):
        s += box_tris(sgn * 47.0, TRAY_Y0, FLOOR_T, sgn * 48.0, TRAY_Y1, RAIL_Z1)
        s += box_tris(sgn * 46.0, TRAY_Y0, FLOOR_T, sgn * 48.0, -31.0, RAIL_Z1)
        # upper guides (keep the drawer square through the stroke)
        s += box_tris(sgn * 47.0, TRAY_Y0, GUIDE_Z0, sgn * 48.0, TRAY_Y1, BAY_Z1)
    # PCB boss tubes (floor up to the board seating plane z=19.5)
    for bx, by in BOSSES:
        s += tube_tris(bx, by, FLOOR_T, FLOOR_T + BOSS_H, BOSS_R, BOSS_DRILL_R)
    # lid screw posts (merge into the wall corners)
    for px, py in POSTS:
        s += tube_tris(px, py, WALL_TOP - 4.0, WALL_TOP, POST_R, POST_DRILL_R)
    return merge(s)

# ---------------------------------------------------------------------------
# lid shell
# ---------------------------------------------------------------------------

def lid_solid():
    s = []
    z0, z1 = LID_Z0, LID_Z0 + LID_T
    # all through-features of the top plate
    holes = [('c', BTN_X, BTN_Y, BTN_R),
             ('c', LED_X, LED_Y, LED_R),
             ('c', PIR_X, PIR_Y, PIR_R),
             ('c', LENS_X, LENS_Y, LENS_R),
             ('c', SMA_X, SMA_Y, SMA_R),
             ('r',) + LCD_WIN, ('r',) + GNSS_WIN, ('r',) + RADAR_WIN,
             ('r',) + IR_WIN_1, ('r',) + IR_WIN_2]
    s += plate_grid_with_holes(-OUTER_W / 2, -OUTER_L / 2,
                               OUTER_W / 2, OUTER_L / 2, z0, z1, holes)
    # 0.8 mm membranes flush with the top: GNSS patch window + radar window
    # (plastic-only for RF; IP story matches the lens seat)
    s += box_tris(GNSS_WIN[0], GNSS_WIN[1], z1 - 0.8,
                  GNSS_WIN[2], GNSS_WIN[3], z1)
    s += box_tris(RADAR_WIN[0], RADAR_WIN[1], z1 - 0.8,
                  RADAR_WIN[2], RADAR_WIN[3], z1)
    # 1.0 mm viewing window over the 2in LCD status screen
    s += box_tris(LCD_WIN[0], LCD_WIN[1], z1 - 1.0,
                  LCD_WIN[2], LCD_WIN[3], z1)
    # lens seat boss: the IMX415 barrel seats 3 mm above the lid
    s += tube_tris(LENS_X, LENS_Y, z1, 33.0, 10.5, 8.2)
    # skirt: 4 walls hanging down outside, closing onto the base walls
    zs0, zs1 = z0 - SKIRT, z0
    s += box_tris(-OUTER_W / 2, OUTER_L / 2 - WALL, zs0, OUTER_W / 2, OUTER_L / 2, zs1)
    s += box_tris(-OUTER_W / 2, -OUTER_L / 2, zs0, OUTER_W / 2, -OUTER_L / 2 + WALL, zs1)
    s += box_tris(OUTER_W / 2 - WALL, -OUTER_L / 2 + WALL, zs0,
                  OUTER_W / 2, OUTER_L / 2 - WALL, zs1)
    s += box_tris(-OUTER_W / 2, -OUTER_L / 2 + WALL, zs0,
                  -OUTER_W / 2 + WALL, OUTER_L / 2 - WALL, zs1)
    # screw bosses in the lid corners (align with base posts)
    for px, py in POSTS:
        s += tube_tris(px, py, z0, z1, LID_POST_R, POST_DRILL_R)
    # 1/4-20 tree-mount boss: printed solid, drilled/tapped for a standard
    # 1/4-20 UNC tripod screw (project-plan §5.3)
    s += tube_tris(TRIPOD_X, TRIPOD_Y, z1, z1 + TRIPOD_H,
                   TRIPOD_R_OUT, TRIPOD_PILOT_R)
    return merge(s)


# ---------------------------------------------------------------------------
# battery drawer (hi-vis insert)
# ---------------------------------------------------------------------------

def tray_solid():
    s = []
    # floor rides on the rails (z 3.2..5)
    s += box_tris(-TRAY_X, TRAY_Y0, RAIL_Z1, TRAY_X, TRAY_Y1, 5.0)
    # side walls + rear wall
    for sgn in (-1, 1):
        s += box_tris(sgn * 45.5, TRAY_Y0, 5.0, sgn * TRAY_X, TRAY_Y1, BAY_Z1)
    s += box_tris(-TRAY_X, TRAY_Y1 - 1.5, 5.0, TRAY_X, TRAY_Y1, BAY_Z1)
    # smart-pack insert (2S NMC with pack-ID + BQ27441 on the 5-pin lead)
    s += box_tris(PACK_X0, PACK_Y0, PACK_Z0, PACK_X1, PACK_Y1, PACK_Z1)
    s += box_tris(-6.0, PACK_Y1, 6.0, 6.0, TRAY_Y1 - 1.5, 10.0)  # conn block
    # full-width paddle lever, 3 mm proud of the -Y face, grip groove mid-height
    s += box_tris(-PADDLE_X, PADDLE_Y0 + 2.5, PADDLE_Z0,
                  PADDLE_X, PADDLE_Y1, PADDLE_Z1)                 # back plate
    s += box_tris(-PADDLE_X, PADDLE_Y0, PADDLE_Z0,
                  PADDLE_X, PADDLE_Y0 + 3.0, GRV_Z0)              # front strip lo
    s += box_tris(-PADDLE_X, PADDLE_Y0, GRV_Z1,
                  PADDLE_X, PADDLE_Y0 + 3.0, PADDLE_Z1)           # front strip hi
    # paddle carry flange: hangs 12 mm below the lever, doubling as the strap
    # hook — webbing slides through the slot and takes the load off the lever
    s += box_tris(-PADDLE_X, PADDLE_Y0 - 0.5, 0.0,
                  PADDLE_X, PADDLE_Y1, STRAP_Z0 - 0.5)            # below slot
    return merge(s)


# ---------------------------------------------------------------------------
# exporters
# ---------------------------------------------------------------------------

def normal(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    l = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return (nx / l, ny / l, nz / l)


def write_stl(path, tris, name):
    with open(path, "wb") as f:
        header = name.encode()[:80].ljust(80, b" ")
        f.write(header)
        f.write(struct.pack("<I", len(tris)))
        for v1, v2, v3 in tris:
            n = normal(v1, v2, v3)
            for vec in (n, v1, v2, v3):
                f.write(struct.pack("<3f", *vec))
            f.write(struct.pack("<H", 0))  # attribute byte count


def write_obj(path, tris, name):
    with open(path, "w") as f:
        f.write("# %s (wapiti trailcam chassis)\n" % name)
        idx, verts, faces = {}, [], []
        for t in tris:
            face = []
            for v in t:
                if v not in idx:
                    idx[v] = len(verts) + 1
                    verts.append(v)
                face.append(idx[v])
            faces.append(face)
        for v in verts:
            f.write("v %.4f %.4f %.4f\n" % v)
        for fa in faces:
            f.write("f %d %d %d\n" % tuple(fa))


def main():
    parts = [("wapiti-base", base_solid()),
             ("wapiti-lid", lid_solid()),
             ("wapiti-tray", tray_solid())]
    for name, mesh in parts:
        write_stl(os.path.join(OUT, name + ".stl"), mesh, name)
        write_obj(os.path.join(OUT, name + ".obj"), mesh, name)
        print("%s: %d triangles -> out/%s.stl .obj" % (name, len(mesh), name))
    print("done.")


if __name__ == "__main__":
    main()

