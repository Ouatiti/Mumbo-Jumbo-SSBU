"""Chorégraphie des mouvements de Mumbo (voir poses.py).

blender -b --factory-startup --python tools/anim/moves.py -- [dossier_sortie] [filtre...]
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from poses import pose, mix, smooth01, Keys, write, length

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
ONLY = argv[1:]
TAU = 2 * math.pi


def add(t, d):
    return tuple(a + b for a, b in zip(t, d))


def emit(name, N, fn, **kw):
    if ONLY and not any(o in name for o in ONLY):
        return
    write(OUT, name, N, fn, **kw)


# ═════════════ Attente : chamane voûté, bâton en main droite ═════════════
BASE = pose(
    yaw=-30.0, hip=(0.0, -0.55, -0.15), hrot=(5, 0, 0), waist=(9, 0, 0), bust=(7, 4, 0), head=(-15, 16, 0),
    footL=(0.45, 0.0, 0.55), footR=(-0.45, 0.0, -0.5), footLrot=(0, 14, 0), footRrot=(0, -16, 0),
    kneeL=(0.35, 0.0, 1.0), kneeR=(-0.4, 0.0, 1.0),
    gripR=(-3.7, -1.7, 1.1), elbowR=(-0.45, -0.1, -0.9), staff=(-0.24, 0.95, 0.20), slide=2.2,
    gripL=(2.7, -2.7, 1.5), elbowL=(0.45, -0.1, -0.9), fist=0.45,
)


def idle(f):
    """boucle de 180 frames : 4 rebonds sur les genoux, 2 agitations du bâton, 2 respirations."""
    b = 0.5 - 0.5 * math.cos(TAU * f / 45)               # 0 debout → 1 fléchi
    bl = 0.5 - 0.5 * math.cos(TAU * (f - 4) / 45)        # retard (tête, bras)
    w = math.sin(TAU * f / 90)
    wl = math.sin(TAU * (f - 6) / 90)
    br = math.sin(TAU * (f - 8) / 90)
    p = dict(BASE)
    p['hip'] = (0.12 * math.sin(TAU * f / 180), -0.40 - 0.34 * b, -0.15)
    p['hrot'] = (5 + 1.5 * b, 0, 1.2 * math.sin(TAU * f / 180))
    p['waist'] = (9 + 1.5 * bl, 0, 0)
    p['bust'] = (7 + 1.8 * br, 4 + 2.5 * wl, 0)
    p['head'] = (-15 - 2.5 * bl, 16 + 2.0 * math.sin(TAU * f / 180), 2.0 * wl)
    p['gripR'] = add(BASE['gripR'], (-0.12 * w, 0.62 * w - 0.12 * bl, 0.25 * wl))
    p['staff'] = (-0.24 - 0.07 * wl, 0.95, 0.20 + 0.16 * wl)
    p['gripL'] = add(BASE['gripL'], (0.1 * bl, -0.2 * bl, 0.25 * br))
    return p


IDLE = idle(0)     # pose de départ et d'arrivée de toutes les attaques = première frame de l'attente


def window(f, a, b, edge=14):
    return smooth01((f - a) / edge) * smooth01((b - f) / edge)


def idle2(f):
    """variante : regarde autour de lui puis tape deux fois le bâton au sol."""
    p = idle(f % 180)
    look = Keys({'y': 0}, [(0, {'head': (0, 0, 0)}), (14, {'head': (0, 0, 0)}), (30, {'head': (2, 34, -8)}),
                           (44, {'head': (2, 36, -8)}), (60, {'head': (-4, -30, 9)}), (72, {'head': (-4, -30, 9)}),
                           (86, {'head': (0, 0, 0)}), (119, {'head': (0, 0, 0)})])(f)['head']
    p['head'] = add(p['head'], look)
    tap = window(f, 66, 110, 10)
    if tap > 0:
        up = max(0.0, math.sin(TAU * (f - 72) / 16)) if 72 <= f <= 104 else 0.0
        q = dict(p)
        q['staff'] = (-0.14, 0.99, 0.08)
        q['plant'] = 1.0
        q['butty'] = 0.25 + 1.5 * up
        q['gripR'] = (-3.8, -2.0 + 0.7 * up, 1.2)
        p = mix(p, q, tap)
    end = smooth01((f - 105) / 14)
    return mix(p, idle(0), end) if end > 0 else p


def idle3(f):
    """variante : petit rire sautillant en secouant le bâton."""
    p = idle(f % 180)
    w = window(f, 8, 92, 16)
    if w > 0:
        h = abs(math.sin(TAU * f / 32))
        q = dict(p)
        q['hip'] = (0.0, -0.75 + 0.55 * h, -0.2)
        q['bust'] = (-2 + 7 * (1 - h), 4, 0)
        q['head'] = (-22 + 9 * math.sin(TAU * f / 10), 14, 5 * math.sin(TAU * f / 20))
        q['gripR'] = (-4.0, -0.6 + 0.5 * math.sin(TAU * f / 16), 1.0)
        q['staff'] = (-0.28 + 0.14 * math.sin(TAU * f / 12), 0.95, 0.12)
        q['gripL'] = (3.3, -1.4 + 0.5 * h, 1.6)
        p = mix(p, q, w)
    end = smooth01((f - 85) / 14)
    return mix(p, idle(0), end) if end > 0 else p


emit('a00wait1', 180, idle)
emit('a00wait2', 119, idle2)
emit('a00wait3', 99, idle3)


# ═════════════ Accroupi et réceptions : tassé sur ses jambes, masque relevé, bâton planté ═════════════
# Les animations de Ness plient trop le buste pour la taille du masque : Mumbo s'y étalait face contre terre.
CROUCH = pose(
    yaw=-30.0, hip=(0.0, -3.0, -0.45), hrot=(10, 0, 0), waist=(14, 0, 0), bust=(8, 4, 0), head=(-29, 16, 0),
    footL=(0.8, 0.0, 0.8), footR=(-0.8, 0.0, -0.7), footLrot=(0, 20, 0), footRrot=(0, -24, 0),
    kneeL=(0.75, 0.0, 0.8), kneeR=(-0.8, 0.0, 0.7),
    gripR=(-3.9, -1.0, 1.3), elbowR=(-0.9, -0.3, -0.3), staff=(-0.22, 0.96, 0.14), plant=1.0, butty=0.25,
    gripL=(3.3, -1.9, 1.9), elbowL=(0.6, -0.2, -0.8), fist=0.45,
)


def settle(N, keys):
    """poses clés données en profondeur d'accroupi : 0 = attente, 1 = accroupi (> 1 : tassement)."""
    return Keys(IDLE, [(f, mix(IDLE, CROUCH, d), m) for f, d, m in keys])


def crouch_wait(N, look=0.0):
    def fn(f):
        s = math.sin(TAU * f / N)
        s2 = math.sin(TAU * (f - 8) / N) - math.sin(TAU * -8 / N)
        p = dict(CROUCH)
        p['hip'] = add(CROUCH['hip'], (0.0, 0.14 * s, 0.0))
        p['bust'] = add(CROUCH['bust'], (-1.2 * s, 0, 0))
        p['head'] = add(CROUCH['head'], (1.5 * s2, look * math.sin(TAU * f / N), 0.0))
        p['gripL'] = add(CROUCH['gripL'], (0.0, 0.1 * s2, 0.0))
        return p
    return fn


def emit_ground():
    n = length('a05squat')
    emit('a05squat', n, settle(n, [(0, 0.0, 'auto'), (round(n * 0.55), 1.06, 'dec'), (n, 1.0, 'auto')]), keep_trans=True)
    for name, look in (('a05squatwait', 0.0), ('a05squatwaititem', 0.0), ('a05squatwait2', 24.0)):
        n = length(name)
        emit(name, n, crouch_wait(n, look), keep_trans=True)
    n = length('a05squatrv')
    emit('a05squatrv', n, settle(n, [(0, 1.0, 'auto'), (round(n * 0.65), -0.08, 'dec'), (n, 0.0, 'auto')]), keep_trans=True)
    n = length('a03jumpsquat')
    emit('a03jumpsquat', n, settle(n, [(0, 0.25, 'auto'), (n - 2, 0.75, 'dec'), (n, 0.45, 'acc')]), keep_trans=True)
    # réceptions : choc rapide, tassement tenu, remontée avec un léger rebond
    for name, deep in (('a05landinglight', 0.6), ('a05landingheavy', 0.9), ('a04landingfallspecial', 1.0),
                       ('c05landingairn', 0.95), ('c05landingairf', 0.95), ('c05landingairb', 1.0),
                       ('c05landingairhi', 0.9), ('c05landingairlw', 1.0)):
        n = length(name)
        hit = max(2, round(n * 0.12))
        emit(name, n, settle(n, [(0, 0.3 * deep, 'auto'), (hit, deep, 'dec'), (round(n * 0.45), 0.8 * deep, 'auto'),
                                 (round(n * 0.8), -0.07, 'auto'), (n, 0.0, 'auto')]), keep_trans=True)


emit_ground()


# ═════════════ Course : trot comique et énergique ═════════════
RUN_T = 24.0                      # une foulée complète (2 pas)


def foot_path(u):
    """u = phase 0..1 d'un pied ; renvoie (z, y, pitch)."""
    stance = 0.38
    if u < stance:
        v = u / stance
        return 1.55 - 3.0 * v, 0.0, 28 * smooth01((v - 0.65) / 0.35) - 14 * (1 - smooth01(v / 0.25))
    v = (u - stance) / (1 - stance)
    z = -1.45 + 3.0 * (0.5 - 0.5 * math.cos(math.pi * v)) ** 1.15
    y = 2.0 * math.sin(math.pi * v ** 0.75) ** 1.3
    pitch = 28 * (1 - smooth01(v / 0.3)) + 45 * math.sin(math.pi * min(v / 0.8, 1)) - 14 * smooth01((v - 0.7) / 0.3)
    return z, y, pitch


def run(f):
    u = (f / RUN_T) % 1.0
    zl, yl, pl = foot_path(u)
    zr, yr, pr = foot_path((u + 0.5) % 1.0)
    c = math.cos(TAU * u)                                     # +1 : pied gauche devant
    air = 0.5 - 0.5 * math.cos(TAU * 2 * (u - 0.19))          # 0 à l'appui, 1 en suspension
    lag = 0.5 - 0.5 * math.cos(TAU * 2 * (u - 0.27))
    return pose(
        yaw=-4.0, hip=(0.12 * math.sin(TAU * u), -0.95 + 0.75 * air, 0.15),
        hrot=(12, 9 * c, 4 * math.sin(TAU * u)), waist=(9 + 3 * (1 - lag), -5 * c, 0),
        bust=(6 + 4 * (1 - lag), -13 * c, -3 * math.sin(TAU * u)),
        head=(-24 + 5 * lag, 9 * c, 3 * math.sin(TAU * u)),
        footL=(0.1, yl, zl), footR=(-0.1, yr, zr), footLrot=(pl, 6, 0), footRrot=(pr, -6, 0),
        kneeL=(0.3, 0.0, 1.0), kneeR=(-0.3, 0.0, 1.0),
        gripR=(-4.1, -1.7 + 0.55 * lag, 0.1 + 0.8 * c), elbowR=(-0.45, 0.0, -0.9),
        staff=(-0.42, 0.84 + 0.1 * (lag - 0.5), -0.3 + 0.12 * c), slide=1.6,
        gripL=(2.9, -1.9 - 0.7 * c * c + 0.5 * max(-c, 0) + 0.9 * max(-c, 0), 0.5 - 2.5 * c),
        elbowL=(0.45, 0.0, -0.9), fist=1.0,
    )


emit('a02run', 48, run)

DASH = Keys(IDLE, [
    (0, {}),
    (4, {'yaw': -8, 'hip': (0, -1.45, -0.45), 'hrot': (18, 0, 0), 'waist': (14, 0, 0), 'bust': (8, 12, 0), 'head': (-30, -6, 0),
         'footL': (0.2, 0.0, 1.2), 'footR': (-0.2, 0.35, -1.5), 'footRrot': (40, -6, 0), 'footLrot': (0, 6, 0),
         'gripR': (-3.9, -1.9, -0.6), 'staff': (-0.4, 0.88, 0.1), 'gripL': (2.9, -1.7, 1.9), 'fist': 1.0}, 'dec'),
    (9, {'hip': (0, -0.75, 0.55), 'hrot': (22, -8, 0), 'footL': (0.15, 1.2, 0.9), 'footR': (-0.15, 0.1, -1.7),
         'footLrot': (30, 6, 0), 'gripL': (3.0, -2.0, -1.2), 'gripR': (-4.0, -1.6, 0.7)}),
])


def dash(f):
    # se fond dans la course ; la dernière frame (25) = course à la phase 1 → enchaînement net
    return mix(DASH(min(f, 9)), run(f - 25 + RUN_T), smooth01((f - 7) / 13))


emit('a02dash', 25, dash, align_end=(7, 25))


# ═════════════ B haut : lévitation vaudoise (bâton en rotor) ═════════════
ROTOR_TILT = math.radians(26)


def hover(f):
    u = f / 45.0
    s1, s2 = math.sin(TAU * u), math.sin(TAU * (u - 0.12))
    s3 = math.sin(TAU * 3 * u)
    th = TAU * 3 * u                                        # 3 tours par boucle
    ct, st = math.cos(ROTOR_TILT), math.sin(ROTOR_TILT)    # disque incliné : vu de côté, il dessine une ellipse
    up = smooth01(f / 7)                                    # le bâton monte de la main au-dessus du masque
    return pose(
        yaw=-20.0, hip=(0.18 * s2, -0.15 + 0.3 * s1, 0.0), hrot=(-4 + 3 * s2, 5 * s1, 3 * s1),
        waist=(-4, 0, 0), bust=(-6 + 2 * s1, 4 * s2, 0), head=(-16 + 3 * s2, 14, 4 * s2),
        footL=(0.25 + 0.15 * s1, 0.25 + 0.2 * s2, 0.15 + 0.55 * s2),
        footR=(-0.25 + 0.15 * s1, 0.55 - 0.2 * s2, -0.35 - 0.5 * s2),
        footLrot=(38 + 10 * s2, 10, 0), footRrot=(48 - 10 * s2, -10, 0),
        gripR=(-4.4, -0.6 + 3.6 * up + 0.2 * s3, 0.5 + 0.35 * math.cos(th)), elbowR=(-0.9, -0.4, -0.15),
        gripL=(4.4, -0.7 + 0.35 * s2, 0.8), elbowL=(0.5, -0.8, -0.35),
        hold=1.0 - up, float_=up,
        floatpos=(-0.4 + 0.15 * math.cos(th), 20.2 + 0.18 * s3 + 0.3 * s1, 0.2 + 0.15 * math.sin(th)),
        staff=(-math.cos(th) * ct, -math.cos(th) * st + 0.9 * (1 - up), math.sin(th)), fist=0.0,
    )


emit('d02specialairhihold', 45, hover)       # le B haut dure 44 frames : joué une seule fois
emit('d02specialhihold', 45, hover)


# ═════════════ B neutre : Zap ═════════════
ZAP_READY = pose(
    yaw=-6.0, hip=(0.0, -1.0, -0.35), hrot=(4, -10, 0), waist=(6, -14, 0), bust=(5, -22, 0), head=(-10, 40, 0),
    footL=(0.85, 0.0, 1.05), footR=(-0.95, 0.0, -0.85), footLrot=(0, 18, 0), footRrot=(0, -34, 0),
    kneeL=(0.5, 0.0, 1.0), kneeR=(-0.75, 0.0, 0.7),
    gripR=(-2.5, -1.95, -0.1), elbowR=(-0.75, -0.35, -0.55), staff=(0.0, 0.07, 1.0), slide=0.3,
    two=1.0, span=2.0, elbowL=(0.65, -0.75, 0.1), fist=1.0,
)

ZAP_START = Keys(IDLE, [
    (0, {}),
    (5, {'hip': (0, -0.7, 0.0), 'footL': (0.75, 0.7, 0.9), 'footR': (-0.8, 0.0, -0.75), 'two': 0.35,
         'gripR': (-3.7, -1.3, 0.8), 'staff': (-0.3, 0.7, 0.65), 'slide': 1.0}),
    (11, dict(ZAP_READY), 'dec'),
    (24, {'gripR': (-2.65, -2.0, -0.45), 'hip': (0, -1.2, -0.5), 'bust': (3, -27, 0), 'head': (-7, 44, 0),
          'staff': (0.0, 0.12, 1.0)}),
    (44, {'gripR': (-2.7, -2.02, -0.55), 'hip': (0, -1.28, -0.55), 'bust': (2, -29, 0), 'head': (-6, 46, 0)}),
])


def zap_start(f):
    p = ZAP_START(f)
    k = smooth01((f - 10) / 26)                  # la charge fait trembler de plus en plus
    t = k * math.sin(f * 2.2)
    p['gripR'] = add(p['gripR'], (0.05 * t, 0.09 * t, 0.0))
    p['head'] = add(p['head'], (1.2 * k * math.sin(f * 2.2 + 1.0), 0, 0))
    p['bust'] = add(p['bust'], (0.8 * t, 0, 0))
    return p


ZAP_CHARGED = ZAP_START(44)
ZAP_FIRE = Keys(ZAP_CHARGED, [
    (0, {}),
    (2, {'gripR': (-1.35, -1.6, 1.9), 'hip': (0, -1.2, 0.6), 'hrot': (10, -8, 0), 'bust': (12, -20, 0),
         'waist': (8, -12, 0), 'head': (-12, 36, 0), 'staff': (0.04, 0.03, 1.0), 'span': 1.5}, 'dec'),
    (7, {'gripR': (-2.2, -1.5, 0.35), 'hip': (0, -1.0, -0.75), 'hrot': (-5, -10, 0), 'waist': (-2, -14, 0),
         'bust': (-6, -22, 0), 'head': (0, 36, 0), 'staff': (0.02, 0.22, 1.0), 'span': 1.8}, 'dec'),
    (13, {'gripR': (-2.3, -1.4, 0.4), 'hip': (0, -1.1, -0.65), 'bust': (0, -20, 0), 'staff': (0.0, 0.1, 1.0),
          'two': 1.0, 'span': 1.8, 'slide': 0.3, 'footL': ZAP_READY['footL'], 'footR': ZAP_READY['footR']}),
    (21, {k: IDLE[k] for k in ('yaw', 'hip', 'hrot', 'waist', 'bust', 'head', 'footL', 'footR', 'footLrot', 'footRrot',
                               'kneeL', 'kneeR', 'gripR', 'elbowR', 'staff', 'slide', 'two', 'gripL', 'elbowL', 'fist')}),
])


def with_air(fn):
    """version aérienne : pieds repliés, sans appui au sol."""
    def g(f):
        p = dict(fn(f))
        p['footL'] = add(p['footL'], (-0.25, 0.65, 0.0))
        p['footR'] = add(p['footR'], (0.25, 0.95, 0.0))
        p['footLrot'] = add(p['footLrot'], (28, 0, 0))
        p['footRrot'] = add(p['footRrot'], (36, 0, 0))
        return p
    return g


emit('d00specialnstart', 44, zap_start, align_end=(5, 30))
emit('d00specialairnstart', 44, with_air(zap_start), align_end=(5, 30))
emit('d00specialnfire', 22, ZAP_FIRE, align_end=(10, 22))
emit('d00specialnairfire', 22, with_air(ZAP_FIRE), align_end=(10, 22))


# ═════════════ Smash côté : coup de bâton massif (touche frame 18) ═════════════
HIGH = dict(
    yaw=-12.0, hip=(0.0, -0.75, -0.65), hrot=(-6, -16, 0), waist=(-8, -18, 0), bust=(-12, -24, 0), head=(-4, 46, 6),
    footL=(0.5, 0.0, 1.0), footR=(-0.7, 0.0, -0.9), footLrot=(0, 12, 0), footRrot=(0, -30, 0),
    kneeL=(0.4, 0.0, 1.0), kneeR=(-0.6, 0.0, 0.8),
    gripR=(-3.9, 2.5, -0.1), elbowR=(-0.95, -0.25, -0.2), staff=(-0.36, 0.87, -0.34), slide=0.9,
    two=1.0, span=-2.0, elbowL=(0.35, -0.9, 0.3), fist=1.0,
)
FS = Keys(IDLE, [
    (0, {}),
    (4, {'hip': (0, -1.05, -0.3), 'two': 0.6, 'gripR': (-3.6, -1.2, 0.5), 'staff': (-0.35, 0.92, -0.15), 'span': -2.0}),
    (11, HIGH, 'dec'),
    (14, {'ground': 0.0, 'gripR': (-3.95, 2.7, -0.3), 'staff': (-0.34, 0.82, -0.46), 'bust': (-14, -27, 0), 'hip': (0, -0.6, -0.75),
          'footL': (0.5, 0.9, 1.4)}),
    (16, {'ground': 0.0, 'elbowL': (0.5, -0.85, 0.2), 'yaw': -8, 'gripR': (-4.0, 0.6, 1.2), 'staff': (-0.5, 0.68, 0.54), 'bust': (8, -6, 0), 'waist': (6, -4, 0),
          'hip': (0, -0.9, 0.2), 'footL': (0.5, 0.35, 2.0), 'span': 1.0}, 'acc'),
    (18, {'yaw': 0, 'hip': (0, -1.6, 0.8), 'hrot': (14, 8, 0), 'waist': (18, 6, 0), 'bust': (18, -6, 0), 'head': (-30, 6, 0),
          'footL': (0.55, 0.0, 2.2), 'footR': (-0.6, 0.1, -1.0), 'footRrot': (30, -24, 0),
          'gripR': (-2.3, -2.2, 2.1), 'elbowR': (-0.9, -0.2, -0.4), 'staff': (0.04, -0.4, 0.92), 'ground': 1.0, 'span': 1.1,
          'elbowL': (0.8, -0.55, 0.0)}, 'lin'),
    (21, {'hip': (0, -1.9, 0.9), 'bust': (22, -6, 0), 'head': (-34, 6, 0), 'gripR': (-2.3, -2.35, 2.0)}, 'dec'),
    (30, {'hip': (0, -1.75, 0.85), 'bust': (18, -4, 0), 'head': (-26, 4, 0), 'gripR': (-2.4, -2.25, 2.0),
          'two': 1.0, 'ground': 1.0, 'span': 1.1, 'staff': (0.04, -0.4, 0.92), 'elbowR': (-0.9, -0.2, -0.4),
          'elbowL': (0.8, -0.55, 0.0), 'footL': (0.55, 0.0, 2.2), 'footR': (-0.6, 0.1, -1.0), 'footRrot': (30, -24, 0)}),
    (40, {'hip': (0, -1.2, 0.4), 'hrot': (8, 0, 0), 'waist': (10, 0, 0), 'bust': (8, 0, 0), 'gripR': (-3.7, -1.9, 1.7),
          'staff': (-0.35, 0.35, 0.87), 'ground': 0.0, 'two': 0.0, 'footL': (0.45, 0.35, 1.3)}),
    (56, {k: IDLE[k] for k in IDLE}),
    (63, {}),
])


def fs_charge(f):
    p = dict(FS(11))
    t = math.sin(TAU * f / 6) * (0.4 + 0.6 * smooth01(f / 30) * smooth01((60 - f) / 6))
    br = math.sin(TAU * f / 30)
    p['gripR'] = add(p['gripR'], (0.05 * t, 0.08 * t + 0.1 * br, 0.0))
    p['hip'] = add(p['hip'], (0.0, 0.1 * br, 0.0))
    p['bust'] = add(p['bust'], (1.0 * t - 1.5 * br, 0, 0))
    p['head'] = add(p['head'], (1.5 * t, 0, 0))
    return p


emit('c03attacks4s', 63, FS, keep_trans=True)
emit('c03attacks4charge', 60, fs_charge, seed=(FS, 11))


# ═════════════ B bas : socle de Mumbo (deux tapes, frames 10 et 19) ═════════════
KNEEL = dict(
    yaw=-18.0, hip=(0.0, -2.05, -0.2), hrot=(10, 0, 0), waist=(12, 0, 0), bust=(10, -6, 0), head=(-16, 22, 0),
    footL=(0.6, 0.0, 1.35), footR=(-0.45, 0.3, -2.0), footLrot=(0, 12, 0), footRrot=(62, -10, 0),
    kneeL=(0.45, 0.3, 1.0), kneeR=(-0.25, -0.55, 0.85),
    gripR=(-3.9, -1.1, 1.9), elbowR=(-0.95, -0.25, -0.2), staff=(-0.13, 0.99, 0.08), plant=1.0, butty=1.7,
    gripL=(3.3, -2.1, 1.7), elbowL=(0.5, -0.1, -0.85), fist=0.0,
)
PAD = Keys(IDLE, [
    (0, {}),
    (3, {'hip': (0, -0.2, -0.15), 'gripR': (-3.9, -0.7, 1.7), 'plant': 1.0, 'butty': 3.0, 'staff': (-0.15, 0.99, 0.1)}),
    (7, KNEEL),
    (10, {'butty': 0.15, 'gripR': (-3.9, -2.1, 1.95), 'bust': (17, -4, 0), 'head': (-12, 20, 0), 'gripL': (3.5, -1.5, 1.9)}, 'acc'),
    (15, {'butty': 2.1, 'gripR': (-3.9, -0.7, 1.85), 'bust': (6, -6, 0), 'head': (-20, 24, 0)}, 'dec'),
    (19, {'butty': 0.15, 'gripR': (-3.9, -2.2, 1.95), 'bust': (19, -4, 0), 'head': (-10, 20, 0), 'gripL': (3.6, -1.3, 2.0)}, 'acc'),
    (28, dict(KNEEL, butty=0.15, gripR=(-3.9, -2.0, 1.9), bust=(13, -5, 0), head=(-20, 22, 0))),
    (34, {'butty': 0.2, 'hip': (0, -1.4, -0.2), 'footR': (-0.45, 0.7, -1.2), 'footRrot': (30, -14, 0)}),
    (43, dict({k: IDLE[k] for k in IDLE}, hip=(0, -0.3, -0.15), plant=0.0)),
    (50, {k: IDLE[k] for k in IDLE}),
])
emit('d03speciallwstart', 50, PAD)


def pad_air(f):
    p = dict(PAD(f))
    k = smooth01(f / 7) * smooth01((50 - f) / 10)
    p['footL'] = add(p['footL'], (-0.2, 1.25 * k + 0.2, -0.6 * k))
    p['footR'] = add(p['footR'], (0.2, 0.6, 0.4 * k))
    p['footLrot'] = add(p['footLrot'], (20, 0, 0))
    p['butty'] = p['butty'] + 0.35
    return p


emit('d03specialairlwstart', 50, pad_air)


# ═════════════ Air : pose de référence ═════════════
AIR = pose(
    yaw=-24.0, hip=(0.0, -0.15, 0.0), hrot=(4, 0, 0), waist=(4, 0, 0), bust=(3, 3, 0), head=(-8, 16, 0),
    footL=(0.3, 0.75, 0.45), footR=(-0.35, 0.3, -0.55), footLrot=(24, 10, 0), footRrot=(36, -12, 0),
    gripR=(-4.1, -0.9, 0.7), elbowR=(-0.45, -0.1, -0.9), staff=(-0.3, 0.9, 0.3), slide=2.0,
    gripL=(3.9, -1.2, 0.8), elbowL=(0.45, -0.1, -0.9), fist=0.25,
)

# Chute libre (après le B haut) : épuisé, membres ballants, le bâton traîne derrière lui.
# Sans ces animations, la chute libre de Ness met la plante des pieds face caméra et le bâton en travers du masque.
def fall_special(n, lean):
    def fn(f):
        th = TAU * f / n
        s, c = math.sin(th), math.cos(th)
        p = dict(AIR)
        p['yaw'] = -24.0
        p['hrot'] = (9 + 9 * lean + 0.8 * s, 0, 1.0 * c)
        p['bust'] = (8 + 3 * lean, 0, -0.8 * c)
        p['head'] = (12 + 1.0 * math.sin(th - 0.8), 10, 2.0 * math.sin(th - 1.2))
        p['footL'] = (0.45, 0.35 + 0.12 * s, 0.35 - 0.7 * lean)
        p['footR'] = (-0.45, 0.15 - 0.12 * s, -0.35 - 0.7 * lean)
        p['footLrot'] = (34 + 2 * s, 8, 0)
        p['footRrot'] = (40 - 2 * s, -8, 0)
        p['gripR'] = (-4.3, -1.7 + 0.12 * c, -0.4)
        p['elbowR'] = (-0.5, 0.15, -0.85)
        p['staff'] = (-0.35, 0.45 + 0.05 * s, -0.82)
        p['gripL'] = (4.3, 0.3 + 0.35 * s, 0.6)
        p['elbowL'] = (0.5, -0.5, -0.7)
        p['fist'] = 0.0
        return p
    return fn


for _name, _lean in (('a04fallspecial', 0.0), ('a04fallspecialf', 1.0), ('a04fallspecialb', -1.0)):
    _n = length(_name)
    emit(_name, _n, fall_special(_n, _lean))


# Aérien avant : coup de tête (touche 14-16), puis revers du bâton (18-22)
FAIR = Keys(AIR, [
    (0, {}),
    (4, {'hrot': (-6, 0, 0), 'waist': (-6, 0, 0), 'bust': (-8, 0, 0), 'head': (-14, 8, 0), 'yaw': -10}),
    (10, {'yaw': 0, 'hip': (0, 0.15, -0.75), 'hrot': (-20, 0, 0), 'waist': (-18, 0, 0), 'bust': (-20, 0, 0), 'head': (-30, 0, 0),
          'footL': (0.2, 1.7, 1.0), 'footR': (-0.2, 1.5, 0.8), 'footLrot': (10, 6, 0), 'footRrot': (14, -6, 0),
          'elbowR': (-0.6, 0.25, -0.75), 'elbowL': (0.6, 0.25, -0.75),
          'gripR': (-3.6, -0.5, 1.9), 'gripL': (3.6, -0.6, 1.9), 'staff': (-0.45, 0.85, 0.25), 'fist': 1.0}, 'dec'),
    (14, {'hip': (0, -0.1, 1.15), 'hrot': (26, 0, 0), 'waist': (24, 0, 0), 'bust': (20, 0, 0), 'head': (20, 0, 0),
          'footL': (0.2, 1.35, -1.4), 'footR': (-0.2, 0.9, -1.5), 'footLrot': (55, 6, 0), 'footRrot': (60, -6, 0),
          'gripR': (-3.6, -1.7, -2.1), 'gripL': (3.5, -1.7, -2.3), 'elbowR': (-0.35, 0.93, -0.1), 'elbowL': (0.35, 0.93, -0.1),
          'staff': (-0.85, 0.45, -0.3)}, 'acc'),
    (16, {'hip': (0, -0.15, 1.25), 'head': (24, 0, 0), 'elbowR': (-0.35, 0.93, -0.1), 'gripR': (-3.6, -1.65, -2.2), 'gripL': (3.5, -1.65, -2.35)}),
    (18, {'hip': (0, -0.15, 0.9), 'hrot': (20, 6, 0), 'bust': (14, 14, 0), 'head': (0, -6, 0),
          'gripR': (-3.9, -1.6, 0.9), 'staff': (-0.85, -0.15, 0.5), 'elbowR': (-0.4, 0.55, -0.7)}),
    (21, {'elbowR': (-0.7, -0.2, -0.7), 'gripR': (-3.0, -1.8, 3.0), 'staff': (0.05, -0.2, 0.98), 'bust': (14, 28, 0), 'head': (-14, -18, 0),
          'gripL': (3.9, -1.2, -1.2)}),
    (27, {'gripR': (-2.9, -1.9, 2.8), 'staff': (0.1, -0.1, 0.99), 'hrot': (14, 6, 0)}),
    (40, dict({k: AIR[k] for k in AIR})),
    (49, {}),
])
emit('c05attackairf', 49, FAIR)

# Aérien neutre : moulinet horizontal à deux mains, deux tours complets
SPIN_HOLD = dict(
    hip=(0.0, -0.2, 0.0), hrot=(8, 0, 0), waist=(6, 0, 0), bust=(4, 0, 0), head=(-12, 0, 0),
    footL=(0.5, 1.2, 0.5), footR=(-0.5, 0.55, -0.7), footLrot=(30, 14, 0), footRrot=(42, -14, 0),
    gripR=(-2.5, -1.7, 2.7), elbowR=(-0.9, -0.35, -0.15), staff=(-1.0, 0.0, 0.05), slide=2.6,
    two=1.0, span=-4.7, elbowL=(0.9, -0.35, -0.15), fist=1.0,
)
NAIR = Keys(AIR, [
    (0, {}),
    (4, dict(SPIN_HOLD, yaw=-55.0), 'auto'),
    (9, {'yaw': 40.0}, 'acc'),
    (22, {'yaw': 618.0, 'footL': (0.9, 1.0, 0.2), 'footR': (-0.9, 0.7, -0.3)}, 'lin'),
    (30, dict(SPIN_HOLD, yaw=704.0, hrot=(4, 0, 0)), 'dec'),
    (34, {'yaw': 696.0, 'two': 0.6}),
    (39, {'two': 0.0}),
    (46, dict({k: AIR[k] for k in AIR}, yaw=696.0)),
    (48, {}),
])

emit('c05attackairn', 48, NAIR)


# ═════════════ Provocation haute : « Eekum Bokum » (59 frames) ═════════════
HOPS = [(0, 7, 'L'), (7, 18, 'R'), (18, 29, 'L'), (29, 40, 'R'), (40, 48, 'L')]


def dance_core(f):
    for a, b, side in HOPS:
        if a <= f <= b:
            break
    else:
        a, b, side = 48, 59, 'B'
    u = (f - a) / (b - a)
    h = math.sin(math.pi * u)
    if side == 'B':
        h = math.sin(math.pi * min(u * 1.6, 1.0)) * 0.35
    # le pied d'appui à la réception (frame b) est `side`
    landing = smooth01(u)
    s = 1.0 if side == 'L' else (-1.0 if side == 'R' else 0.0)
    prev = -s
    sway = prev + (s - prev) * landing
    liftL = max(-sway, 0.0)           # pied gauche levé quand le poids est à droite
    liftR = max(sway, 0.0)
    sh = math.sin(TAU * f / 6.0)
    return pose(
        yaw=-18 + 12 * sway, hip=(0.55 * sway, -0.8 + 0.35 * h, -0.1), hrot=(6, 6 * sway, -7 * sway),
        waist=(6, 0, -4 * sway), bust=(2 + 5 * (1 - h), -8 * sway, 6 * sway), head=(-14 + 12 * (1 - h) - 4, 12 - 6 * sway, 11 * sway),
        lift=1.35 * h,
        footL=(0.55, 1.5 * liftL, 0.35 + 0.7 * liftL), footR=(-0.55, 1.5 * liftR, 0.05 + 0.7 * liftR),
        footLrot=(30 * liftL, 20, 0), footRrot=(30 * liftR, -20, 0), kneeL=(0.55, 0.0, 1.0), kneeR=(-0.55, 0.0, 1.0),
        gripR=(-4.35, 1.85 + 0.55 * sh + 0.4 * h, 0.55), elbowR=(-0.75, -0.65, -0.1),
        staff=(-0.28 + 0.2 * math.sin(TAU * f / 12.0), 0.96, 0.08 * sh), slide=1.2,
        gripL=(4.0, -0.9 + 1.8 * liftR - 0.2 * liftL, 1.2), elbowL=(0.6, -0.8, -0.2), fist=0.1,
    )


def dance(f):
    p = dance_core(f)
    if f >= 48:                     # bouquet final : bâton brandi puis retour
        k = smooth01((f - 48) / 3) * smooth01((55 - f) / 4)
        top = dict(p, gripR=(-4.3, 2.6, 0.5), staff=(-0.2, 0.98, 0.0), bust=(-10, 0, 0), head=(-26, 12, 0),
                   gripL=(4.3, 1.2, 0.8))
        p = mix(p, top, k)
    w = smooth01(f / 7) * smooth01((59 - f) / 8)
    return mix(IDLE, p, w)


emit('j01appealhir', 59, dance)


# ═════════════ Victoire : lévitation assise sur le bâton ═════════════
SEAT_LIFT = 2.6
SEAT_X = -1.7          # décalé vers le crâne pour qu'il dépasse des pieds
SEAT_Y = 0.75          # hauteur du bâton sous les fesses, relative à `lift` (floatpos suit le saut)
SIT = pose(
    yaw=0.0, lift=SEAT_LIFT, hip=(0.0, -1.55, 0.0), hrot=(-6, 0, 0), waist=(0, 0, 0), bust=(-4, 0, 0), head=(-9, 6, 9),
    footL=(-1.85, 1.35, 1.65), footR=(1.85, 1.0, 1.35), footLrot=(10, -75, 0), footRrot=(10, 75, 0),
    kneeL=(1.0, 0.05, 0.45), kneeR=(-1.0, 0.05, 0.45),
    gripR=(1.15, -1.55, 2.15), elbowR=(-0.8, -0.55, 0.2), gripL=(-1.15, -2.15, 2.4), elbowL=(0.8, -0.55, 0.2),
    hold=0.0, float_=1.0, floatpos=(SEAT_X, SEAT_Y, -0.35), staff=(-1.0, 0.0, 0.0), fist=0.8,
)


def sit_bob(f):
    """boucle de 90 frames, f=0 = hauteur moyenne."""
    s = math.sin(TAU * f / 90.0)
    s2 = math.sin(TAU * (f - 10) / 90.0)
    p = dict(SIT)
    p['lift'] = SEAT_LIFT + 0.42 * s
    p['floatpos'] = add(SIT['floatpos'], (0.0, 0.08 * math.sin(TAU * (f - 8) / 90.0), 0.0))     # léger retard sur le corps
    p['head'] = add(SIT['head'], (2.5 * s2, 3 * math.sin(TAU * f / 90.0 + 1.5) - 3 * math.sin(1.5), 2.0 * s2 + 2.0 * math.sin(TAU * 10 / 90)))
    p['bust'] = add(SIT['bust'], (1.8 * s2 + 1.8 * math.sin(TAU * 10 / 90), 0, 0))
    p['footL'] = add(SIT['footL'], (0.0, 0.07 * s2, 0.0))
    p['footR'] = add(SIT['footR'], (0.0, 0.07 * s2, 0.0))
    return p


STAND = pose(**dict(IDLE, floatpos=(-3.6, 5.5, 1.4)))
WIN = Keys(STAND, [
    (0, {}),
    (10, {'hip': (0, -0.35, -0.15), 'gripR': (-3.9, -0.6, 1.4), 'head': (-16, 8, 0), 'float_': 0.0, 'hold': 1.0,
          'floatpos': (-3.6, 5.5, 1.4), 'staff': IDLE['staff'], 'fist': 0.45, 'yaw': -10.0}),
    (28, {'float_': 1.0, 'hold': 0.0, 'floatpos': (-1.6, 3.4, 3.2), 'staff': (-0.85, 0.45, 0.25),
          'gripR': (-4.2, -0.9, 1.8), 'gripL': (4.0, -1.0, 1.8), 'head': (4, 0, 0), 'fist': 0.0, 'yaw': 0.0}),
    (42, {'lift': 0.0, 'kneeL': IDLE['kneeL'], 'kneeR': IDLE['kneeR'], 'floatpos': (SEAT_X, SEAT_LIFT + SEAT_Y - 0.6, 3.6), 'staff': (-1.0, 0.0, 0.0),
          'hip': (0, -1.7, -0.2), 'hrot': (16, 0, 0), 'bust': (12, 0, 0), 'head': (-20, 0, 0),
          'footL': (0.4, 0.0, 0.3), 'footR': (-0.4, 0.0, -0.2), 'footLrot': (0, 10, 0), 'footRrot': (0, -10, 0),
          'gripR': (-4.2, -2.0, 0.3), 'gripL': (4.2, -2.0, 0.3)}),
    (46, {'floatpos': (SEAT_X, SEAT_LIFT + SEAT_Y, 3.2)}),
    (52, {'floatpos': (SEAT_X, SEAT_LIFT + SEAT_Y, -0.35)}),
    (51, {'lift': SEAT_LIFT + 2.5, 'hip': (0, -0.5, 0.0), 'hrot': (4, 0, 0), 'bust': (-6, 0, 0), 'head': (-16, 0, 0),
          'footL': (-0.3, 2.0, 1.0), 'footR': (0.3, 1.8, 0.9), 'footLrot': (20, -30, 0), 'footRrot': (20, 30, 0),
          'kneeL': (0.7, 0.0, 0.8), 'kneeR': (-0.7, 0.0, 0.8), 'gripR': (-4.4, 0.9, 0.8), 'gripL': (4.4, 0.9, 0.8)}, 'dec'),
    (62, dict({k: SIT[k] for k in SIT}, lift=SEAT_LIFT - 0.55, bust=(8, 0, 0), head=(2, 3, 5),
              gripR=(-3.0, -2.2, 1.9), gripL=(3.0, -2.3, 1.9)), 'acc'),
    (72, {'lift': SEAT_LIFT + 0.25, 'bust': (-7, 0, 0), 'head': (-14, 6, 9), 'gripR': (-1.0, -1.2, 3.2), 'gripL': (1.0, -1.9, 3.3)}),
    (82, dict({k: SIT[k] for k in SIT}), 'auto'),
    (135, {}),
])


def win(f):
    p = WIN(f)
    if f > 82:
        k = smooth01((f - 82) / 16)
        p = mix(p, sit_bob(f - 135), k)
    if 42 <= f < 62:
        # le bâton attend à hauteur d'assise pendant le saut, puis accompagne le poids à la réception
        w = smooth01((f - 54) / 8)
        x, y, z = p['floatpos']
        wait = SEAT_LIFT + SEAT_Y - 0.6 * (1 - smooth01((f - 42) / 8)) - p['lift']
        p['floatpos'] = (x, wait + (SEAT_Y - wait) * w, z)
    return p


emit('j02win1', 135, win, align_end=(60, 125))
emit('j02win1wait', 90, sit_bob)


import attacks
attacks.register(emit, IDLE, AIR, CROUCH)
