"""blender51 -b retarget.blend --python preview.py -- <out.png> <action> [n]"""
import bpy, sys, os, math
import numpy as np
argv = sys.argv[sys.argv.index('--') + 1:]
out, actname = argv[0], argv[1]; n = int(argv[2]) if len(argv) > 2 else 6
sc = bpy.context.scene
arm = bpy.data.objects['smush_blender_import']
if actname == 'REST':
    if arm.animation_data: arm.animation_data.action = None
    for pb in arm.pose.bones: pb.matrix_basis.identity()
    fr = (0, 0)
else:
    act = bpy.data.actions[actname]
    arm.animation_data.action = act
    if hasattr(arm.animation_data, 'action_slot') and act.slots:
        arm.animation_data.action_slot = act.slots[0]
    fr = act.frame_range
sc.render.engine = 'BLENDER_WORKBENCH'
RX, RY = (int(x) for x in os.environ.get('PV_RES', '240x300').split('x'))
sc.render.resolution_x = RX; sc.render.resolution_y = RY
sc.render.film_transparent = False
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'MATERIAL'
for o in list(bpy.data.objects):
    if o.type in ('CAMERA', 'LIGHT'): bpy.data.objects.remove(o)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 18
views = {'front': ((0, -30, 7.5), (math.radians(90), 0, 0)), 'side': ((30, 0, 7.5), (math.radians(90), 0, math.radians(90)))}
tiles = []
tmp = os.path.join(os.path.dirname(out), '_t.png')
for v, (loc, rot) in views.items():
    row = []
    cam.location = loc; cam.rotation_euler = rot
    for k in range(n):
        f = int(fr[0] + (fr[1] - fr[0]) * k / max(1, n - 1))
        sc.frame_set(f)
        sc.render.filepath = tmp; bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(tmp); px = np.array(img.pixels[:]).reshape(RY, RX, 4)[::-1, :, :3]
        bpy.data.images.remove(img); row.append(px)
    tiles.append(np.concatenate(row, 1))
full = (np.concatenate(tiles, 0) * 255).clip(0, 255).astype(np.uint8)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bt_pose
bt_pose.png(out, full)
print('PREVIEW', out, fr[:])
