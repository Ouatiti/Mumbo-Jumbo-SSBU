"""Retarget des animations Mumbo (Banjo-Tooie) sur le squelette Ness (step2.blend), export .nuanmb.
Usage : blender51 -b step2.blend --python retarget.py -- <outdir> [noms...]"""
import bpy, sys, os, math
import numpy as np
from mathutils import Matrix, Vector, Quaternion
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bt_pose as P
from bt_lib import bones_of, rd, parse_anim

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else os.path.join(HERE, 'anim_out')
ONLY = set(argv[1:])
os.makedirs(OUT, exist_ok=True)

MODEL = 0x854
bt_bones = bones_of(rd(MODEL))
bt_idx = {b[0]: i for i, b in enumerate(bt_bones)}
C = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)   # BT (x,y,z) -> Blender (x,-z,y)
SC = 4.369 / 103.5

# os Ness -> (os BT, joint début, joint fin pour la direction ou None)
MAP = {
    'Hip': (3, None), 'Waist': (1, None), 'Head': (18, None),
    'ShoulderL': (14, (14, 8)), 'ArmL': (8, (8, 16)), 'HandL': (16, (16, 71)),
    'ShoulderR': (28, (28, 22)), 'ArmR': (22, (22, 30)), 'HandR': (30, (30, 70)),
    'LegL': (10, (10, 12)), 'KneeL': (12, (12, 6)), 'FootL': (6, None),
    'LegR': (24, (24, 26)), 'KneeR': (26, (26, 20)), 'FootR': (20, None),
    'HaveR': (85, None),
}
NESS_DIR = {  # tête de l'os -> point cible côté Ness
    'ShoulderL': 'ArmL', 'ArmL': 'HandL', 'HandL': 'FingerL31',
    'ShoulderR': 'ArmR', 'ArmR': 'HandR', 'HandR': 'FingerR31',
    'LegL': 'KneeL', 'KneeL': 'FootL', 'FootL': 'ToeL',
    'LegR': 'KneeR', 'KneeR': 'FootR', 'FootR': 'ToeR',
}
STATIC_KEY = ['Trans', 'Rot', 'ClavicleL', 'ClavicleR', 'Bust', 'Neck', 'LegC', 'ClavicleC']

# nom Ness : (anim BT, mode, params)
#  'stretch' : toute la durée Ness couvre [a,b] (fraction de l'anim BT) -> boucles
#  'play'    : lecture à vitesse v depuis a (frames BT), bloquée en fin
#  'pose'    : pose fixe frame a
JOBS = {
    'a00wait1':      (0x3c3, 'stretch', (0.0, 1.0)),
    'a00wait2':      (0x0b5, 'stretch', (0.0, 1.0)),
    'a00wait3':      (0x0b7, 'play', (0, 0.6)),
    'a01walkslow':   (0x462, 'stretch', (0.0, 1.0)),
    'a01walkmiddle': (0x462, 'stretch', (0.0, 1.0)),
    'a01walkfast':   (0x462, 'stretch', (0.0, 1.0)),
    'a02run':        (0x09c, 'stretch', (0.0, 1.0)),
    'a02dash':       (0x09c, 'stretch', (0.0, 1.0)),
    'a03jumpf':      (0x377, 'play', (0, 0.25, 9)),
    'a03jumpb':      (0x377, 'play', (0, 0.25, 9)),
    'a03jumpaerialf': (0x377, 'play', (2, 0.3, 9)),
    'a03jumpaerialb': (0x377, 'play', (2, 0.3, 9)),
    'a04fall':       (0x377, 'pose', (9,)),
    'a04fallf':      (0x377, 'pose', (9,)),
    'a04fallb':      (0x377, 'pose', (9,)),
    'a04fallaerial': (0x377, 'pose', (9,)),
    'j01appealhir':  (0x0b6, 'stretch', (0.0, 0.6)),
    'j01appealsr':   (0x3c5, 'stretch', (0.0, 1.0)),
    'j01appeallwr':  (0x09d, 'stretch', (0.0, 1.0)),
}
LEVITATE = {'j01appeallwr'}
NESS_LEN = {'a00wait1': 180, 'a00wait2': 119, 'a00wait3': 99, 'a01walkslow': 40, 'a01walkmiddle': 36,
            'a01walkfast': 28, 'a02dash': 25, 'a02run': 48, 'a03jumpf': 59, 'a03jumpb': 59,
            'a03jumpaerialf': 57, 'a03jumpaerialb': 57, 'a04fall': 8, 'a04fallf': 8, 'a04fallb': 8,
            'a04fallaerial': 8, 'j01appealhir': 59, 'j01appealsr': 69, 'j01appeallwr': 64}

arm = bpy.data.objects['smush_blender_import']
bones = arm.data.bones
REST = {b.name: b.matrix_local.copy() for b in bones}
def m3(a): return Matrix([list(r) for r in a])
def np3(m): return np.array([list(r) for r in m.to_3x3()])

def minrot(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b)
    v = np.cross(a, b); c = float(np.dot(a, b))
    if np.linalg.norm(v) < 1e-8: return np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * (1 / (1 + c))

bt_rest = {b[0]: np.array(b[2], float) for b in bt_bones}
CAL = {}
for nb, (bid, d) in MAP.items():
    if d:
        nd = np.array(REST[NESS_DIR[nb]].translation - REST[nb].translation)
        bd = C @ (bt_rest[d[1]] - bt_rest[d[0]])
        CAL[nb] = minrot(nd, bd)
    else:
        CAL[nb] = np.eye(3)
# le bâton suit l'étalonnage de la main
#  maillage : bâton vers -Y (tête de mort au bout) ; BT : 89 -> 85 = vers le haut
CAL['HaveR'] = minrot(np.array([0.0, -1.0, 0.0]), C @ (bt_rest[85] - bt_rest[89]))
for k in ('ArmL', 'ArmR', 'KneeL', 'HaveR'):
    print('CAL', k, np.round(np.degrees(np.arccos(np.clip((np.trace(CAL[k]) - 1) / 2, -1, 1))), 1))

def bt_world(ch, f):
    W = P.pose(bt_bones, ch, f)
    out = {}
    for i, (bid, par, p) in enumerate(bt_bones):
        R = W[i][:3, :3].copy()
        u, s, vt = np.linalg.svd(R); R = u @ vt   # retire l'échelle
        out[bid] = (R, W[i] @ np.array([*p, 1.0]))
    return out

order = []  # ordre hiérarchique
def walk(b):
    order.append(b)
    for c in b.children: walk(c)
for b in bones:
    if b.parent is None: walk(b)

# Redressement du corps entier (fraction de l'inclinaison BT conservée) : la course BT
# couche Mumbo quasi à l'horizontale, illisible en jeu.
DEBUG_TILT = os.environ.get('DEBUG_TILT') == '1'
TAME = {'a02run': 0.35, 'a02dash': 0.35, 'a01walkfast': 0.5, 'j01appeallwr': 0.15}

# ───── Couches procédurales (spec emotes) ─────
UP = np.array([0.0, 0.0, 1.0])
_f = np.array(REST['ToeL'].translation - REST['FootL'].translation); _f[2] = 0
FWD = _f / np.linalg.norm(_f)
def _n(v): v = np.array(v, float); return v / np.linalg.norm(v)
def _rest_dir(n): return np.array(REST[NESS_DIR[n]].translation - REST[n].translation)

# Emote haut : danse en tournant autour du bâton planté (pivot = main du bâton, 2 tours).
SPIN = {'j01appealhir': (10, 48, 2.0)}   # frame début, fin, nombre de tours
# Emote bas : jambes en tailleur (directions monde visées par os).
def _cross():
    out = {}
    for side, other_shin in (('L', 0.15), ('R', -0.05)):
        o = np.array([np.sign(REST['Leg' + side].translation.x), 0.0, 0.0])
        want = {
            'Leg' + side:  _n(FWD * 0.75 + o * 0.55 - UP * 0.05),
            'Knee' + side: _n(-o * 0.9 + FWD * (0.25 if side == 'L' else 0.1) - UP * (0.15 if side == 'L' else 0.3)),
            'Foot' + side: _n(FWD * 0.4 - o * 0.4 - UP * 0.8),
        }
        for n, d in want.items():
            out[n] = minrot(_rest_dir(n), d) @ np3(REST[n])
    return out
CROSS = {'j01appeallwr': _cross()}
# Emote bas : bâton qui flotte à l'horizontale au-dessus de la tête.
FLOAT_STAFF = {'j01appeallwr'}
STAFF_Q = minrot(np.array([0.0, -1.0, 0.0]), FWD) @ np3(REST['HaveR'])

def solve(ch, f, hip0, extra_z=0.0, tame=1.0, override=None):
    bw = bt_world(ch, f)
    Wrot = {}; basis = {}; hip_loc = None
    G = np.eye(3)
    if tame < 1.0:
        up = np.array([0.0, 0.0, 1.0])
        u = (C @ bw[3][0] @ C.T) @ up
        v = (1 - tame) * up + tame * u
        G = minrot(u, v)
        if DEBUG_TILT: print('TILT', round(f, 1), round(math.degrees(math.acos(max(-1, min(1, u[2])))), 1))
    for b in order:
        n = b.name
        Rr = np3(REST[n])
        if b.parent:
            Rp = np3(REST[b.parent.name]); L = Rp.T @ Rr; Wp = Wrot[b.parent.name]
        else:
            L = Rr; Wp = np.eye(3)
        if override and n in override:
            Q = override[n]
            B = L.T @ Wp.T @ Q
            Wrot[n] = Q; basis[n] = B
        elif n in MAP:
            bid = MAP[n][0]
            Rd = C @ bw[bid][0] @ C.T
            Q = G @ Rd @ CAL[n] @ Rr
            B = L.T @ Wp.T @ Q
            Wrot[n] = Q; basis[n] = B
        else:
            Wrot[n] = Wp @ L
    # translation de la hanche
    pos = bw[3][1][:3]
    d = C @ (pos - hip0) * SC
    d[2] += extra_z
    hip_loc = np3(REST['Hip']).T @ d
    return basis, hip_loc

def bt_frame_for(job, i, N, s, e):
    aid, mode, prm = job
    if mode == 'stretch':
        a, b = prm; return s + (e - s) * (a + (b - a) * i / N)
    if mode == 'play':
        a, v = prm[:2]; stop = prm[2] if len(prm) > 2 else e - s
        return min(s + a + i * v, s + stop, e)
    return e if prm[0] < 0 else s + prm[0]

for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'
bpy.context.view_layer.objects.active = arm
arm.select_set(True)

for name, job in JOBS.items():
    if ONLY and name not in ONLY: continue
    an = parse_anim(rd(job[0])); ch = P.channels(an); s, e = an[0], an[1]
    N = NESS_LEN[name]
    # dérive horizontale de la racine : on la retire (garde le balancement)
    hp = lambda f: bt_world(ch, f)[3][1][:3]
    f0 = bt_frame_for(job, 0, N, s, e); f1 = bt_frame_for(job, N, N, s, e)
    p0, p1 = hp(f0), hp(f1)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    arm.animation_data_create(); arm.animation_data.action = act
    for i in range(N + 1):
        f = bt_frame_for(job, i, N, s, e)
        t = (f - f0) / (f1 - f0) if f1 != f0 else 0
        hip0 = bt_rest[3].copy()
        drift = p0 + (p1 - p0) * t
        hip0[0] = drift[0]; hip0[2] = drift[2]
        ez = (1.2 + 0.25 * math.sin(2 * math.pi * i / N)) * min(1, i / 8, (N - i) / 8) if name in LEVITATE else 0.0
        ov = dict(CROSS.get(name, {}))
        if name in FLOAT_STAFF: ov['HaveR'] = STAFF_Q
        basis, hl = solve(ch, f, hip0, ez, TAME.get(name, 1.0), ov)
        for n, B in basis.items():
            pb = arm.pose.bones[n]
            pb.rotation_quaternion = m3(B).to_quaternion()
            pb.keyframe_insert('rotation_quaternion', frame=i)
        pb = arm.pose.bones['Hip']
        pb.location = Vector(hl.tolist()); pb.keyframe_insert('location', frame=i)
        for n in STATIC_KEY:
            if n in arm.pose.bones:
                q = arm.pose.bones[n]; q.rotation_quaternion = Quaternion(); q.location = Vector()
                q.keyframe_insert('rotation_quaternion', frame=i); q.keyframe_insert('location', frame=i)
        if name in FLOAT_STAFF:
            # place la poignée du bâton au-dessus de la tête (FK évaluée par Blender)
            hv = arm.pose.bones['HaveR']; hv.location = Vector(); hv.keyframe_insert('location', frame=i)
            bpy.context.scene.frame_set(i)
            pbn = arm.pose.bones
            hh = np.array(pbn['Head'].head); hip = np.array(pbn['Hip'].head)
            h = max(0.5, hh[2] - hip[2])
            bob = 0.08 * h * math.sin(2 * math.pi * 2 * i / N)
            target = hh + UP * (0.9 * h + bob) - FWD * 0.6 * h
            P0 = np.array(hv.head)
            par = hv.parent
            Wp = np3(par.matrix); L = np3(REST[par.name]).T @ np3(REST['HaveR'])
            loc = (Wp @ L).T @ (target - P0)
            hv.location = Vector(loc.tolist()); hv.keyframe_insert('location', frame=i)
        if name in SPIN:
            a0, a1, turns = SPIN[name]
            if i == a0 or (i == 0 and a0 <= 0):
                bpy.context.scene.frame_set(i)
                PIV = np.array(arm.pose.bones['HaveR'].head)
            u = min(1.0, max(0.0, (i - a0) / (a1 - a0)))
            th = 2 * math.pi * turns * (u * u * (3 - 2 * u))
            if th != 0.0:
                Rr = np3(REST['Rot']); hd = np.array(REST['Rot'].translation)
                c, s_ = math.cos(th), math.sin(th)
                Rz = np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1.0]])
                p = PIV.copy(); p[2] = hd[2]
                q = arm.pose.bones['Rot']
                q.rotation_quaternion = m3(Rr.T @ Rz @ Rr).to_quaternion()
                q.location = Vector((Rr.T @ ((np.eye(3) - Rz) @ (p - hd))).tolist())
                q.keyframe_insert('rotation_quaternion', frame=i); q.keyframe_insert('location', frame=i)
    # continuité des quaternions
    out = os.path.join(OUT, name + '.nuanmb')
    bpy.context.scene.frame_start = 0; bpy.context.scene.frame_end = N
    r = bpy.ops.sub.anim_export(filepath=out, include_transform_track=True, include_material_track=False,
                                include_visibility_track=False, first_blender_frame=0, last_blender_frame=N)
    print('EXPORT', name, hex(job[0]), N, r, os.path.exists(out))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'retarget.blend'))
