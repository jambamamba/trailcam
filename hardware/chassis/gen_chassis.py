# gen_chassis.py - Blender batch renderer for the wapiti chassis previews
#
# Run headless (Blender >= 4.x):
#   ~/Downloads/blender-5.2.0-linux-x64/blender -b -P gen_chassis.py
#
# Imports the verified constructive meshes from gen_chassis_stl.py
# (out/wapiti-base.stl + out/wapiti-lid.stl + out/wapiti-tray.stl,
# 1 unit = 1 mm) and renders three Cycles (CPU) images to out/:
#   preview.png            - exploded 3/4 view (lid +45 z, drawer pulled -Y)
#   preview-assembled.png  - assembled 3/4 view
#   preview-top.png        - assembled top-down (plan) view, USB wall +Y up
#
# Geometry source of truth is gen_chassis_stl.py; this script only renders.

import math
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
BASE_STL = os.path.join(OUT, "wapiti-base.stl")
LID_STL = os.path.join(OUT, "wapiti-lid.stl")
TRAY_STL = os.path.join(OUT, "wapiti-tray.stl")

SCALE = 0.001          # STL mm -> Blender meters
LID_EXPLODE = 0.045    # lid lift for the exploded view (m)
TRAY_PULL = 0.028      # drawer pull-out for the exploded view (m, -Y)
RES_X, RES_Y = 1000, 700
SAMPLES = 64

# render views: (name, explode?, target, ortho scale, azimuth, elevation)
VIEWS = [
    ("preview",           True,  (0.0, -0.005, 0.030), 0.19, 30.0, 25.0),
    ("preview-assembled", False, (0.0,  0.000, 0.014), 0.16, 30.0, 25.0),
    ("preview-top",       False, (0.0,  0.000, 0.000), 0.14,  0.0, 90.0),
]


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_stl(path, name):
    before = set(bpy.data.objects)
    try:
        bpy.ops.wm.stl_import(filepath=path)
    except AttributeError:                       # Blender < 4.0
        bpy.ops.import_mesh.stl(filepath=path)
    obj = [o for o in bpy.data.objects if o not in before][0]
    obj.name = name
    obj.scale = (SCALE, SCALE, SCALE)
    # flat shading: crisp CAD look (STL carries no normals worth smoothing)
    for p in obj.data.polygons:
        p.use_smooth = False
    return obj


def make_material(name, rgb, rough=0.55):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    return m


def add_camera(name, target, ortho_scale, az_deg, el_deg, r=2.0):
    cd = bpy.data.cameras.new(name)
    cd.type = "ORTHO"
    cd.ortho_scale = ortho_scale
    cd.clip_start = 0.01
    cd.clip_end = 100.0
    cam = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(cam)
    az, el = math.radians(az_deg), math.radians(el_deg)
    loc = (target[0] + r * math.cos(el) * math.cos(az),
           target[1] + r * math.cos(el) * math.sin(az),
           target[2] + r * math.sin(el))
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return cam


def setup_scene():
    scene = bpy.context.scene
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.07, 0.07, 0.08, 1.0)
    bg.inputs[1].default_value = 1.0
    scene.world = world

    sun_data = bpy.data.lights.new("sun", "SUN")
    sun_data.energy = 3.0
    sun = bpy.data.objects.new("sun", sun_data)
    bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(55), 0.0, math.radians(20))

    fill_data = bpy.data.lights.new("fill", "SUN")
    fill_data.energy = 1.0
    fill = bpy.data.objects.new("fill", fill_data)
    bpy.context.scene.collection.objects.link(fill)
    fill.rotation_euler = (math.radians(35), 0.0, math.radians(200))

    scene.render.engine = "CYCLES"
    # Do NOT touch cycles preferences / get_devices() here: enumerating GPU
    # devices segfaults inside libsycl on some headless machines. Setting
    # device = "CPU" is enough for a deterministic headless render.
    scene.cycles.device = "CPU"
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    return scene


def main():
    reset_scene()
    scene = setup_scene()

    base = import_stl(BASE_STL, "wapiti-base")
    lid = import_stl(LID_STL, "wapiti-lid")
    tray = import_stl(TRAY_STL, "wapiti-tray")
    base.data.materials.append(make_material("base_mat", (0.35, 0.38, 0.45)))
    lid.data.materials.append(make_material("lid_mat", (0.30, 0.33, 0.38)))
    # hi-vis drawer interior (4.13: visible through the mouth with mittens on)
    tray.data.materials.append(make_material("tray_mat", (0.95, 0.45, 0.15)))

    for name, explode, target, ortho, az, el in VIEWS:
        lid.location.z = LID_EXPLODE if explode else 0.0
        tray.location.y = -TRAY_PULL if explode else 0.0
        cam = add_camera("cam-" + name, target, ortho, az, el)
        scene.camera = cam
        scene.render.filepath = os.path.join(OUT, name + ".png")
        bpy.ops.render.render(write_still=True)
        print("wrote %s" % scene.render.filepath)


if __name__ == "__main__":
    main()
