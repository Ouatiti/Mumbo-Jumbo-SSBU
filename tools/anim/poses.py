"""Moteur de poses « propre » pour Mumbo sur le squelette de Ness (espace jeu : Y haut, avant +Z, gauche +X).

Une pose est un dictionnaire de canaux (voir DEFAULT). Le moteur construit le squelette ainsi :
  - torse : hanches -> taille -> buste -> cou -> tête, rotations cumulées (pitch, yaw, roll en degrés) ;
  - bras et jambes : IK 2 os à plan de pliage explicite (coude / genou = vraie charnière, aucune vrille parasite) ;
  - bâton : l'avant-bras prend une partie de la torsion, le poignet est limité, l'os HaveR fait le reste ;
  - main gauche posée sur le bâton (two) à `slide` unités de la main droite.
Les animations sont soit des poses clés (Keys), soit des fonctions f -> pose (boucles).
"""
import sys, os, math
sys.path.insert(0, r"C:\Users\sofia\AppData\Roaming\Blender Foundation\Blender\5.1\scripts\addons\smash-ultimate-blender\dependencies\ssbh_data_py\win")
import ssbh_data_py as S
from mathutils import Matrix, Vector, Quaternion

NESS_SK = r"E:\Emulateurs\ness_model\fighter\ness\model\body\c00\model.nusktb"
NESS_MO = r"E:\Emulateurs\ness_model\fighter\ness\motion\body\c00"
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
STAFF_TIP, STAFF_BUTT = 10.0, 1.4      # longueurs du bâton de part et d'autre de l'os HaveR
HEAD_BOX = ((-3.2, 3.2), (-1.4, 9.8), (-1.5, 3.9))   # masque + coiffe, relatif à l'os Head
AXIS_R = Vector((0.51, -0.48, -0.04))  # au repos : manche par rapport à l'os HaveR / paume droite (maillage)
AXIS_L = Vector((-0.45, -0.5, 0.0))    # idem paume gauche (miroir) : le manche passe entre les doigts
SHAFT_TILT = -0.08                     # le manche descend un peu vers le crâne par rapport à l'os


def mat(m):
    return Matrix([list(r) for r in m]).transposed()


def tf_mat(v):
    q = Quaternion((v.rotation[3], v.rotation[0], v.rotation[1], v.rotation[2]))
    return Matrix.Translation(Vector(v.translation)) @ q.to_matrix().to_4x4()


_sk = S.skel_data.read_skel(NESS_SK)
NAMES = [b.name for b in _sk.bones]
PARENT = {b.name: (_sk.bones[b.parent_index].name if b.parent_index is not None else None) for b in _sk.bones}
REST_L = {b.name: mat(b.transform) for b in _sk.bones}
REST_W = {b.name: mat(_sk.calculate_world_transform(b)) for b in _sk.bones}
REST_P = {n: m.translation.copy() for n, m in REST_W.items()}
REST_R = {n: m.to_quaternion() for n, m in REST_W.items()}


def read_nodes(name):
    a = S.anim_data.read_anim(os.path.join(NESS_MO, name + '.nuanmb'))
    g = next(g for g in a.groups if g.group_type.name == 'Transform')
    return a, g, {nd.name: nd.tracks[0].values for nd in g.nodes}


def length(name):
    return int(read_nodes(name)[0].final_frame_index)


def _grip_fingers():
    """doigts fermés (prise à deux mains du smash batte de Ness) et doigts détendus (attente)."""
    closed = read_nodes('c03attacks4s')[2]
    relaxed = read_nodes('a00wait1')[2]
    out = {}
    for n in NAMES:
        if n.startswith('Finger') and n in closed:
            out[n] = (tf_mat(relaxed[n][0]), tf_mat(closed[n][min(18, len(closed[n]) - 1)]))
    return out


FINGERS = _grip_fingers()

# ───────────────────────── canaux ─────────────────────────
DEFAULT = dict(
    yaw=0.0,                      # orientation générale (deg, + = vers sa gauche)
    lift=0.0,                     # décalage vertical de tout le personnage (sauts, lévitation)
    hip=(0.0, 0.0, 0.0),          # décalage des hanches
    hrot=(0.0, 0.0, 0.0),         # hanches (pitch + = penché en avant, yaw, roll)
    waist=(0.0, 0.0, 0.0), bust=(0.0, 0.0, 0.0), head=(0.0, 0.0, 0.0),
    footL=(0.0, 0.0, 0.0), footR=(0.0, 0.0, 0.0),          # décalage par rapport au pied au repos
    footLrot=(0.0, 0.0, 0.0), footRrot=(0.0, 0.0, 0.0),    # (pitch + = pointe vers le bas, yaw, roll)
    kneeL=(0.2, 0.0, 1.0), kneeR=(-0.2, 0.0, 1.0),         # direction des genoux
    gripR=(-3.0, -2.4, 1.4), gripL=(3.0, -2.6, 0.8),       # paumes, relatives au haut du buste
    elbowR=(-0.45, -0.1, -0.9), elbowL=(0.45, -0.1, -0.9),   # direction des coudes
    staff=(0.0, 1.0, 0.12),       # direction du bâton (vers le crâne)
    hold=1.0,                     # 1 = la main droite oriente le bâton
    slide=0.0,                    # coulisse du bâton dans la main (+ = main plus près du crâne)
    two=0.0, span=1.8,            # main gauche sur le bâton, à `span` unités de la droite
    fist=0.0,                     # fermeture de la main gauche
    float_=0.0, floatpos=(0.0, 5.0, 2.0),   # bâton détaché : centre du bâton (espace personnage)
    ground=0.0,                   # 1 = la tête du bâton vient toucher le sol (hauteur 0.4)
    plant=0.0, butty=0.2,         # 1 = le talon du bâton est à la hauteur `butty` (règle la coulisse)
)


def V(t):
    return Vector(t)


def euler(r):
    p, y, ro = (math.radians(a) for a in r)
    return Quaternion(Y, y) @ Quaternion(X, p) @ Quaternion(Z, ro)


def frame_q(d, n):
    """base orthonormée (direction du segment, normale de la charnière)."""
    d = d.normalized()
    n = (n - d * n.dot(d)).normalized()
    return Matrix((d, n, d.cross(n))).transposed()


def solve_limb(root, target, pole, a, b, u0, v0, pole0):
    """IK 2 os. Renvoie (delta rotation segment haut, delta segment bas, position milieu, extrémité)."""
    v = target - root
    d = min(max(v.length, abs(a - b) + 0.05), (a + b) * 0.995)
    u = v.normalized() if v.length > 1e-5 else u0.copy()
    end = root + u * d
    x = (a * a - b * b + d * d) / (2 * d)
    h = math.sqrt(max(a * a - x * x, 0.0))
    pl = pole - u * pole.dot(u)
    if pl.length < 1e-4:
        pl = pole0 - u * pole0.dot(u)
    pl.normalize()
    mid = root + u * x + pl * h
    n0 = u0.cross(pole0).normalized()
    n1 = u.cross(pl).normalized()
    q1 = (frame_q(mid - root, n1) @ frame_q(u0, n0).transposed()).to_quaternion()
    q2 = (frame_q(end - mid, n1) @ frame_q(v0, n0).transposed()).to_quaternion()
    return q1, q2, mid, end


def clamp_rot(q, deg):
    if q.w < 0:
        q = -q
    a = q.angle
    lim = math.radians(deg)
    return q if a <= lim else Quaternion().slerp(q, lim / a)


class Builder:
    def __init__(self):
        self.stats = {'reach': 0.0, 'head': 0, 'where': ''}
        self.frame = 0
        self.staff_prev = None          # (direction, orientation) : transport parallèle, aucun retournement

    def build(self, p, trans_local=None):
        """pose (canaux) -> dictionnaire des matrices locales."""
        W, L = {}, {}
        Yq = Quaternion(Y, math.radians(p['yaw']))
        lift = Vector((0, p['lift'], 0))

        def put(n, rot, pos=None):
            par = PARENT[n]
            if pos is None:
                pos = (W[par] @ REST_L[n]).translation
            W[n] = Matrix.Translation(pos) @ rot.to_matrix().to_4x4()
            L[n] = W[par].inverted() @ W[n] if par else W[n]

        def delta(n, d, pos=None):
            put(n, d @ REST_R[n], pos)

        def rest(n, loc=None):
            par = PARENT[n]
            L[n] = loc if loc is not None else REST_L[n]
            W[n] = W[par] @ L[n] if par else L[n]

        rest('Trans', trans_local)
        rest('Rot')
        qh = Yq @ euler(p['hrot'])
        delta('Hip', qh, W['Trans'] @ (Yq @ (REST_P['Hip'] + V(p['hip'])) + lift))
        qw = qh @ euler(p['waist']); delta('Waist', qw)
        qb = qw @ euler(p['bust']); delta('Bust', qb)
        qhe = euler(p['head'])
        delta('Neck', qb @ Quaternion().slerp(qhe, 0.4))
        delta('Head', qb @ qhe)
        rest('Hat')
        delta('ClavicleC', qb)
        anchor = W['ClavicleC'].translation.copy()
        space = W['Trans'].to_3x3()

        def world_dir(t):
            return (Yq @ V(t)).normalized()

        # ── bras ──
        def arm(side, palm, pole, staff_dir=None, orient=0.0, line=None, off_w=0.0):
            s = 1.0 if side == 'L' else -1.0
            cl, sh, fo, ha = ('Clavicle' + side, 'Shoulder' + side, 'Arm' + side, 'Hand' + side)
            # haussement d'épaule quand la main monte
            rel = (Yq.inverted() @ (palm - anchor))
            up = max(0.0, min(1.0, (rel.y + 0.5) / 3.5))
            delta(cl, qb @ Quaternion(Z, s * math.radians(22.0) * up))
            put(sh, REST_R[sh])
            root = W[sh].translation.copy()
            a = (REST_P[fo] - REST_P[sh]).length
            b = (REST_P[ha] - REST_P[fo]).length
            if line is not None:          # main hors de portée : elle coulisse sur le manche
                o, d, w = line
                rmax = (a + b) * 0.99 + 0.9
                if (palm - root).length > rmax:
                    t, tp = (palm - o).dot(d), (root - o).dot(d)
                    half = math.sqrt(max(rmax * rmax - (o + d * tp - root).length_squared, 0.0))
                    palm = palm + d * ((min(max(t, tp - half), tp + half) - t) * w)
            grip_off = Vector((s * 1.0, 0, 0))          # paume = poignet + 1 le long de la main
            u0 = (REST_P[fo] - REST_P[sh]).normalized()
            v0 = (REST_P[ha] - REST_P[fo]).normalized()
            dir_hand = (palm - root).normalized()
            qf = None
            qhand = qb
            for _ in range(14):
                goal = palm - (qhand @ AXIS_L) * off_w           # prise : l'axe du manche tombe dans la paume
                wrist = goal - dir_hand * 1.0
                q1, q2, mid, end = solve_limb(root, wrist, pole, a, b, u0, v0, Vector((0, 0, -1)))
                qf, qhand = q2, q2
                if staff_dir is not None and orient > 0:
                    axis = (end - mid).normalized()
                    cur = (q2 @ Z).normalized()
                    # torsion de l'avant-bras : fonction continue (prise inversée au-delà de 90°)
                    cp = cur - axis * cur.dot(axis)
                    sp = staff_dir - axis * staff_dir.dot(axis)
                    tang = 0.0
                    if cp.length > 1e-4 and sp.length > 1e-4:
                        ang = math.atan2(axis.dot(cp.cross(sp)), cp.dot(sp))
                        ang = math.copysign(min(abs(ang), math.pi - abs(ang)), ang)
                        tang = ang * smooth01(cp.length * sp.length * 1.4) * orient
                    qf = Quaternion(axis, 0.5 * tang) @ q2
                    qt = Quaternion(axis, tang) @ q2
                    # flexion du poignet, limitée à 60°
                    cur = (qt @ Z).normalized()
                    ax = cur.cross(staff_dir)
                    qhand = qt
                    if ax.length > 1e-5:
                        ang = cur.angle(staff_dir)
                        ang = min(min(ang, math.pi - ang), math.radians(60)) * smooth01(ax.length * 2) * orient
                        qhand = Quaternion(ax.normalized(), ang) @ qt
                new_dir = (qhand @ grip_off).normalized()
                dir_hand = (dir_hand + new_dir).normalized()
            delta(sh, q1)
            delta(fo, qf)
            delta(ha, qhand)
            hp = (W[ha] @ REST_L['Have' + side]).translation
            err = (hp - (palm - (qhand @ AXIS_L) * off_w)).length
            if err > self.stats['reach']:
                self.stats['reach'] = err
                self.stats['where'] = f'bras{side}@{self.frame}'
            return hp, qhand

        sdir = world_dir(p['staff'])
        palmR = anchor + space @ (Yq @ V(p['gripR']))
        if p['ground'] > 0:
            gy = min(max((0.4 - palmR.y) / STAFF_TIP, -0.98), 0.98)
            h = Vector((sdir.x, 0, sdir.z)).normalized() * math.sqrt(1 - gy * gy)
            sdir = sdir.lerp(Vector((h.x, gy, h.z)), p['ground']).normalized()
        gripR, qhandR = arm('R', palmR, world_dir(p['elbowR']), sdir, p['hold'] * (1 - p['float_']))
        # bâton
        if self.staff_prev is None:
            up = Yq @ Quaternion(X, math.radians(-90))        # bâton vertical, crâne face à l'avant
            qstaff = Y.rotation_difference(sdir) @ up
        else:
            qstaff = self.staff_prev[0].rotation_difference(sdir) @ self.staff_prev[1]
        self.staff_prev = (sdir.copy(), qstaff.copy())
        qstaff = Quaternion(sdir, p.get('roll', 0.0)) @ qstaff   # vrille ajoutée (raccord), hors transport
        # le manche passe dans la paume droite, même quand le poignet ne suit pas le bâton
        gripS = gripR + (qhandR @ AXIS_R - qstaff @ AXIS_R) * (1 - p['float_'])
        slide = p['slide']
        if p['plant'] > 0:
            s_butt = (gripS.y - p['butty']) / max(sdir.y, 0.3) - STAFF_BUTT
            slide += (s_butt - slide) * p['plant']
        pos = gripS - sdir * slide
        if p['float_'] > 0:
            center = Yq @ V(p['floatpos']) + lift + W['Trans'].translation
            pos = pos.lerp(center - sdir * (0.5 * (STAFF_TIP - STAFF_BUTT)), p['float_'])
        delta('HaveR', qstaff, pos)
        rest('Bat')
        # main gauche
        palmL = anchor + space @ (Yq @ V(p['gripL']))
        if p['two'] > 0:
            axis = qstaff @ (AXIS_R + Vector((0.0, SHAFT_TILT * p['span'], 0.0)))
            palmL = palmL.lerp(pos + sdir * (slide + p['span']) + axis, p['two'])
        gripL, qhandL = arm('L', palmL, world_dir(p['elbowL']), sdir if p['two'] > 0 else None, p['two'],
                            (pos + axis, sdir, p['two']) if p['two'] > 0 else None,
                            p['two'])
        rest('HaveL'); rest('BatL')
        # ── jambes ──
        delta('LegC', qh)
        for side, s in (('L', 1.0), ('R', -1.0)):
            leg, knee, foot, toe = ('Leg' + side, 'Knee' + side, 'Foot' + side, 'Toe' + side)
            put(leg, REST_R[leg])
            root = W[leg].translation.copy()
            a = (REST_P[knee] - REST_P[leg]).length
            b = (REST_P[foot] - REST_P[knee]).length
            tgt = W['Trans'] @ (Yq @ (REST_P[foot] + V(p['foot' + side])) + lift)
            q1, q2, mid, end = solve_limb(root, tgt, world_dir(p['knee' + side]), a, b,
                                          (REST_P[knee] - REST_P[leg]).normalized(),
                                          (REST_P[foot] - REST_P[knee]).normalized(), Vector((0, 0, 1)))
            if (end - tgt).length > self.stats['reach']:
                self.stats['reach'] = (end - tgt).length
                self.stats['where'] = f'jambe{side}@{self.frame}'
            delta(leg, q1); delta(knee, q2)
            qft = Yq @ euler(p['foot' + side + 'rot'])
            delta(foot, qft)
            delta(toe, qft)
        # ── reste : doigts, os annexes ──
        for n in NAMES:
            if n in L:
                continue
            if n in FINGERS:
                w = 1.0 if n.startswith('FingerR') else max(p['fist'], p['two'])
                if n.startswith('FingerR'):
                    w = 1.0 - 0.7 * p['float_']
                a, b = FINGERS[n]
                q = a.to_quaternion().slerp(b.to_quaternion(), w)
                rest(n, Matrix.Translation(REST_L[n].translation) @ q.to_matrix().to_4x4())
            else:
                rest(n)
        # contrôle : le bâton traverse-t-il le masque ?
        inv = W['Head'].to_quaternion() @ REST_R['Head'].inverted()
        hpos = W['Head'].translation
        for k in range(0, 23):
            pt = pos + sdir * (-STAFF_BUTT + (STAFF_TIP + STAFF_BUTT) * k / 22)
            r = inv.inverted() @ (pt - hpos)
            if all(lo + 0.5 < r[i] < hi - 0.5 for i, (lo, hi) in enumerate(HEAD_BOX)):
                self.stats['head'] += 1
                break
        return L


# ───────────────────────── interpolation ─────────────────────────
def as_list(v):
    return list(v) if isinstance(v, (tuple, list, Vector)) else [float(v)]


class Keys:
    """Poses clés : [(frame, {canaux}, mode)] ; mode = façon d'ARRIVER sur la clé :
    'auto' (courbe lisse), 'acc' (accélère : frappe), 'dec' (freine : anticipation), 'lin'."""

    def __init__(self, base, keys, loop_len=None, lag=None):
        self.base = dict(base)
        self.tracks = {}
        self.loop_len = loop_len
        self.lag = lag or {}
        for key in keys:
            f, ch = key[0], key[1]
            mode = key[2] if len(key) > 2 else 'auto'
            for c, v in ch.items():
                self.tracks.setdefault(c, []).append((f, as_list(v), mode))
        for c, tr in self.tracks.items():          # canal introduit plus tard : part de la pose de base
            if tr[0][0] > keys[0][0]:
                tr.insert(0, (keys[0][0], as_list(self.base[c]), 'auto'))

    def sample(self, c, t):
        tr = self.tracks[c]
        if t <= tr[0][0]:
            return tr[0][1]
        if t >= tr[-1][0]:
            return tr[-1][1]
        i = next(i for i in range(len(tr) - 1) if tr[i][0] <= t < tr[i + 1][0])
        f0, a, _ = tr[i]
        f1, b, mode = tr[i + 1]
        h = f1 - f0
        u = (t - f0) / h
        if mode == 'acc':
            w = u ** 2.2
        elif mode == 'dec':
            w = 1 - (1 - u) ** 2.2
        elif mode == 'lin':
            w = u
        else:
            def tan(j, k):
                if j == 0 or j == len(tr) - 1:
                    return 0.0
                d0 = (tr[j][1][k] - tr[j - 1][1][k]) / (tr[j][0] - tr[j - 1][0])
                d1 = (tr[j + 1][1][k] - tr[j][1][k]) / (tr[j + 1][0] - tr[j][0])
                if d0 * d1 <= 0:                       # extremum : pas de dépassement
                    return 0.0
                m = 0.5 * (d0 + d1)
                lim = 3 * min(abs(d0), abs(d1))        # courbe monotone
                return max(-lim, min(lim, m))
            u2, u3 = u * u, u * u * u
            return [(2 * u3 - 3 * u2 + 1) * a[k] + (u3 - 2 * u2 + u) * h * tan(i, k)
                    + (-2 * u3 + 3 * u2) * b[k] + (u3 - u2) * h * tan(i + 1, k) for k in range(len(a))]
        return [a[k] + (b[k] - a[k]) * w for k in range(len(a))]

    def __call__(self, f):
        p = dict(self.base)
        for c in self.tracks:
            t = f - self.lag.get(c, 0.0)
            v = self.sample(c, t)
            p[c] = v[0] if len(v) == 1 else tuple(v)
        return p


def pose(**kw):
    p = dict(DEFAULT)
    for k, v in kw.items():
        if k not in p:
            raise KeyError(k)
        p[k] = v
    return p


def mix(a, b, w):
    out = {}
    for k in a:
        if isinstance(a[k], (tuple, list)):
            out[k] = tuple(x + (y - x) * w for x, y in zip(a[k], b[k]))
        else:
            out[k] = a[k] + (b[k] - a[k]) * w
    return out


def smooth01(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ref_staff(sdir, yaw):
    """orientation du bâton sur la première frame d'une animation (même règle que Builder.build)."""
    return Y.rotation_difference(sdir) @ (Quaternion(Y, math.radians(yaw)) @ Quaternion(X, math.radians(-90)))


def end_roll(N, fn):
    """vrille (rad) qui manque à la dernière frame pour retrouver l'orientation de référence."""
    b = Builder()
    for f in range(N + 1):
        p = fn(f)
        b.build(p)
    sdir, q = b.staff_prev
    ref = ref_staff(sdir, fn(N)['yaw'])
    rel = ref @ q.inverted()
    a = 2 * math.atan2(Vector((rel.x, rel.y, rel.z)).dot(sdir), rel.w)
    return (a + math.pi) % (2 * math.pi) - math.pi


def write(out_dir, name, N, fn, keep_trans=False, align_end=None):
    """align_end=(a, b) : entre les frames a et b, le bâton rattrape l'orientation attendue par l'anim suivante."""
    # fn(f) -> pose ; N = dernière frame. Écrit <out_dir>/<name>.nuanmb (gabarit = anim de Ness).
    if align_end:
        ang, base, (r0, r1) = end_roll(N, fn), fn, align_end
        fn = lambda f: dict(base(f), roll=ang * smooth01((f - r0) / (r1 - r0)))
        print(f'  raccord {name} : vrille corrigée {math.degrees(ang):.0f} deg')
    a, g, nodes = read_nodes(name)
    a.groups = [g]
    a.final_frame_index = float(N)
    b = Builder()
    frames, sdirs = [], []
    for f in range(N + 1):
        tl = None
        if keep_trans and 'Trans' in nodes:
            v = nodes['Trans']
            tl = tf_mat(v[min(f, len(v) - 1)])
        b.frame = f
        frames.append(b.build(fn(f), tl))
        sdirs.append(b.staff_prev[0])
    scales = {k: v[0].scale for k, v in read_nodes('a00wait1')[2].items()}
    for nd in g.nodes:
        if nd.name not in REST_L:
            continue
        tr = nd.tracks[0]
        sc = scales.get(nd.name, tr.values[0].scale)       # le smash de Ness rétrécit HaveR (sa batte)
        vals = []
        for L in frames:
            q = L[nd.name].to_quaternion()
            t = L[nd.name].translation
            if q.w < 0:        # nuanmb ne stocke pas w (recalculé >= 0)
                q = -q
            vals.append(S.anim_data.Transform(list(sc), [q.x, q.y, q.z, q.w], [t.x, t.y, t.z]))
        tr.values = vals
    a.save(os.path.join(out_dir, name + '.nuanmb'))
    # contrôle de fluidité : plus grand saut de rotation d'un os entre deux frames
    jumps = []
    for bn in ('Hip', 'Bust', 'Head', 'ShoulderL', 'ShoulderR', 'ArmL', 'ArmR', 'HandL', 'HandR', 'HaveR',
               'LegL', 'LegR', 'KneeL', 'KneeR'):
        for i in range(N):
            d = frames[i][bn].to_quaternion().rotation_difference(frames[i + 1][bn].to_quaternion()).angle
            jumps.append((math.degrees(min(d, 2 * math.pi - d)), bn, i + 1))
    jumps.sort(reverse=True)
    sj = max((math.degrees(sdirs[i].angle(sdirs[i + 1])), i + 1) for i in range(N))
    top = ' '.join(f'{bn}@{i}:{d:.0f}' for d, bn, i in jumps[:5])
    print(f'WROTE {name} frames={N + 1} reach_err={b.stats["reach"]:.2f} {b.stats["where"]} '
          f'staff_in_head={b.stats["head"]} sauts: {top} | bâton@{sj[1]}:{sj[0]:.0f}')
