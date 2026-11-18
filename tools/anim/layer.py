"""Animations Mumbo = animations d'origine de Ness (fluides, timing calé sur le gameplay)
+ couches de style Mumbo (posture voûtée, bâton tenu, rebond) appliquées par-dessus.
Usage : blender51 -b step2.blend --python layer.py -- <outdir> [noms...]
"""
import bpy, sys, os, math
from mathutils import Quaternion, Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0]
ONLY = set(argv[1:])
os.makedirs(OUT, exist_ok=True)
NESS = r"E:\Emulateurs\ness_model\fighter\ness\motion\body\c00"
STYLE = os.environ.get('MUMBO_STYLE', '1') == '1'

arm = bpy.data.objects['smush_blender_import']
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'

NAMES = ['a00wait1', 'a00wait2', 'a00wait3', 'a01walkslow', 'a01walkmiddle', 'a01walkfast',
         'a02run', 'a02dash', 'a03jumpf', 'a03jumpb', 'a03jumpaerialf', 'a03jumpaerialb',
         'a04fall', 'a04fallf', 'a04fallb', 'a04fallaerial']

# Emotes : nos retargets Banjo-Tooie (déjà exportés), simplement lissés dans le temps.
APPEALS = ['j01appealhir', 'j01appealsr', 'j01appeallwr']
MINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')

# ───── couches de style Mumbo ─────
UP = Vector((0, 0, 1))
REST_HAVE = arm.data.bones['HaveR'].matrix_local.to_3x3()
STAFF_AXIS = Vector((0, -1, 0))  # direction du bâton (vers la tête de mort) dans le repère repos monde
# amortissement du balancier du bras qui tient le bâton (0 = figé sur la moyenne, 1 = Ness d'origine)
ARM_DAMP = {'ShoulderR': 0.55, 'ArmR': 0.45, 'HandR': 0.5}
# part de l'orientation « bâton droit » (le reste suit la main de Ness : garde de la vie)
STAFF_UPRIGHT = 0.8
HUNCH_DEG = 7.0     # dos légèrement voûté

def keyframes(act, path_prefix):
    fr = set()
    for fc in act_fcurves(act):
        if fc.data_path.startswith(path_prefix):
            fr.update(int(round(k.co[0])) for k in fc.keyframe_points)
    return sorted(fr)

def act_fcurves(act):
    if hasattr(act, 'fcurves'):
        return list(act.fcurves)
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                out.extend(bag.fcurves)
    return out

def qavg(qs):
    q0 = qs[0]; acc = Vector((0, 0, 0, 0))
    for q in qs:
        v = Vector(q) if q.dot(q0) >= 0 else -Vector(q)
        acc += v
    return Quaternion(acc).normalized()  # (Vector 4D .normalized() de Blender 5.1 ignore w)

def damp_arm(frames):
    for n, k in ARM_DAMP.items():
        pb = arm.pose.bones.get(n)
        if pb is None: continue
        qs = []
        for f in frames:
            bpy.context.scene.frame_set(f); qs.append(pb.rotation_quaternion.copy())
        m = qavg(qs)
        for f, q in zip(frames, qs):
            pb.rotation_quaternion = m.slerp(q if q.dot(m) >= 0 else -q, k).normalized()
            pb.keyframe_insert('rotation_quaternion', frame=f)

def hunch(frames):
    pb = arm.pose.bones.get('Bust')
    if pb is None: return
    for f in frames:
        bpy.context.scene.frame_set(f)
        M = pb.matrix.copy()
        fwd = Vector((0, -1, 0))
        axis = fwd.cross(UP).normalized()          # pencher vers l'avant
        R = Quaternion(axis, math.radians(HUNCH_DEG)).to_matrix().to_4x4()
        T = Matrix.Translation(M.translation)
        pb.matrix = T @ R @ Matrix.Translation(-M.translation) @ M
        pb.keyframe_insert('rotation_quaternion', frame=f)

def staff_upright(frames, loop):
    pb = arm.pose.bones['HaveR']
    # direction cible lissée (léger retard = inertie du bâton)
    dirs = []
    for f in frames:
        bpy.context.scene.frame_set(f)
        cur = (pb.matrix.to_3x3() @ REST_HAVE.inverted() @ STAFF_AXIS).normalized()
        tgt = (UP * 1.0 + Vector((0, -0.18, 0))).normalized()
        dirs.append((tgt * STAFF_UPRIGHT + cur * (1 - STAFF_UPRIGHT)).normalized())
    sm = smooth_vecs(dirs, 2, loop)
    for f, d in zip(frames, sm):
        bpy.context.scene.frame_set(f)
        M = pb.matrix.copy()
        cur = (M.to_3x3() @ REST_HAVE.inverted() @ STAFF_AXIS).normalized()
        R = cur.rotation_difference(d).to_matrix().to_4x4()
        T = Matrix.Translation(M.translation)
        pb.matrix = T @ R @ Matrix.Translation(-M.translation) @ M
        pb.keyframe_insert('rotation_quaternion', frame=f)
        pb.keyframe_insert('location', frame=f)

def smooth_vecs(vs, r, loop):
    n = len(vs); out = []
    for i in range(n):
        acc = Vector((0, 0, 0)); w = 0
        for d in range(-r, r + 1):
            j = i + d
            if loop: j %= n
            elif j < 0 or j >= n: continue
            ww = 1.0 / (1 + abs(d)); acc += vs[j] * ww; w += ww
        out.append((acc / w).normalized())
    return out

def smooth_all(frames, r, loop):
    """Lissage temporel de toutes les rotations (emotes retargetées : coupe les à-coups)."""
    n = len(frames)
    data = {}
    for f in frames:
        bpy.context.scene.frame_set(f)
        for pb in arm.pose.bones:
            data.setdefault(pb.name, []).append((pb.rotation_quaternion.copy(), pb.location.copy()))
    for name, seq in data.items():
        pb = arm.pose.bones[name]
        if all(q.rotation_difference(seq[0][0]).angle < 1e-4 and (l - seq[0][1]).length < 1e-5 for q, l in seq):
            continue
        for i, f in enumerate(frames):
            qs = []; ls = Vector((0, 0, 0)); w = 0
            for d in range(-r, r + 1):
                j = i + d
                if loop: j %= n
                else: j = min(max(j, 0), n - 1)
                ww = math.exp(-(d * d) / (0.5 * r * r + 1e-6))
                qs.append((seq[j][0], ww)); ls += seq[j][1] * ww; w += ww
            q0 = qs[r][0]; acc = Vector((0, 0, 0, 0))
            for q, ww in qs:
                acc += (Vector(q) if q.dot(q0) >= 0 else -Vector(q)) * ww
            pb.rotation_quaternion = Quaternion(acc).normalized(); pb.location = ls / w
            pb.keyframe_insert('rotation_quaternion', frame=f); pb.keyframe_insert('location', frame=f)

LOOPS = {'a00wait1', 'a00wait2', 'a01walkslow', 'a01walkmiddle', 'a01walkfast', 'a02run', 'a04fall',
         'a04fallf', 'a04fallb', 'a04fallaerial', 'j01appeallwr'}

def process(name):
    path = os.path.join(MINE if name in APPEALS else NESS, name + '.nuanmb')
    arm.animation_data_create(); arm.animation_data.action = None
    bpy.ops.sub.import_anim(filepath=path, include_transform_track=True, include_material_track=False,
                            include_visibility_track=False, first_blender_frame=0)
    act = arm.animation_data.action
    act.name = name; act.use_fake_user = True
    f0, f1 = (int(x) for x in act.frame_range)
    print('IMPORT', name, f0, f1, len(act_fcurves(act)))
    frames = list(range(f0, f1 + 1))
    if STYLE:
        loop = name in LOOPS
        if name in APPEALS:
            smooth_all(frames, 3, loop)
        else:
            damp_arm(frames)
            hunch(frames)
            staff_upright(frames, loop)
    out = os.path.join(OUT, name + '.nuanmb')
    bpy.context.scene.frame_start = f0; bpy.context.scene.frame_end = f1
    r = bpy.ops.sub.anim_export(filepath=out, include_transform_track=True, include_material_track=False,
                                include_visibility_track=False, first_blender_frame=f0, last_blender_frame=f1)
    print('EXPORT', name, r, os.path.exists(out))

for n in NAMES + APPEALS:
    if ONLY and n not in ONLY: continue
    process(n)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'layer.blend'))
