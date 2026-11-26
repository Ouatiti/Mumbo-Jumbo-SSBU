"""Combo neutre, attaques inclinées et dash, smashs haut / bas, aériennes restantes, saisies et projections.

Appelé à la fin de moves.py. Les durées sont celles de Ness et les frames de frappe celles de
src/normals.rs (ou, pour les saisies et le dash, celles de Ness). Les hitboxes « haver » sont
placées le long du manche : la pose à la frame de frappe doit pointer le bâton vers la cible.
"""
import math
from poses import (S, REST_L, PARENT, pose, mix, smooth01, Keys, length, read_nodes, tf_mat, V)

TAU = 2 * math.pi


def register(emit, IDLE, AIR, CROUCH):
    def full(base, **kw):
        return dict(base, **kw)

    def seq(base, N, keys, end=None):
        """poses clés partant de `base` et revenant à `end` (par défaut `base`) à la dernière frame."""
        return Keys(base, [(0, {})] + keys + [(N, full(end or base))])

    def attack(name, keys, base=IDLE, end=None, back=None, **kw):
        """`back` = frame où la pose de fin est atteinte (tenue ensuite jusqu'au bout)."""
        N = length(name)
        end = end or base
        if back:
            keys = keys + [(back, full(end))]
        fn = seq(base, N, keys, end)
        kw.setdefault('align_end', (min(round(N * 0.45), N - 6), N))
        emit(name, N, fn, **kw)
        return fn

    def tremble(held, N=60):
        """boucle de charge d'un smash : la pose chargée tremble de plus en plus."""
        def fn(f):
            p = dict(held)
            t = math.sin(TAU * f / 6) * (0.4 + 0.6 * smooth01(f / 30) * smooth01((N - f) / 6))
            br = math.sin(TAU * f / 30)
            p['gripR'] = (p['gripR'][0] + 0.05 * t, p['gripR'][1] + 0.08 * t + 0.1 * br, p['gripR'][2])
            p['hip'] = (p['hip'][0], p['hip'][1] + 0.1 * br, p['hip'][2])
            p['bust'] = (p['bust'][0] + 1.0 * t - 1.5 * br, p['bust'][1], p['bust'][2])
            p['head'] = (p['head'][0] + 1.5 * t, p['head'][1], p['head'][2])
            return p
        return fn

    # ═════════ Combo neutre ═════════
    STAND = dict(footL=(0.6, 0.0, 1.1), footR=(-0.65, 0.0, -0.7))
    # 1 : estoc sec, bâton à l'horizontale (frappe 4)
    JAB1 = dict(STAND, yaw=-8.0, hip=(0.0, -0.85, 0.45), hrot=(8, -6, 0), waist=(8, -8, 0), bust=(8, -10, 0),
                head=(-18, 24, 0), gripR=(-3.2, -1.7, 2.7), elbowR=(-0.9, -0.35, -0.3), staff=(0.06, 0.04, 1.0),
                slide=0.8, gripL=(3.6, -1.6, -0.4), fist=1.0)
    attack('c00attack11', [
        (2, full(JAB1, hip=(0.0, -0.8, -0.15), gripR=(-3.7, -1.6, 0.3), staff=(-0.1, 0.35, 0.93), bust=(4, -2, 0)), 'dec'),
        (4, JAB1, 'acc'), (8, full(JAB1, gripR=(-3.25, -1.75, 2.55))),
    ], back=22)
    # 2 : revers montant (frappe 4)
    JAB2 = dict(JAB1, yaw=-22.0, bust=(2, 10, 0), waist=(5, 6, 0), gripR=(-3.0, -1.0, 2.8), staff=(0.1, 0.22, 0.97),
                head=(-16, 6, 0))
    attack('c00attack12', [
        (2, full(JAB2, bust=(10, -20, 0), gripR=(-3.7, -2.4, 0.9), staff=(-0.15, -0.2, 0.97), head=(-18, 32, 0)), 'dec'),
        (4, JAB2, 'acc'),
        (8, full(JAB2, gripR=(-3.5, 0.2, 2.1), staff=(-0.1, 0.75, 0.65)), 'dec'),
    ], back=22)
    # 3 : grand coup à deux mains, pas en avant (frappe 6)
    JAB3_UP = dict(yaw=-14.0, hip=(0.0, -0.8, -0.5), hrot=(-4, -16, 0), waist=(-6, -18, 0), bust=(-8, -22, 0),
                   head=(-8, 44, 0), footL=(0.5, 0.5, 0.9), footR=(-0.7, 0.0, -0.8),
                   gripR=(-3.8, 1.2, -0.2), elbowR=(-0.95, -0.25, -0.2), staff=(-0.4, 0.8, -0.45), slide=0.9,
                   two=1.0, span=-2.0, elbowL=(0.35, -0.9, 0.3), fist=1.0)
    JAB3_HIT = dict(JAB3_UP, yaw=-2.0, hip=(0.0, -1.35, 0.75), hrot=(12, 6, 0), waist=(14, 6, 0), bust=(14, -2, 0),
                    head=(-24, 4, 0), footL=(0.55, 0.0, 1.9), footR=(-0.6, 0.0, -0.9),
                    gripR=(-2.5, -2.0, 2.3), elbowR=(-0.9, -0.2, -0.4), staff=(0.05, -0.1, 0.99), span=1.1,
                    elbowL=(0.8, -0.55, 0.0))
    attack('c00attack13', [
        (3, JAB3_UP, 'dec'), (6, JAB3_HIT, 'acc'),
        (10, full(JAB3_HIT, gripR=(-2.4, -2.3, 2.2), staff=(0.1, -0.28, 0.95), hip=(0.0, -1.55, 0.8)), 'dec'),
        (22, full(JAB3_HIT, staff=(0.05, -0.2, 0.98))),
    ], back=40, keep_trans=True)

    # ═════════ Attaque en course : charge à la lance (frappes 7, 13, 19) ═════════
    LANCE = dict(yaw=-6.0, hip=(0.0, -1.5, 0.7), hrot=(18, -6, 0), waist=(14, -8, 0), bust=(10, -12, 0),
                 head=(-34, 24, 0), footL=(0.5, 0.0, 1.7), footR=(-0.55, 0.35, -1.6), footRrot=(45, -12, 0),
                 gripR=(-2.9, -2.0, 1.9), elbowR=(-0.9, -0.35, -0.35), staff=(0.05, 0.04, 1.0), slide=0.5,
                 two=1.0, span=2.0, elbowL=(0.65, -0.75, 0.1), fist=1.0)
    PUSH = dict(LANCE, gripR=(-2.6, -2.05, 2.8), hip=(0.0, -1.75, 1.05), staff=(0.04, 0.0, 1.0))
    PULL = dict(LANCE, gripR=(-3.0, -1.9, 1.35), hip=(0.0, -1.35, 0.5), staff=(0.05, 0.09, 1.0))
    attack('c00attackdash', [
        (4, PULL, 'dec'), (7, PUSH, 'acc'), (10, PULL), (13, PUSH, 'acc'), (16, PULL), (19, PUSH, 'acc'),
        (28, full(PUSH, hip=(0.0, -1.5, 0.8))),
        (36, full(IDLE, hip=(0.0, -1.1, 0.2), footL=(0.45, 0.35, 1.0))),
    ], back=45, keep_trans=True)

    # ═════════ Inclinée côté : grand balayage à une main (frappe 8) ═════════
    for suffix, dy, low in (('s', 0.0, 0.0), ('hi', 0.42, -0.2), ('lw', -0.36, 0.45)):
        hit = dict(STAND, yaw=2.0, hip=(0.0, -1.0 - low, 0.65), hrot=(8 + 8 * low, 8, 0), waist=(8 + 10 * low, 14, 0),
                   bust=(6 + 10 * low - 14 * max(dy, 0), 20, 0), head=(-18 - 14 * low, -22, 0),
                   footL=(0.55, 0.0, 1.7), gripR=(-2.8, -1.4 + 1.9 * dy - 0.5 * low, 2.7),
                   elbowR=(-0.9, -0.3, -0.3), staff=(0.05, dy, 1.0 - 0.3 * abs(dy)), slide=0.7,
                   gripL=(3.8, -1.3, -1.2), fist=1.0)
        wind = dict(STAND, yaw=-44.0, hip=(0.0, -1.0 - 0.5 * low, -0.55), hrot=(2, -14, 0), waist=(2, -16, 0),
                    bust=(0, -22, 0), head=(-12, 52, 0), footL=(0.5, 0.35, 1.2),
                    gripR=(-4.0, -0.5 + 0.5 * dy, -0.9), elbowR=(-0.8, -0.3, -0.5), staff=(-0.55, 0.35 + dy, -0.75),
                    slide=0.7, gripL=(3.0, -1.5, 2.2), fist=1.0)
        side = dict(hit, yaw=-18.0, bust=(2, -2, 0), head=(-16, 20, 0), gripR=(-4.2, -1.0 + dy, 1.4),
                    staff=(-0.9, 0.1 + dy * 0.7, 0.35), hip=(0.0, -1.1 - low, 0.2))
        thru = dict(hit, yaw=10.0, bust=(8 + 10 * low - 14 * max(dy, 0), 32, 0), head=(-18 - 14 * low, -34, 0),
                    gripR=(-1.9, -1.5 + 1.9 * dy - 0.5 * low, 2.5), staff=(0.6, dy * 1.1, 0.75))
        attack('c01attacks3' + suffix, [
            (4, wind, 'dec'), (6, side, 'acc'), (8, hit, 'lin'), (12, thru, 'dec'), (24, full(thru, staff=(0.65, dy, 0.7))),
            (36, full(STAND_POSE(IDLE), gripR=(-3.6, -1.9, 2.0), staff=(-0.2, 0.6, 0.78))),
        ], back=48, keep_trans=True)

    # ═════════ Inclinée haut : arc au-dessus du masque (frappe 7-11) ═════════
    attack('c02attackhi3', [
        (3, full(IDLE, yaw=-16.0, hip=(0.0, -1.45, 0.1), waist=(14, 6, 0), bust=(10, 12, 0), head=(-24, 4, 0),
                 gripR=(-3.8, -2.2, 2.0), staff=(-0.3, -0.05, 0.95), slide=0.8, gripL=(3.5, -2.0, 0.4)), 'dec'),
        (7, full(IDLE, yaw=-14.0, hip=(0.0, -0.45, 0.1), waist=(-2, -2, 0), bust=(-8, -4, 0), head=(-24, 18, -6),
                 gripR=(-4.4, 1.7, 1.5), elbowR=(-0.9, -0.4, -0.1), staff=(-0.36, 0.72, 0.6), slide=0.8,
                 gripL=(3.8, -1.7, 0.8), fist=1.0), 'acc'),
        (9, full(IDLE, yaw=-18.0, hip=(0.0, -0.3, -0.1), bust=(-12, -8, 0), waist=(-6, -4, 0), head=(-18, 22, -8),
                 gripR=(-4.4, 2.6, 0.2), elbowR=(-0.95, -0.25, -0.2), staff=(-0.4, 0.91, -0.05), slide=0.8,
                 gripL=(3.8, -1.7, 0.5), fist=1.0), 'lin'),
        (13, full(IDLE, yaw=-28.0, hip=(0.0, -0.8, -0.4), bust=(-6, -18, 0), head=(-10, 36, -4),
                  gripR=(-4.4, 0.6, -1.4), elbowR=(-0.9, -0.35, -0.2), staff=(-0.45, 0.35, -0.82), slide=0.8,
                  gripL=(3.5, -1.6, 1.4), fist=1.0), 'dec'),
        (22, {'gripR': (-4.35, 0.4, -1.4)}),
        (31, full(IDLE, gripR=(-4.3, 0.4, 0.4), staff=(-0.42, 0.9, -0.1))),
    ], back=42, end=IDLE)

    # ═════════ Inclinée bas : estoc au ras du sol, accroupi (frappe 7) ═════════
    LOW_READY = dict(CROUCH, plant=0.0, gripR=(-3.8, -1.7, 0.2), staff=(-0.25, 0.2, 0.95), slide=1.2)
    LOW_HIT = dict(CROUCH, plant=0.0, ground=1.0, yaw=-6.0, hip=(0.0, -3.05, 0.35), hrot=(14, -4, 0),
                   waist=(14, -6, 0), bust=(8, -10, 0), head=(-34, 22, 0), gripR=(-2.9, -2.4, 2.8),
                   elbowR=(-0.95, -0.3, -0.2), staff=(0.06, -0.2, 0.98), slide=0.6, gripL=(3.6, -1.5, 0.3), fist=1.0)
    N = length('c02attacklw3')
    attack('c02attacklw3', [
        (4, LOW_READY, 'dec'), (7, LOW_HIT, 'acc'), (10, full(LOW_HIT, gripR=(-2.9, -2.45, 2.7)), 'dec'),
        (15, full(LOW_HIT)),
    ], base=CROUCH, back=N - 2, keep_trans=True)

    # ═════════ Smash haut : le bâton jaillit au ciel (charge 11, frappe 14) ═════════
    US_CHARGE = dict(yaw=-16.0, hip=(0.0, -2.2, -0.25), hrot=(10, -10, 0), waist=(14, -12, 0), bust=(10, -16, 0),
                     head=(-24, 36, 0), footL=(0.85, 0.0, 0.95), footR=(-0.9, 0.0, -0.8), footLrot=(0, 18, 0),
                     footRrot=(0, -30, 0), kneeL=(0.6, 0.0, 0.9), kneeR=(-0.75, 0.0, 0.7),
                     gripR=(-3.8, -2.3, 0.9), elbowR=(-0.8, -0.35, -0.5), staff=(-0.3, 0.1, 0.95), slide=1.4,
                     two=1.0, span=2.0, elbowL=(0.65, -0.75, 0.1), fist=1.0)
    US_HIT = dict(US_CHARGE, yaw=-10.0, hip=(0.0, 0.0, 0.1), hrot=(-6, -4, 0), waist=(-8, -4, 0), bust=(-12, -6, 0),
                  head=(-22, 16, -8), footL=(0.6, 0.0, 0.8), footR=(-0.65, 0.0, -0.7), gripR=(-4.4, 3.0, 0.4),
                  elbowR=(-0.95, -0.25, -0.15), staff=(-0.22, 0.97, 0.06), slide=0.3, two=0.0,
                  gripL=(4.4, -0.2, 0.9), elbowL=(0.5, -0.8, -0.35))
    N = length('c04attackhi4')
    us = attack('c04attackhi4', [
        (5, full(US_CHARGE, hip=(0.0, -1.4, -0.1), two=0.7)), (11, US_CHARGE, 'dec'),
        (14, US_HIT, 'acc'),
        (18, full(US_HIT, gripR=(-4.4, 3.2, 0.35), hip=(0.0, 0.1, 0.1), bust=(-14, -6, 0)), 'dec'),
        (30, full(US_HIT)),
        (42, full(IDLE, hip=(0.0, -1.1, -0.15), gripR=(-4.2, 0.3, 1.2), staff=(-0.35, 0.92, 0.15))),
    ], back=56)
    emit('c04attackhi4charge', length('c04attackhi4charge'), tremble(us(11)), seed=(us, 11))

    # ═════════ Smash bas : le bâton s'abat à plat et fait jaillir deux geysers (charge 6, frappe 13) ═════════
    DS_CHARGE = dict(yaw=-48.0, hip=(0.0, -1.6, -0.35), hrot=(6, -12, 0), waist=(6, -16, 0), bust=(0, -18, 0),
                     head=(-18, 62, 0), footL=(0.9, 0.0, 0.9), footR=(-0.95, 0.0, -0.8), footLrot=(0, 22, 0),
                     footRrot=(0, -30, 0), kneeL=(0.6, 0.0, 0.9), kneeR=(-0.75, 0.0, 0.7),
                     gripR=(-4.1, 0.6, -0.6), elbowR=(-0.9, -0.35, -0.25), staff=(-0.35, 0.8, -0.48), slide=1.8,
                     two=1.0, span=-2.0, elbowL=(0.35, -0.9, 0.3), fist=1.0)
    DS_HIT = dict(DS_CHARGE, yaw=-4.0, hip=(0.0, -3.1, 0.2), hrot=(16, 0, 0), waist=(18, 0, 0), bust=(12, -4, 0),
                  head=(-38, 8, 0), footL=(1.25, 0.0, 1.35), footR=(-1.3, 0.0, -1.2), gripR=(-2.6, -2.5, 1.9),
                  elbowR=(-0.95, -0.2, -0.2), staff=(0.02, -0.08, 1.0), slide=3.0, span=2.0, ground=1.0,
                  elbowL=(0.75, -0.6, 0.0))
    N = length('c04attacklw4')
    ds = attack('c04attacklw4', [
        (6, DS_CHARGE, 'dec'),
        (9, full(DS_CHARGE, hip=(0.0, -0.2, -0.2), yaw=-30.0, gripR=(-4.1, 2.4, 0.4), staff=(-0.35, 0.9, 0.1)), 'dec'),
        (13, DS_HIT, 'acc'),
        (16, full(DS_HIT, hip=(0.0, -3.3, 0.25), bust=(16, -4, 0)), 'dec'),
        (19, full(DS_HIT, hip=(0.0, -2.9, 0.2), bust=(10, -4, 0))),
        (34, full(DS_HIT)),
        (48, full(IDLE, hip=(0.0, -1.2, -0.15), gripR=(-3.7, -1.9, 1.7), staff=(-0.3, 0.7, 0.65))),
    ], back=58)
    emit('c04attacklw4charge', length('c04attacklw4charge'), tremble(ds(6)), seed=(ds, 6))

    # ═════════ Aérien haut : coup de masque vers le ciel (frappe 8-11) ═════════
    attack('c05attackairhi', [
        (4, full(AIR, hip=(0.0, -0.5, 0.2), hrot=(14, 0, 0), waist=(16, 0, 0), bust=(14, 0, 0), head=(20, 6, 0),
                 footL=(0.3, 1.5, 0.9), footR=(-0.35, 1.2, -0.2), gripR=(-3.8, -1.9, 1.8), gripL=(3.8, -2.0, 1.7),
                 staff=(-0.6, 0.6, 0.5), fist=1.0), 'dec'),
        (8, full(AIR, yaw=-8.0, lift=0.9, hip=(0.0, 0.35, 0.0), hrot=(-8, 0, 0), waist=(-10, 0, 0), bust=(-12, 0, 0),
                 head=(-24, 0, 0), footL=(0.25, 0.2, -0.3), footR=(-0.25, 0.1, -0.6), footLrot=(55, 6, 0),
                 footRrot=(60, -6, 0), gripR=(-3.7, -2.8, -0.9), gripL=(3.7, -2.8, -0.9), staff=(-0.65, 0.45, -0.6),
                 fist=1.0), 'acc'),
        (11, {'lift': 1.15, 'head': (-34, 0, 0), 'bust': (-16, 0, 0)}, 'dec'),
        (20, {'lift': 0.5, 'head': (-16, 10, 0), 'bust': (-6, 0, 0)}),
    ], base=AIR, back=40)

    # ═════════ Aérien arrière : décharge du bâton derrière lui (frappe 10) ═════════
    BAIR = dict(AIR, yaw=-38.0, hrot=(10, -14, 0), waist=(8, -18, 0), bust=(4, -26, 0), head=(-18, -8, 0),
                footL=(0.3, 0.9, 0.9), footR=(-0.35, 0.8, 0.4), gripR=(-4.2, 0.3, -1.9), elbowR=(-0.95, -0.25, 0.1),
                staff=(-0.1, 0.32, -0.94), slide=0.4, gripL=(3.4, -1.0, 2.2), fist=1.0)
    attack('c05attackairb', [
        (6, full(BAIR, yaw=-16.0, bust=(6, 4, 0), gripR=(-3.5, -0.9, 1.9), staff=(-0.5, 0.82, 0.25),
                 head=(-12, 20, 0)), 'dec'),
        (10, BAIR, 'acc'),
        (13, full(BAIR, hip=(0.0, -0.2, 0.9), gripR=(-4.1, 0.1, -1.2), staff=(-0.1, 0.44, -0.9),
                  bust=(10, -22, 0)), 'dec'),
        (22, full(BAIR, hip=(0.0, -0.2, 0.4))),
    ], base=AIR, back=40)

    # ═════════ Aérien bas : le bâton plonge sous ses pieds (frappe 15) ═════════
    DAIR_UP = dict(AIR, yaw=-14.0, lift=0.5, hip=(0.0, 0.1, -0.3), hrot=(-8, 0, 0), waist=(-8, 0, 0), bust=(-10, 0, 0),
                   head=(-14, 14, 0), footL=(0.5, 2.2, 0.6), footR=(-0.55, 1.9, -0.3), gripR=(-3.9, 2.0, 0.6),
                   elbowR=(-0.95, -0.25, -0.1), staff=(-0.35, 0.88, 0.3), slide=1.2, two=1.0, span=-2.0,
                   elbowL=(0.4, -0.9, 0.2), fist=1.0)
    DAIR_HIT = dict(DAIR_UP, yaw=-6.0, lift=0.0, hip=(0.0, 0.2, -0.45), hrot=(18, 0, 0), waist=(14, 0, 0),
                    bust=(10, 0, 0), head=(-26, 6, 0), footL=(0.9, 2.3, -0.9), footR=(-0.9, 1.9, -1.2),
                    footLrot=(40, 12, 0), footRrot=(46, -12, 0), gripR=(-2.7, -2.4, 2.7), staff=(0.06, -0.93, 0.36),
                    span=-1.8, slide=1.8, elbowR=(-0.95, -0.2, -0.2), elbowL=(0.85, -0.5, 0.0))
    attack('c05attackairlw', [
        (8, DAIR_UP, 'dec'),
        (12, full(DAIR_UP, gripR=(-3.4, 0.4, 2.4), staff=(-0.3, 0.1, 0.95)), 'acc'),
        (15, DAIR_HIT, 'lin'),
        (18, full(DAIR_HIT, gripR=(-2.7, -2.65, 2.6)), 'dec'),
        (27, full(DAIR_HIT)),
        (40, full(AIR, gripR=(-3.8, -1.6, 1.9), staff=(-0.5, 0.2, 0.84))),
    ], base=AIR, back=52)

    # ═════════ Saisies : la main gauche agrippe, le vaudou tient la cible en l'air ═════════
    HOLD = dict(IDLE, yaw=-30.0, hip=(0.0, -0.8, 0.0), hrot=(4, 6, 0), waist=(2, 8, 0), bust=(-4, 12, 0),
                head=(-22, -4, 0), footL=(0.6, 0.0, 1.0), footR=(-0.65, 0.0, -0.8), gripR=(-4.3, -0.4, 0.9),
                elbowR=(-0.8, -0.5, -0.3), staff=(-0.3, 0.9, 0.32), gripL=(2.4, 0.2, 3.6), elbowL=(0.8, -0.6, 0.0),
                fist=0.15)
    REACH = dict(HOLD, yaw=-10.0, hip=(0.0, -1.25, 0.9), hrot=(12, 8, 0), waist=(10, 12, 0), bust=(8, 18, 0),
                 head=(-28, -16, 0), footL=(0.55, 0.0, 2.0), gripL=(1.4, -0.9, 4.4), fist=0.0,
                 gripR=(-4.4, -1.0, -0.8), staff=(-0.45, 0.82, -0.35))
    GRAB = dict(REACH, fist=1.0, gripL=(1.5, -0.7, 4.2))
    COIL = dict(IDLE, yaw=-38.0, hip=(0.0, -0.9, -0.5), bust=(2, -14, 0), head=(-14, 42, 0), gripL=(3.8, -1.2, 0.0),
                fist=0.0, gripR=(-4.0, -1.2, 0.8))
    attack('e00catch', [
        (4, COIL, 'dec'), (6, REACH, 'acc'), (9, GRAB, 'dec'), (18, full(GRAB, hip=(0.0, -1.15, 0.75))),
    ], back=38)
    attack('e00catchdash', [
        (5, full(COIL, hip=(0.0, -1.4, 0.0), hrot=(14, 0, 0))),
        (9, full(REACH, hip=(0.0, -1.7, 1.1)), 'acc'), (13, full(GRAB, hip=(0.0, -1.85, 1.1)), 'dec'),
        (24, full(GRAB, hip=(0.0, -1.5, 0.8))),
    ], back=42, keep_trans=True)
    # pivot : volte-face, la prise se referme dans le dos et il reste retourné (le jeu change alors son orientation)
    BACK = dict(IDLE, yaw=150.0)
    reach_b = full(REACH, yaw=170.0, hip=(0.0, -1.25, -0.9), footL=(-0.55, 0.0, -2.0), footR=(0.65, 0.0, 0.8),
                   footLrot=(0, 184, 0), footRrot=(0, 156, 0), kneeL=(-0.4, 0.0, -1.0), kneeR=(0.4, 0.0, -1.0),
                   elbowL=(-0.8, -0.6, 0.0), elbowR=(0.8, -0.5, 0.3), staff=(-0.2, 0.75, 0.62))
    back_pose = full(BACK, footL=(-0.45, 0.0, -0.55), footR=(0.45, 0.0, 0.5), footLrot=(0, 194, 0),
                     footRrot=(0, 164, 0), kneeL=(-0.35, 0.0, -1.0), kneeR=(0.4, 0.0, -1.0),
                     elbowL=(-0.45, -0.1, 0.9), elbowR=(0.45, -0.1, 0.9), staff=(-0.15, 0.85, -0.5))
    attack('e00catchturn', [
        (5, full(COIL, yaw=60.0, hip=(0.0, -1.2, 0.0), footL=(-0.3, 0.8, -0.6), footR=(0.3, 0.0, 0.6),
                 footLrot=(20, 110, 0), footRrot=(0, 70, 0), kneeL=(0.8, 0.0, -0.4), kneeR=(0.6, 0.0, 0.7),
                 elbowL=(0.2, -0.6, -0.8), elbowR=(-0.2, -0.4, 0.8), staff=(0.1, 0.95, 0.3))),
        (10, reach_b, 'acc'), (14, full(reach_b, fist=1.0), 'dec'), (26, full(reach_b, fist=1.0)),
    ], end=back_pose, back=44)
    N = length('e00catchpull')
    emit('e00catchpull', N, seq(GRAB, N, [(6, full(HOLD, gripL=(2.3, 0.5, 3.2), fist=0.1), 'dec')], HOLD),
         align_end=(2, N))

    def catch_wait(f):
        s = math.sin(TAU * f / 60)
        s2 = math.sin(TAU * f / 20)
        p = dict(HOLD)
        p['hip'] = (0.0, -0.8 + 0.18 * s, 0.0)
        p['gripL'] = (2.4 + 0.2 * s2, 0.2 + 0.25 * s, 3.6)
        p['gripR'] = (-4.3, -0.4 + 0.3 * s2, 0.9)
        p['staff'] = (-0.3 + 0.12 * math.sin(TAU * f / 30), 0.9, 0.32)
        p['head'] = (-22 + 2 * s, -4, 3 * s)
        return p

    emit('e00catchwait', length('e00catchwait'), catch_wait)
    N = length('e00catchattack')              # coup de masque sur la cible tenue
    emit('e00catchattack', N, seq(HOLD, N, [
        (2, full(HOLD, bust=(14, 14, 0), waist=(12, 10, 0), head=(-4, -6, 0), hip=(0.0, -1.0, 0.45),
                 gripR=(-4.2, 0.6, 0.6), staff=(-0.35, 0.93, 0.0)), 'acc'),
        (6, full(HOLD, bust=(-10, 10, 0), head=(-26, -4, 0)), 'dec'),
    ]), align_end=(6, N))

    # ═════════ Projections : le bâton désigne la victime et la mène où il veut ═════════
    def throw_path(name):
        _, _, nodes = read_nodes(name)
        out = []
        for v in nodes['Throw']:
            out.append(tf_mat(v).translation.copy())
        return out

    def throw(name, release, finish, yaw_keys=()):
        """`release` = frame du lâcher ; `finish` = pose d'accompagnement tenue après le lâcher."""
        N = length(name)
        path = throw_path(name)
        hand = V((-3.6, 7.0, 1.0))                    # hauteur de la main qui tient le bâton

        def aim(f):
            acc = V((0.0, 0.0, 0.0))
            for k in range(-4, 5):
                i = min(max(f + k, 0), release)
                d = path[min(i, len(path) - 1)] - hand
                acc += d.normalized() * (5 - abs(k))
            d = acc.normalized()
            if d.x > -0.22:                           # le manche reste sur le côté du masque
                d.x = -0.22
            return d.normalized()

        keys = Keys(HOLD, [(0, {}), (release, dict(HOLD)), (min(release + 5, N), dict(finish), 'dec'),
                           (min(release + 18, N - 10), dict(finish)), (N - 3, dict(IDLE)), (N, dict(IDLE))])
        turn = Keys(HOLD, [(0, {})] + [(f, {'yaw': y}) for f, y in yaw_keys] + [(N, {'yaw': IDLE['yaw']})]) \
            if yaw_keys else None

        def fn(f):
            p = keys(f)
            k = smooth01(f / 6) * smooth01((release + 5 - f) / 6)
            if k > 0:
                d = aim(f)
                lift = max(min(d.y, 1.0), -0.5)
                q = dict(p)
                q['staff'] = (d.x, d.y, d.z)
                q['gripR'] = (-4.3, -0.9 + 2.6 * lift, 0.3 + 1.7 * d.z)
                q['gripL'] = (3.2 + 0.6 * max(lift, 0), -1.0 + 2.2 * lift, 1.0 + 2.2 * d.z)
                q['bust'] = (-14 * lift + 4, 6, 0)
                q['head'] = (-24 * max(lift, 0) - 8, 6, 0)
                q['hip'] = (0.0, -1.1 + 0.6 * lift, 0.35 * d.z)
                p = mix(p, q, k)
            if turn:
                p['yaw'] = turn(f)['yaw']
            return p

        emit(name, N, fn, keep=('Throw', 'Rot'), keep_trans=True, align_end=(release + 6, N))

    throw('e01throwf', 26, full(HOLD, yaw=-6.0, hip=(0.0, -1.3, 0.8), bust=(12, 14, 0), head=(-26, -10, 0),
                                footL=(0.55, 0.0, 1.8), gripR=(-3.0, -1.4, 2.8), staff=(0.0, 0.3, 0.95),
                                gripL=(3.8, -1.2, -0.8), fist=1.0))
    throw('e01throwb', 17, full(HOLD, yaw=-42.0, hip=(0.0, -1.1, -0.5), bust=(0, -24, 0), head=(-18, 20, 0),
                                gripR=(-4.2, 0.5, -1.7), staff=(-0.2, 0.55, -0.8), gripL=(3.2, -1.4, 2.0),
                                fist=1.0), yaw_keys=((8, -4.0), (17, -48.0), (34, -42.0)))
    throw('e01throwhi', 30, full(HOLD, yaw=-14.0, hip=(0.0, -0.1, 0.0), waist=(-8, 0, 0), bust=(-12, 0, 0),
                                 head=(-30, 12, -6), gripR=(-4.4, 3.0, 0.4), elbowR=(-0.95, -0.25, -0.15),
                                 staff=(-0.22, 0.97, 0.06), gripL=(4.4, 1.8, 0.8), fist=1.0))
    throw('e01throwlw', 20, full(HOLD, yaw=-14.0, hip=(0.0, -2.4, 0.3), waist=(16, 0, 0), bust=(14, 0, 0),
                                 head=(-34, 12, 0), footL=(0.9, 0.0, 1.3), footR=(-0.95, 0.0, -0.9),
                                 gripR=(-3.6, -2.4, 2.2), staff=(-0.15, -0.25, 0.95), ground=1.0,
                                 gripL=(3.4, -2.2, 2.2), fist=0.0))


def STAND_POSE(idle):
    return dict(idle, footL=(0.55, 0.0, 1.0), footR=(-0.55, 0.0, -0.6))
