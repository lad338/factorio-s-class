import bpy, sys, math, os, mathutils

argv = sys.argv[sys.argv.index("--") + 1:]
MODEL_PATH = argv[0]
OUT_DIR = argv[1]
VARIANT = argv[2]

FRAME_SIZE = 512
ORTHO_SCALE = 7
MODEL_YAW_OFFSET = 90

# Reusable lighting/material comparison tool -- add a variant here, run
# it, compare against others. Each variant: (world_color, world_strength,
# key_energy, fill_energy, fill_angle_z_deg, rim_energy_or_None,
# rim_angle_z_deg, light_angular_size_deg, body_roughness_or_None).
#
# light_angular_size_deg: Blender sun lamps default to a tiny pinpoint
# angular size -- on glossy/low-roughness surfaces that produces a sharp
# "glint" per light; a larger angular size spreads it into a broader,
# softer highlight without reducing overall brightness.
#
# body_roughness: overrides the body paint materials' Roughness input
# directly (source value is 0, a perfect mirror) -- the other lever for
# the same glint problem, attacking the surface instead of the light.
#
# "baseline" and "soft-light" are kept for regression comparison; "final"
# matches what render-sprites.py actually ships.
VARIANTS = {
    "baseline":  ((0.5, 0.5, 0.5), 0.08, 3.5, 1.8, -45, None, 0,   0, None),
    "soft-light": ((0.5, 0.5, 0.5), 0.05, 3.5, 1.2, -45, 2.0, 200, 30, None),
    "final":     ((0.5, 0.5, 0.5), 0.05, 3.5, 1.2, -45, 2.0, 200, 0, 0.32),
}
world_color, world_strength, key_e, fill_e, fill_z, rim_e, rim_z, soft_deg, body_rough = VARIANTS[VARIANT]

BODY_PAINT_MATERIALS = ["TwiXeR_W223", "TwiXeR_W223.001", "TwiXeR_W223_brabus_black"]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=MODEL_PATH)

if body_rough is not None:
    for name in BODY_PAINT_MATERIALS:
        mat = bpy.data.materials.get(name)
        if not mat:
            continue
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Roughness"].default_value = body_rough

for o in list(bpy.context.scene.objects):
    if o.type in ('LIGHT', 'CAMERA'):
        bpy.data.objects.remove(o, do_unlink=True)

imported = [o for o in bpy.context.scene.objects if o.type == 'MESH']
roots = [o for o in bpy.context.scene.objects if o.parent is None and o.type != 'MESH'] or \
        [o for o in imported if o.parent is None]

min_co = mathutils.Vector((1e9, 1e9, 1e9))
max_co = mathutils.Vector((-1e9, -1e9, -1e9))
for o in imported:
    for v in o.bound_box:
        world = o.matrix_world @ mathutils.Vector(v)
        min_co.x = min(min_co.x, world.x)
        min_co.y = min(min_co.y, world.y)
        min_co.z = min(min_co.z, world.z)
        max_co.x = max(max_co.x, world.x)
        max_co.y = max(max_co.y, world.y)
        max_co.z = max(max_co.z, world.z)
offset = mathutils.Vector(((min_co.x + max_co.x) / 2, (min_co.y + max_co.y) / 2, min_co.z))
yaw = mathutils.Matrix.Rotation(math.radians(MODEL_YAW_OFFSET), 4, 'Z')
for o in roots:
    centered = o.matrix_world.copy()
    centered.translation -= offset
    o.matrix_world = yaw @ centered

bpy.ops.object.empty_add(location=(0, 0, 0))
rig = bpy.context.object
rig.name = "RotationRig"

bpy.ops.object.camera_add()
cam = bpy.context.object
cam.data.type = 'ORTHO'
cam.data.ortho_scale = ORTHO_SCALE
cam.location = (0, -500, 500)
cam.rotation_euler = (math.radians(45), 0, 0)
cam.parent = rig
bpy.context.scene.camera = cam

world = bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (*world_color, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = world_strength

angle_rad = math.radians(soft_deg) if soft_deg else None

bpy.ops.object.light_add(type='SUN')
sun = bpy.context.object
sun.data.energy = key_e
sun.data.use_shadow = False
sun.rotation_euler = (math.radians(45), 0, math.radians(135))
sun.parent = rig
if angle_rad:
    sun.data.angle = angle_rad

if fill_e is not None:
    bpy.ops.object.light_add(type='SUN')
    fill = bpy.context.object
    fill.data.energy = fill_e
    fill.data.use_shadow = False
    fill.rotation_euler = (math.radians(60), 0, math.radians(fill_z))
    fill.parent = rig
    if angle_rad:
        fill.data.angle = angle_rad

if rim_e is not None:
    bpy.ops.object.light_add(type='SUN')
    rim = bpy.context.object
    rim.data.energy = rim_e
    rim.data.use_shadow = False
    rim.rotation_euler = (math.radians(70), 0, math.radians(rim_z))
    rim.parent = rig
    if angle_rad:
        rim.data.angle = angle_rad

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = FRAME_SIZE
scene.render.resolution_y = FRAME_SIZE
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'

os.makedirs(OUT_DIR, exist_ok=True)

def rig_angle(i):
    return (2 * math.pi * i / 36) - (math.pi / 2)

# Just two representative frames per variant: front-ish (0) and a side
# profile (9) where the wheel detail -- the actual thing being judged --
# is clearly visible.
for i in (0, 9):
    rig.rotation_euler = (0, 0, rig_angle(i))
    scene.render.filepath = os.path.join(OUT_DIR, f"{VARIANT}_frame_{i:02d}.png")
    bpy.ops.render.render(write_still=True)

rig.rotation_euler = (0, 0, math.radians(135) - math.radians(90))
scene.render.filepath = os.path.join(OUT_DIR, f"{VARIANT}_icon.png")
bpy.ops.render.render(write_still=True)

print(f"PREVIEW_DONE variant={VARIANT}")
