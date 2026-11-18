"""Animations Mumbo à partir des trophées aide (Bomberman, Akira, Kawasaki) : retarget + mashup.

Tout se fait en espace « jeu » (Y haut, avant = +Z) avec ssbh_data_py, sans passer par Blender :
  1. pour chaque source, rotation monde de chaque os par frame  ->  delta monde D = W(f) . W_repos^-1
     (tous les squelettes SSBU partagent la même convention de repos en T : les deltas se transfèrent)
  2. mashup : moyenne pondérée des deltas de plusieurs sources (par os, avec masques), rééchantillonnées
     à la durée de l'anim de Ness correspondante (le rythme du gameplay reste le même)
  3. reconstruction sur le squelette Ness (longueurs d'os de Ness), hanches mises à l'échelle
  4. couches Mumbo : dos voûté, bras du bâton amorti, bâton redressé, vue 3/4 à l'arrêt
  5. lissage temporel gaussien (cyclique pour les boucles) -> mouvement continu, sans à-coups
  6. écriture .nuanmb (gabarit = anim vanilla de Ness du même nom, seul le groupe Transform est gardé)

Usage : blender -b --factory-startup --python assist_retarget.py -- <outdir> [noms...]
        (MUMBO_SRC=src:anim[,..] -> mode test : une seule source, sortie test_<src>_<anim>.nuanmb)
"""
import sys, os, math
sys.path.insert(0, r"C:\Users\sofia\AppData\Roaming\Blender Foundation\Blender\5.1\scripts\addons\smash-ultimate-blender\dependencies\ssbh_data_py\win")
import ssbh_data_py as S
from mathutils import Matrix, Vector, Quaternion

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0]
ONLY = set(argv[1:])
os.makedirs(OUT, exist_ok=True)

A = r"E:\Emulateurs\assist_ref\assist"
NESS_SK = r"E:\Emulateurs\ness_model\fighter\ness\model\body\c00\model.nusktb"
NESS_MO = r"E:\Emulateurs\ness_model\fighter\ness\motion\body\c00"

def mat(m):
    return Matrix([list(r) for r in m]).transposed()

def tf_mat(v):
    q = Quaternion((v.rotation[3], v.rotation[0], v.rotation[1], v.rotation[2]))
    return Matrix.Translation(Vector(v.translation)) @ q.to_matrix().to_4x4()

class Skel:
    def __init__(self, path):
        sk = S.skel_data.read_skel(path)
        self.names = [b.name for b in sk.bones]
        self.parent = {b.name: (sk.bones[b.parent_index].name if b.parent_index is not None else None) for b in sk.bones}
        self.rest_local = {b.name: mat(b.transform) for b in sk.bones}
        self.rest_world = {b.name: mat(sk.calculate_world_transform(b)) for b in sk.bones}
        self.rest_rot = {n: m.to_quaternion() for n, m in self.rest_world.items()}

def leg_len(sk):
    hip = sk.rest_world['Hip'].translation.y
    foot = sk.rest_world['FootL'].translation.y
    return hip - foot

class Source:
    """Une anim source évaluable à un temps continu."""
    def __init__(self, char, anim, face='lat'):
        self.face = face
        self.sk = SKELS[char]
        a = S.anim_data.read_anim(os.path.join(A, char, 'motion', 'body', 'c00', anim + '.nuanmb'))
        self.n = int(a.final_frame_index)
        self.tracks = {}
        for g in a.groups:
            if g.group_type.name == 'Transform':
                for nd in g.nodes:
                    self.tracks[nd.name] = nd.tracks[0].values
        self.ratio = leg_len(NESS) / leg_len(self.sk)
        self.name = f'{char}:{anim}'
        self._cache = {}

    def local(self, name, t):
        vals = self.tracks.get(name)
        if not vals or name == 'Trans':   # Trans = déplacement racine : ignoré (anims sur place)
            return self.sk.rest_local[name]
        if len(vals) == 1:
            return tf_mat(vals[0])
        t = min(max(t, 0.0), len(vals) - 1.0)
        i = int(math.floor(t)); j = min(i + 1, len(vals) - 1); u = t - i
        a, b = vals[i], vals[j]
        qa = Quaternion((a.rotation[3], *a.rotation[:3])); qb = Quaternion((b.rotation[3], *b.rotation[:3]))
        q = qa.slerp(qb, u)
        p = Vector(a.translation).lerp(Vector(b.translation), u)
        return Matrix.Translation(p) @ q.to_matrix().to_4x4()

    def world(self, t):
        key = round(t, 4)
        if key in self._cache: return self._cache[key]
        W = {}
        for n in self.sk.names:
            p = self.sk.parent[n]
            L = self.local(n, t)
            W[n] = W[p] @ L if p else L
        self._cache[key] = W
        return W

    def deltas(self, t):
        """delta de rotation monde (par os) + décalage des hanches (mis à l'échelle Ness).
        L'orientation moyenne de la source est ramenée face à +Z (certains trophées marchent
        tournés vers la caméra) : toutes les couches d'un mashup partagent le même repère."""
        W = self.world(t)
        Y = self.unyaw
        D = {n: Y @ W[n].to_quaternion() @ self.sk.rest_rot[n].inverted() for n in MAP if n in W}
        hip = Y @ ((W['Hip'].translation - self.sk.rest_world['Hip'].translation) * self.ratio)
        h0 = self.sk.rest_world['Hip'].translation
        base = Vector((h0.x, 0, h0.z))
        # pieds : hauteur repos source -> 0 (Ness ajoute sa propre hauteur de pied au repos)
        # pieds : déplacement par rapport au pied au repos (mis à l'échelle), ajouté au repos de Ness
        feet = {f: Y @ ((W[f].translation - base) * self.ratio) - (self.sk.rest_world[f].translation - base) * self.ratio
                for f in ('FootL', 'FootR') if f in W}
        return D, hip, feet

    @property
    def unyaw(self):
        if not hasattr(self, '_unyaw'):
            self._unyaw = Quaternion()
            acc = Vector((0, 0, 0))
            for k in range(12):
                W = self.world(self.n * k / 12)
                # orientation = axe latéral hanches + épaules (gauche - droite), +X au repos
                for l, r in (('LegL', 'LegR'), ('ShoulderL', 'ShoulderR')):
                    d = W[l].translation - W[r].translation
                    acc += Vector((d.x, 0, d.z)).normalized()
            yaw = math.atan2(-acc.z, acc.x)
            if self.face == 'foot':
                # locomotion : axe de déplacement des pieds (ACP en XZ) -> les pas vont droit devant
                cxx = czz = cxz = 0.0
                for f in ('FootL', 'FootR'):
                    ps = [self.world(self.n * k / 24)[f].translation for k in range(24)]
                    mx = sum(p.x for p in ps) / 24; mz = sum(p.z for p in ps) / 24
                    for p in ps:
                        dx, dz = p.x - mx, p.z - mz
                        cxx += dx * dx; czz += dz * dz; cxz += dx * dz
                th = 0.5 * math.atan2(2 * cxz, cxx - czz)
                yf = math.atan2(math.cos(th), math.sin(th))
                if math.cos(yf - yaw) < 0: yf += math.pi
                yf = math.atan2(math.sin(yf), math.cos(yf))
                print('FACING', self.name, 'lat', round(math.degrees(yaw), 1), 'foot', round(math.degrees(yf), 1))
                yaw = yf
            self._unyaw = Quaternion(Vector((0, 1, 0)), -yaw)
            print('FACING', self.name, round(math.degrees(yaw), 1))
        return self._unyaw

    def foot_sig(self, t):
        """avance relative pied gauche - pied droit (le long de l'axe de marche)."""
        W = self.world(t)
        return (self.unyaw @ (W['FootL'].translation - W['FootR'].translation)).z

    def leg_sig(self, t):
        W = self.world(t)
        Y = self.unyaw
        return [Y @ W[n].to_quaternion() @ self.sk.rest_rot[n].inverted() for n in ('LegL', 'LegR')]

def align(rc):
    """Cale automatiquement (nombre de cycles, phase) des couches à phase None sur la 1re couche :
    les jambes des deux sources avancent ensemble, le mélange ne s'annule pas."""
    if not rc['loop']: return
    L = rc['layers']
    if rc.get('ref_sig'):
        # démarche procédurale : on cale l'écart des pieds de chaque source sur celui de la démarche
        K = 24; ref = [rc['ref_sig'](k / K) for k in range(K)]
        m = max(abs(v) for v in ref) or 1.0; ref = [v / m for v in ref]
        for i, (c, a, w, mk, cyc, ph) in enumerate(L):
            if ph is not None: continue
            s = SRC(c, a, rc['face']); best = None
            for cy in ((cyc,) if cyc else (1, 2)):
                sig0 = [s.foot_sig((k / 48) * s.n) for k in range(48)]
                ms = max(abs(v) for v in sig0) or 1.0
                for p in range(50):
                    ph2 = p / 50
                    err = sum((s.foot_sig(((k / K * cy + ph2) % 1.0) * s.n) / ms - ref[k]) ** 2 for k in range(K))
                    if best is None or err < best[0]: best = (err, cy, ph2)
            L[i] = (c, a, w, mk, best[1], best[2])
            print('ALIGN-FOOT', c, a, 'cycles', best[1], 'phase', best[2], 'err', round(best[0], 2))
        return
    ref = SRC(L[0][0], L[0][1], rc['face'])
    K = 16
    refsig = [ref.leg_sig(((k / K * L[0][4] + L[0][5]) % 1.0) * ref.n) for k in range(K)]
    for i, (c, a, w, m, cyc, ph) in enumerate(L):
        if ph is not None: continue
        s = SRC(c, a, rc['face']); best = None
        for cy in ((cyc,) if cyc else (1, 2)):
            for p in range(50):
                ph2 = p / 50
                err = 0
                for k in range(K):
                    sig = s.leg_sig(((k / K * cy + ph2) % 1.0) * s.n)
                    err += sum(q1.rotation_difference(q2).angle for q1, q2 in zip(sig, refsig[k]))
                if best is None or err < best[0]: best = (err, cy, ph2)
        L[i] = (c, a, w, m, best[1], best[2])
        print('ALIGN', c, a, 'cycles', best[1], 'phase', best[2], 'err', round(best[0], 2))

NESS = Skel(NESS_SK)
SKELS = {c: Skel(os.path.join(A, c, 'model', 'body', 'c00', 'model.nusktb'))
         for c in ('bomberman', 'akira', 'kawasaki', 'claptrap', 'rodin', 'zero')}

# os transférés (même nom dans tous les squelettes SSBU)
MAP = ['Hip', 'Waist', 'Bust', 'Head', 'ShoulderL', 'ArmL', 'HandL', 'ShoulderR', 'ArmR', 'HandR',
       'LegL', 'KneeL', 'FootL', 'ToeL', 'LegR', 'KneeR', 'FootR', 'ToeR']
UPPER = {'Waist', 'Bust', 'Head', 'ShoulderL', 'ArmL', 'HandL', 'ShoulderR', 'ArmR', 'HandR'}
LOWER = {'Hip', 'LegL', 'KneeL', 'FootL', 'ToeL', 'LegR', 'KneeR', 'FootR', 'ToeR'}
ARMS = {'ShoulderL', 'ArmL', 'HandL', 'ShoulderR', 'ArmR', 'HandR'}
SPINE = {'Hip', 'Waist', 'Bust', 'Head'}

def ness_len(name):
    return int(S.anim_data.read_anim(os.path.join(NESS_MO, name + '.nuanmb')).final_frame_index)

# ───────────────────────── recettes (mashups) ─────────────────────────
# couche = (perso, anim, poids, masque d'os ou None, cycles sur la durée cible, décalage de phase 0..1)
# Bomberman : petit, tête lourde, rebond -> proportions proches de Mumbo (base des boucles au sol)
# Akira     : marche/course humaines souples (jambes, balancier)
# Kawasaki  : dos rond, gestuelle tranquille de vieux cuisinier (haut du corps)
RECIPES = {}

def recipe(names, layers, loop=True, yaw=0.0, hip_y=1.0, hip_xz=0.3, smooth=3, staff=0.8, hunch=8.0,
           face='lat', ik=False, crouch=0.0, ground=None, **gait):
    """face : 'lat' (axe épaules/hanches, idles/sauts) ou 'foot' (axe de marche, locomotion)
    ik : pieds posés par IK sur les trajectoires des pieds source (genoux recalculés, foulée Ness)
    crouch : abaissement des hanches (fraction de jambe) -> genoux souples
    ground : 'plant' (pied le plus bas collé au sol) / 'floor' (jamais sous le sol) / None"""
    for n in names:
        RECIPES[n] = dict(layers=layers, loop=loop, yaw=yaw, hip_y=hip_y, hip_xz=hip_xz, smooth=smooth,
                          staff=staff, hunch=hunch, face=face, ik=ik, crouch=crouch, ground=ground, **gait)

def blend_frame(rc, f, N):
    accD = {}; hip = Vector((0, 0, 0)); hw = 0.0
    feet = {'FootL': Vector((0, 0, 0)), 'FootR': Vector((0, 0, 0))}; fw = 0.0
    for (char, anim, w, mask, cycles, phase) in rc['layers']:
        src = SRC(char, anim, rc['face'])
        if rc['loop']:
            u = (f / N * cycles + phase) % 1.0
            t = u * src.n
        else:
            t = min(f / N * cycles, 1.0) * src.n
        D, h, ft = src.deltas(t)
        if os.environ.get('MUMBO_DBG') == '2' and f % 6 == 0 and 'Bust' in D:
            e = D['Bust'].to_euler('YXZ'); print('BUSTL', f, char, tuple(round(math.degrees(x)) for x in e))
        for n, q in D.items():
            if mask is not None and n not in mask: continue
            accD.setdefault(n, []).append((q, w))
        if mask is None or 'Hip' in mask:
            hip += h * w; hw += w
        if (mask is None or 'FootL' in mask) and len(ft) == 2:
            for k in feet: feet[k] += ft[k] * w
            fw += w
    out = {}
    for n, lst in accD.items():
        q0 = lst[0][0]; acc = Vector((0, 0, 0, 0)); ws = 0
        for q, w in lst:
            acc += (Vector(q) if q.dot(q0) >= 0 else -Vector(q)) * w; ws += w
        out[n] = Quaternion(acc).normalized()  # (Vector 4D .normalized() de Blender 5.1 ignore w)
    feet = {k: v / fw for k, v in feet.items()} if fw else None
    return out, (hip / hw if hw else hip), feet

_SRC = {}
def SRC(c, a, face='lat'):
    k = (c, a, face)
    if k not in _SRC: _SRC[k] = Source(c, a, face)
    return _SRC[k]

def rebuild_world(L):
    W = {}
    for n in NESS.names:
        p = NESS.parent[n]
        W[n] = W[p] @ L[n] if p else L[n]
    return W

def ik_leg(W, L, side, target, fwd):
    """IK 2 os Leg->Knee->Foot (longueurs Ness) : le pied atteint target, genou plié vers fwd.
    Le pied garde son orientation monde."""
    leg, knee, foot = 'Leg' + side, 'Knee' + side, 'Foot' + side
    P = W[leg].translation; K0 = W[knee].translation; F0 = W[foot].translation
    a = (NESS.rest_world[knee].translation - NESS.rest_world[leg].translation).length
    b = (NESS.rest_world[foot].translation - NESS.rest_world[knee].translation).length
    v = target - P; d = min(max(v.length, 1e-4), (a + b) * 0.999)
    u = v.normalized(); T = P + u * d
    x = (a * a - b * b + d * d) / (2 * d); h = math.sqrt(max(a * a - x * x, 0.0))
    pole = fwd - u * fwd.dot(u)
    if pole.length < 1e-5: pole = Vector((0, 0, 1))
    K = P + u * x + pole.normalized() * h
    R1 = (K0 - P).rotation_difference(K - P)
    R2 = (R1 @ (F0 - K0)).rotation_difference(T - K)
    footrot = W[foot].to_3x3()
    nleg = Matrix.Translation(P) @ (R1.to_matrix() @ W[leg].to_3x3()).to_4x4()
    nknee = Matrix.Translation(K) @ ((R2 @ R1).to_matrix() @ W[knee].to_3x3()).to_4x4()
    nfoot = Matrix.Translation(T) @ footrot.to_4x4()
    L[leg] = W[NESS.parent[leg]].inverted() @ nleg
    L[knee] = nleg.inverted() @ nknee
    L[foot] = nknee.inverted() @ nfoot

def ik_arm(W, L, target, pole, s='R'):
    """IK 2 os Shoulder(bras)->Arm(avant-bras)->Hand ; la main garde son orientation monde."""
    up, fo, ha = 'Shoulder' + s, 'Arm' + s, 'Hand' + s
    P = W[up].translation; E0 = W[fo].translation; H0 = W[ha].translation
    a = (NESS.rest_world[fo].translation - NESS.rest_world[up].translation).length
    b = (NESS.rest_world[ha].translation - NESS.rest_world[fo].translation).length
    v = target - P; d = min(max(v.length, 1e-4), (a + b) * 0.995)
    u = v.normalized(); T = P + u * d
    x = (a * a - b * b + d * d) / (2 * d); h = math.sqrt(max(a * a - x * x, 0.0))
    pl = pole - u * pole.dot(u)
    if pl.length < 1e-5: pl = Vector((0, 0, -1))
    E = P + u * x + pl.normalized() * h
    R1 = (E0 - P).rotation_difference(E - P)
    R2 = (R1 @ (H0 - E0)).rotation_difference(T - E)
    nup = Matrix.Translation(P) @ (R1.to_matrix() @ W[up].to_3x3()).to_4x4()
    nfo = Matrix.Translation(E) @ ((R2 @ R1).to_matrix() @ W[fo].to_3x3()).to_4x4()
    nha = Matrix.Translation(T) @ W[ha].to_3x3().to_4x4()
    L[up] = W[NESS.parent[up]].inverted() @ nup
    L[fo] = nup.inverted() @ nfo
    L[ha] = nfo.inverted() @ nha

def ness_vanilla_feet(nodes, frames):
    """trajectoires monde des pieds de l'anim vanilla de Ness (pour caler la foulée)."""
    out = []
    for f in frames:
        L = {n: (NESS.rest_local[n] if n == 'Trans' else tmpl_local(nodes, n, f)) for n in NESS.names}
        W = rebuild_world(L)
        out.append({k: W[k].translation.copy() for k in ('FootL', 'FootR', 'Hip')})
    return out

# ───────────────────────── couches Mumbo ─────────────────────────
UPv = Vector((0, 1, 0)); FWD = Vector((0, 0, 1)); SIDE = Vector((1, 0, 0))
STAFF_AXIS_REST = FWD  # le bâton (os HaveR) pointe vers l'avant en pose de repos
BUST_KIDS = None

class Gait:
    """Démarche procédurale : trajectoires de pieds lisses (appui linéaire, envol Hermite à vitesse
    continue), cadence et foulée prises sur l'anim vanilla de Ness (pas de glisse en jeu),
    rebond / balancement / torsion des hanches synchronisés sur les appuis."""
    def __init__(self, name, rc, nodes, N):
        van = ness_vanilla_feet(nodes, range(N + 1))
        zl = [v['FootL'].z - v['Hip'].z for v in van]; zr = [v['FootR'].z - v['Hip'].z for v in van]
        if os.environ.get('MUMBO_DBG'):
            for i in range(0, N + 1, 3):
                v = van[i]; print('VAN', i, tuple(round(x, 2) for x in v['FootL'] - v['Hip']), tuple(round(x, 2) for x in v['FootR'] - v['Hip']))
        self.S = rc.get('stride', 1.0) * 0.5 * ((max(zl) - min(zl)) + (max(zr) - min(zr)))
        m = sum(zl) / len(zl)
        self.cyc = max(1, sum(1 for i in range(N) if zl[i] - m < 0 <= zl[i + 1] - m))
        fmax = max(range(N), key=lambda i: zl[i])
        self.ph0 = -fmax / N * self.cyc
        self.N = N
        Ll = leg_len(NESS)
        self.beta = rc.get('beta', 0.6)
        self.H = rc.get('lift', 0.2) * Ll
        self.bob = rc.get('bob', 0.03) * Ll
        self.sway = rc.get('sway', 0.03) * Ll
        self.tw = math.radians(rc.get('twist', 6.0))
        self.lean = math.radians(rc.get('lean', 4.0))
        self.pitch = math.radians(rc.get('pitch', 18.0))
        # hanches assez basses pour que la jambe atteigne l'avant/l'arrière de la foulée sans se tendre
        a = (NESS.rest_world['KneeL'].translation - NESS.rest_world['LegL'].translation).length
        b = (NESS.rest_world['FootL'].translation - NESS.rest_world['KneeL'].translation).length
        hv = NESS.rest_world['LegL'].translation.y - NESS.rest_world['FootL'].translation.y
        reach = 0.97 * (a + b); half = 0.5 * self.S
        need = hv - math.sqrt(max(reach * reach - half * half, 0.0)) - 0.8 * self.bob
        self.crouch = max(0.0, need) + rc['crouch'] * Ll
        print('GAIT', name, 'S', round(self.S, 2), 'cycles', self.cyc, 'ph0', round(self.ph0, 3), 'leg', round(a + b, 2),
              'hv', round(hv, 2), 'crouch', round(self.crouch, 2))

    def phase(self, f): return f / self.N * self.cyc + self.ph0

    def foot(self, ph):
        """-> (z, y, pitch) d'un pied ; ph = 0 : posé tout devant."""
        b, S = self.beta, self.S; ph %= 1.0
        if ph < b:
            return S / 2 - S * ph / b, 0.0, 0.0
        s = (ph - b) / (1 - b); s2, s3 = s * s, s * s * s
        mt = -S / b * (1 - b)  # vitesse d'appui conservée au décollage et à la pose
        z = -S / 2 * (2 * s3 - 3 * s2 + 1) + mt * (s3 - 2 * s2 + s) + S / 2 * (-2 * s3 + 3 * s2) + mt * (s3 - s2)
        y = self.H * math.sin(math.pi * s) ** 1.5
        p = self.pitch * math.sin(math.pi * s) * (1 - 1.6 * s)  # pointe vers le bas au décollage, talon à la pose
        return z, y, p

    def ref_sig(self, u):
        ph = u * self.cyc + self.ph0
        return self.foot(ph)[0] - self.foot(ph + 0.5)[0]

    def frame(self, f, D):
        """remplit D (hanche, jambes) et renvoie (offset hanche, pieds)."""
        ph = self.phase(f); b = self.beta
        zl, yl, pl = self.foot(ph); zr, yr, pr = self.foot(ph + 0.5)
        hip = Vector((self.sway * math.cos(2 * math.pi * (ph - b / 2)),
                      self.bob * math.cos(4 * math.pi * (ph - b / 2)) - self.crouch, 0.0))
        D['Hip'] = Quaternion(UPv, -self.tw * math.cos(2 * math.pi * ph)) @ Quaternion(SIDE, self.lean)
        for s, p in (('L', pl), ('R', pr)):
            D['Leg' + s] = Quaternion(); D['Knee' + s] = Quaternion(); D['Toe' + s] = Quaternion()
            D['Foot' + s] = Quaternion(SIDE, p)
        return hip, {'FootL': Vector((0.0, yl, zl)), 'FootR': Vector((0.0, yr, zr))}

def descendants(sk, root):
    out = {root}
    changed = True
    while changed:
        changed = False
        for n in sk.names:
            if n not in out and sk.parent[n] in out:
                out.add(n); changed = True
    return out

def qavg(qs, ws=None):
    ws = ws or [1.0] * len(qs)
    q0 = qs[0]; acc = Vector((0, 0, 0, 0))
    for q, w in zip(qs, ws):
        acc += (Vector(q) if q.dot(q0) >= 0 else -Vector(q)) * w
    return Quaternion(acc).normalized()

def smooth_seq(seq, r, loop):
    n = len(seq)
    if r <= 0 or n < 3: return seq
    out = []
    for i in range(n):
        qs = []; ws = []
        for d in range(-r, r + 1):
            j = i + d
            j = j % n if loop else min(max(j, 0), n - 1)
            qs.append(seq[j]); ws.append(math.exp(-(d * d) / (0.5 * r * r)))
        # centre en premier pour l'hémisphère
        k = r
        qs = [qs[k]] + qs[:k] + qs[k + 1:]; ws = [ws[k]] + ws[:k] + ws[k + 1:]
        out.append(qavg(qs, ws))
    return out

def smooth_vec(seq, r, loop):
    n = len(seq)
    if r <= 0 or n < 3: return seq
    out = []
    for i in range(n):
        acc = Vector((0, 0, 0)); w = 0
        for d in range(-r, r + 1):
            j = i + d
            j = j % n if loop else min(max(j, 0), n - 1)
            ww = math.exp(-(d * d) / (0.5 * r * r)); acc += seq[j] * ww; w += ww
        out.append(acc / w)
    return out

def build(name, rc, tmpl_nodes):
    loop = rc['loop']
    N = ness_len(name)
    gait = None
    if rc['ik'] == 'proc':
        gait = Gait(name, rc, tmpl_nodes, N)
        rc['ref_sig'] = gait.ref_sig
    align(rc)
    frames = list(range(N + 1))
    # 1) deltas mélangés par frame
    Ds = []; Hs = []; Fs = []
    for f in frames:
        D, h, ft = blend_frame(rc, f if not loop else f % N, N)
        if os.environ.get('MUMBO_DBG') == '2' and 'Bust' in D:
            print('BUSTM', f, tuple(round(math.degrees(x)) for x in D['Bust'].to_euler('YXZ')))
        Ds.append(D); Hs.append(h); Fs.append(ft)
    # hanches : vertical gardé, horizontal atténué et sans dérive
    mean = sum(Hs, Vector((0, 0, 0))) / len(Hs)
    Hs = [Vector(((h.x - mean.x) * rc['hip_xz'], h.y * rc['hip_y'], (h.z - mean.z) * rc['hip_xz'])) for h in Hs]
    if gait:
        for i, f in enumerate(frames):
            Hs[i], Fs[i] = gait.frame(f, Ds[i])
    if loop:
        Ds[-1] = Ds[0]; Hs[-1] = Hs[0]
    # 2) lissage temporel des deltas (cyclique pour les boucles : la jointure est continue)
    sm = rc['smooth']
    bones = sorted({n for D in Ds for n in D})
    body = frames[:-1] if loop else frames
    for n in bones:
        seq = [Ds[i].get(n, Quaternion()) for i in range(len(body))]
        if os.environ.get('MUMBO_DBG') == '2' and n == 'Bust':
            print('SEQ0', [tuple(round(x, 3) for x in q) for q in seq[:4]], seq[-3:])
        seq = smooth_seq(seq, sm, loop)
        if os.environ.get('MUMBO_DBG') == '2' and n == 'Bust':
            print('SEQ1', [tuple(round(x, 3) for x in q) for q in seq[:4]])
        for i, q in enumerate(seq): Ds[i][n] = q
    Hs[:len(body)] = smooth_vec(Hs[:len(body)], sm, loop)
    if os.environ.get('MUMBO_DBG') == '2':
        for i in range(0, len(body), 6):
            if 'Bust' in Ds[i]: print('BUSTS', i, tuple(round(math.degrees(x)) for x in Ds[i]['Bust'].to_euler('YXZ')))
    if loop:
        Ds[-1] = Ds[0]; Hs[-1] = Hs[0]
    # 2b) atténuation par os (couches trop amples) : delta ramené vers l'identité
    for n, k in rc.get('damp', {}).items():
        done = set()
        for D in Ds:
            if n not in D or id(D) in done: continue
            done.add(id(D))
            q = D[n] if D[n].w >= 0 else -D[n]
            D[n] = Quaternion().slerp(q, k).normalized()
    # 2c) torsion moyenne du torse retirée (le buste suit la direction de marche)
    if rc.get('detwist'):
        for n in ('Waist', 'Bust', 'Head'):
            if n not in bones: continue
            ys = [Ds[i][n].to_euler('YXZ').y for i in range(len(body))]
            m = sum(ys) / len(ys); R = Quaternion(UPv, -rc['detwist'] * m)
            for i in range(len(body)): Ds[i][n] = (R @ Ds[i][n]).normalized()
            if loop: Ds[-1] = Ds[0]
    if os.environ.get('MUMBO_DBG'):
        for n in ('Hip', 'Waist', 'Bust', 'Head', 'ShoulderL', 'ArmL'):
            if n not in bones: continue
            es = [Ds[i][n].to_euler('YXZ') for i in range(len(body))]
            print('EUL', n, ' '.join(f'{ax}:{round(math.degrees(min(getattr(e, ax) for e in es)))}..{round(math.degrees(max(getattr(e, ax) for e in es)))}' for ax in 'xyz'))
    # 3) bras du bâton : balancier amorti vers la moyenne (le bâton pèse)
    for n, k in (('ShoulderR', 0.45), ('ArmR', 0.35), ('HandR', 0.4)):
        if n not in bones: continue
        m = qavg([D[n] for D in Ds])
        done = set()
        for D in Ds:
            if id(D) in done: continue      # boucles : la dernière frame est le même dict que la 1re
            done.add(id(D))
            q = D[n] if D[n].dot(m) >= 0 else -D[n]
            D[n] = m.slerp(q, k).normalized()
    # 4) reconstruction sur le squelette Ness + couches
    yaw = Quaternion(UPv, math.radians(rc['yaw']))
    hunch = Quaternion(SIDE, math.radians(rc['hunch']))
    bust_kids = descendants(NESS, 'Bust')
    staff_dirs = []
    locals_per_frame = []
    # pieds (IK) : trajectoires lissées, foulée recalée sur celle de Ness vanilla
    ik = rc['ik'] and Fs[0] is not None
    if ik and not gait:
        for k in ('FootL', 'FootR'):
            seq = smooth_vec([F[k] for F in Fs[:len(body)]], sm, loop)
            for i, v in enumerate(seq): Fs[i][k] = v
            if loop: Fs[-1][k] = Fs[0][k]
        van = ness_vanilla_feet(tmpl_nodes, frames)
        def zrange(seq): return max(seq) - min(seq)
        zs = zrange([F['FootL'].z for F in Fs]) + zrange([F['FootR'].z for F in Fs])
        zv = zrange([V['FootL'].z for V in van]) + zrange([V['FootR'].z for V in van])
        k_stride = (zv / zs) if zs > 1e-4 else 1.0
        k_stride = min(max(k_stride, 0.5), 2.0)
        print('STRIDE', name, 'src', round(zs, 2), 'ness', round(zv, 2), 'k', round(k_stride, 2))
        for k in ('FootL', 'FootR'):
            mz = sum(F[k].z for F in Fs) / len(Fs)
            for F in Fs: F[k] = Vector((F[k].x, F[k].y, mz + (F[k].z - mz) * k_stride))
    crouch = 0.0 if gait else rc['crouch'] * leg_len(NESS)
    for i, f in enumerate(frames):
        D = Ds[i]; W = {}; L = {}
        if crouch: Hs[i] = Hs[i] - Vector((0, crouch, 0))
        for n in NESS.names:
            p = NESS.parent[n]
            if n in D:
                q = D[n].normalized()
                if n in bust_kids: q = hunch @ q
                q = (yaw @ q).normalized()
                rot = (q @ NESS.rest_rot[n]).to_matrix().to_4x4()
                if n == 'Hip':
                    pos = yaw @ (NESS.rest_world['Hip'].translation + Hs[i])
                else:
                    pos = (W[p] @ NESS.rest_local[n]).translation
                W[n] = Matrix.Translation(pos) @ rot
            else:
                loc = tmpl_local(tmpl_nodes, n, f)
                if n in ('Trans', 'Rot'): loc = NESS.rest_local[n]
                W[n] = (W[p] @ loc) if p else loc
            L[n] = (W[p].inverted() @ W[n]) if p else W[n]
        if ik:
            fwd = yaw @ FWD
            for s in ('L', 'R'):
                r0 = NESS.rest_world['Foot' + s].translation
                d = Fs[i]['Foot' + s]
                tgt = yaw @ Vector((r0.x + d.x, r0.y + max(d.y, 0.0), r0.z + d.z))
                ik_leg(W, L, s, tgt, fwd + (yaw @ SIDE) * (0.15 if s == 'L' else -0.15))
            W = rebuild_world(L)
        if rc['ground']:
            fy = min(W['FootL'].translation.y, W['FootR'].translation.y)
            ry = NESS.rest_world['FootL'].translation.y
            dy = ry - fy
            if rc['ground'] == 'plant' or dy > 0:
                p = NESS.parent['Hip']
                nh = Matrix.Translation((0, dy, 0)) @ W['Hip']
                L['Hip'] = (W[p].inverted() @ nh) if p else nh
                W = rebuild_world(L)
        # main du bâton posée (idles) : à côté de la hanche, un peu devant, coude souple vers l'arrière
        if rc.get('staff_hand'):
            al = sum((NESS.rest_world[c].translation - NESS.rest_world[p].translation).length
                     for p, c in (('ShoulderR', 'ArmR'), ('ArmR', 'HandR')))
            ox, oy, oz = rc['staff_hand']
            ph = 2 * math.pi * f / max(1, N)
            off = Vector((ox, oy + 0.03 * math.sin(ph), oz + 0.03 * math.cos(ph))) * al
            ik_arm(W, L, W['ShoulderR'].translation + yaw @ off, yaw @ Vector((-0.6, 0.0, -1.0)))
            if rc.get('free_hand'):
                fx, fy, fz = rc['free_hand']
                offl = Vector((fx, fy + 0.04 * math.sin(ph + 1.0), fz + 0.05 * math.sin(ph + 0.4))) * al
                W = rebuild_world(L)
                ik_arm(W, L, W['ShoulderL'].translation + yaw @ offl, yaw @ Vector((0.6, 0.0, -1.0)), 'L')
            W = rebuild_world(L)
        # bâton redressé
        if 'HaveR' in W:
            cur = (W['HaveR'].to_3x3() @ NESS.rest_world['HaveR'].to_3x3().inverted() @ STAFF_AXIS_REST).normalized()
            tgt = (yaw @ (UPv + FWD * rc.get('staff_fwd', 0.18))).normalized()
            staff_dirs.append((cur, tgt))
        locals_per_frame.append((W, L))
    # direction du bâton lissée (inertie) puis appliquée sur HaveR
    if staff_dirs:
        want = [(t * rc['staff'] + c * (1 - rc['staff'])).normalized() for c, t in staff_dirs]
        want = [v.normalized() for v in smooth_vec(want, 2, loop)]
        for (W, L), (cur, _), d in zip(locals_per_frame, staff_dirs, want):
            R = cur.rotation_difference(d).to_matrix().to_4x4()
            M = W['HaveR']; T = Matrix.Translation(M.translation)
            W['HaveR'] = T @ R @ Matrix.Translation(-M.translation) @ M
            L['HaveR'] = W['HandR'].inverted() @ W['HaveR']
    if os.environ.get('MUMBO_DBG'):
        for i in range(0, len(frames), 30):
            W, L = locals_per_frame[i]; W2 = rebuild_world(L)
            ax = lambda M: tuple(round(x, 2) for x in (M.to_3x3() @ NESS.rest_world['HaveR'].to_3x3().inverted() @ FWD).normalized())
            print('DBG', i, 'cur', tuple(round(x, 2) for x in staff_dirs[i][0]), 'want', tuple(round(x, 2) for x in want[i]),
                  'W', ax(W['HaveR']), 'W2', ax(W2['HaveR']), 'hand', (W['HandR'].translation - W2['HandR'].translation).length)
            print('WQ', i, tuple(round(x, 3) for x in W2['HaveR'].to_quaternion()), tuple(round(x, 3) for x in NESS.rest_world['HaveR'].to_quaternion()))
            if i == 0:
                for n in ('Trans', 'Rot', 'Hip', 'Waist', 'Bust', 'ClavicleC', 'ClavicleR', 'ShoulderR', 'ArmR', 'HandR', 'HaveR'):
                    q = L[n].to_quaternion(); print('DBGL', n, tuple(round(x, 3) for x in q), tuple(round(x, 2) for x in L[n].translation),
                                                    'det', round(L[n].to_3x3().determinant(), 3), 'restdet', round(NESS.rest_local[n].to_3x3().determinant(), 3),
                                                    'wdet', round(W2[n].to_3x3().determinant(), 3))
    return [L for _, L in locals_per_frame]

def tmpl_local(nodes, name, f):
    if name.startswith('H_'):
        return NESS.rest_local[name]
    v = nodes.get(name)
    if not v: return NESS.rest_local[name]
    return tf_mat(v[min(f, len(v) - 1)] if len(v) > 1 else v[0])

def write(name, out_name, rc):
    a = S.anim_data.read_anim(os.path.join(NESS_MO, name + '.nuanmb'))
    a.groups = [g for g in a.groups if g.group_type.name == 'Transform']
    g = a.groups[0]
    missing = [n for n in MAP + ['Neck', 'HaveR'] if n not in {nd.name for nd in g.nodes}]
    if missing: print('MISSING', name, missing)
    nodes = {nd.name: nd.tracks[0].values for nd in g.nodes}
    Ls = build(name, rc, nodes)
    for nd in g.nodes:
        if nd.name not in NESS.rest_local: continue
        tr = nd.tracks[0]
        vals = []
        sc0 = tr.values[0].scale
        for L in Ls:
            m = L[nd.name]
            q = m.to_quaternion(); p = m.translation
            # la compression nuanmb ne stocke pas w (recalculé >= 0) : un quaternion à w < 0 serait retourné
            if q.w < 0: q = Quaternion((-q.w, -q.x, -q.y, -q.z))
            vals.append(S.anim_data.Transform(list(sc0), [q.x, q.y, q.z, q.w], [p.x, p.y, p.z]))
        tr.values = vals
    path = os.path.join(OUT, out_name + '.nuanmb')
    a.save(path)
    print('WROTE', path, len(Ls))

# ───────────────────────── recettes ─────────────────────────
B, K, Z = 'bomberman', 'akira', 'kawasaki'
# (phase / cycles None = calage automatique sur la 1re couche)
X = 'zero'
TORSO = {'Waist', 'Bust', 'Head'}
HAND_IDLE = (-0.7, -0.6, 0.15)  # main du bâton : bien à droite, planté près de la hanche (vue jeu : derrière le crâne, pas devant le visage)
FREE_IDLE = (0.28, -0.82, 0.12)  # main libre : pend détendue le long du corps, légèrement devant
recipe(['a00wait1'], [(B, 'wait', 0.7, None, 1, 0.0), (Z, 'wait', 0.5, TORSO, 1, 0.0)], yaw=-50, hip_y=0.8, ground='plant',
       staff_hand=HAND_IDLE, free_hand=FREE_IDLE, staff=1.0, staff_fwd=0.0)
recipe(['a00wait2'], [(B, 'wait', 0.5, None, 1, 0.3), (Z, 'wait', 0.7, TORSO, 1, 0.5)], yaw=-55, hip_y=0.8, ground='plant',
       staff_hand=HAND_IDLE, free_hand=FREE_IDLE, staff=1.0, staff_fwd=0.0)
recipe(['a00wait3'], [(B, 'wait', 0.6, None, 1, 0.6), (Z, 'wait', 0.5, TORSO, 1, 0.25)], loop=False, yaw=-50, hip_y=0.8, ground='plant',
       staff_hand=HAND_IDLE, free_hand=FREE_IDLE, staff=1.0, staff_fwd=0.0)
# marche : pas trottinants du vieux cuisinier (pieds par IK, genoux Ness) + balancier des bras de Bomberman
recipe(['a01walkslow', 'a01walkmiddle'], [(Z, 'walk', 1.0, TORSO, None, None), (B, 'run', 0.35, ARMS | {'Bust'}, None, None)],
       yaw=-10, face='foot', ik='proc', stride=0.75, crouch=0.02, lift=0.16, bob=0.025, sway=0.03, twist=6, lean=3, pitch=15, detwist=0.6)
recipe(['a01walkfast'], [(Z, 'walk', 0.6, TORSO, None, None), (B, 'run', 0.5, ARMS | {'Bust', 'Head'}, None, None)],
       yaw=-8, face='foot', ik='proc', stride=0.8, crouch=0.04, beta=0.55, lift=0.22, bob=0.035, sway=0.025, twist=8, lean=7, pitch=20, detwist=0.6)
recipe(['a02run'], [(X, 'run', 0.5, None, 1, 0.0), (B, 'run', 0.5, None, None, None)], yaw=-5, hunch=12, face='foot', ground='floor')
recipe(['a02dash'], [(K, 'dash', 0.6, None, 1, 0.0), (B, 'runstart', 0.4, None, 1, 0.0)], loop=False, yaw=-5, hunch=12, ground='floor',
       staff_hand=(-0.35, -0.62, 0.42))
recipe(['a03jumpf', 'a03jumpb'], [(B, 'jump', 0.6, None, 1, 0.0), (K, 'jump', 0.4, None, 1, 0.0)], loop=False, hip_y=0.0, hip_xz=0.0)
recipe(['a03jumpaerialf', 'a03jumpaerialb'], [(B, 'jumpair', 0.6, None, 1, 0.0), (K, 'jumpair', 0.4, None, 1, 0.0)], loop=False, hip_y=0.0, hip_xz=0.0)
recipe(['a04fall', 'a04fallf', 'a04fallb', 'a04fallaerial'], [(B, 'fall', 0.5, None, 1, 0.0), (Z, 'fall', 0.5, None, 1, 0.0)], hip_y=0.0, hip_xz=0.0)

if os.environ.get('MUMBO_SRC'):
    for spec in os.environ['MUMBO_SRC'].split(','):
        c, an = spec.split(':')
        tmpl = os.environ.get('MUMBO_TMPL', 'a00wait1')
        rc = dict(layers=[(c, an, 1.0, None, 1, 0.0)], loop=True, yaw=0, hip_y=1.0, hip_xz=1.0, smooth=0, staff=0.0, hunch=0.0,
                  face='lat', ik=False, crouch=0.0, ground=None)
        rc.update(eval(os.environ.get('MUMBO_OPTS', '{}')))
        write(tmpl, f'test_{c}_{an}', rc)
else:
    for n, rc in RECIPES.items():
        if ONLY and n not in ONLY: continue
        write(n, n, rc)
