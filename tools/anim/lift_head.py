"""Relève le masque de Mumbo dans les animations au sol de Ness où il passe sous le plancher.

blender -b --factory-startup --python tools/anim/lift_head.py
Deux corrections, calculées image par image puis lissées :
  1. le buste, le cou et la tête se redressent (les pieds ne bougent pas) ;
  2. si cela ne suffit pas (couché, roulade), les hanches montent du reste.
Les animations en l'air, au rebord, dans l'eau ou subies par un adversaire (projections) ne sont pas
touchées : passer sous l'origine y est normal. Les animations propres à Mumbo ne sont jamais écrasées.
Sortie : tools/anim/out (liste des fichiers écrits dans lift_head.txt), puis add_token_tracks.py.
"""
import sys, os, re, math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import poses as P
from mathutils import Matrix, Vector, Quaternion

OUT = os.path.join(HERE, 'out')
MANIFEST = os.path.join(HERE, 'lift_head.txt')
TARGET = -0.5                       # la coiffe peut effleurer le sol
STEP, MAX_ANGLE = 3, 75             # redressement total (deg)
SHARE = (('Waist', 0.2), ('Bust', 0.25), ('Neck', 0.2), ('Head', 0.35))
GROUND = re.compile(r'^(a02runbrake|b02escape(f|b|$)|c0[0-4]attack|e00catch|f00damage|f03|f04|'
                    r'f05passive|f06furafura|f07sleep|f09camerahit|g00ottotto|g03slip|h0[0-5])')
SKIP = re.compile(r'air|cliff|swim|ladder|ceil|wall|thrown|fly|fall|dragoon|screw')
CORNERS = [Vector((x, y, z)) for x in P.HEAD_BOX[0] for y in P.HEAD_BOX[1] for z in P.HEAD_BOX[2]]
CHAIN = []                          # de la racine à la tête
b = 'Head'
while b:
    CHAIN.insert(0, b)
    b = P.PARENT[b]


def local(nodes, bone, f):
    v = nodes.get(bone)
    return P.tf_mat(v[min(f, len(v) - 1)]) if v else P.REST_L[bone].copy()


def solve(nodes, f, angle, sign):
    """redresse la chaîne de `angle` degrés -> (matrices locales modifiées, point le plus bas du masque)."""
    share = dict(SHARE)
    W, out, parent = Matrix.Identity(4), {}, None
    for bone in CHAIN:
        L = local(nodes, bone, f)
        parent, W = W, W @ L
        if bone in share and angle:
            # axe latéral du personnage : horizontal, perpendiculaire à son regard
            hip = out['_hipq']
            axis = hip @ Vector((1, 0, 0))
            axis.y = 0.0
            axis = axis.normalized() if axis.length > 0.2 else Vector((1, 0, 0))
            turn = Quaternion(axis, sign * math.radians(angle * share[bone]))
            pos = W.translation.copy()
            W = Matrix.Translation(pos) @ (turn @ W.to_quaternion()).to_matrix().to_4x4()
            out[bone] = parent.inverted() @ W
        if bone == 'Hip':
            out['_hipq'] = W.to_quaternion() @ P.REST_R['Hip'].inverted()
            out['_hipparent'] = parent
            out['_hip'] = W.copy()
    q = W.to_quaternion() @ P.REST_R['Head'].inverted()
    low = min((W.translation + q @ c).y for c in CORNERS)
    return out, low


def envelope(vals, radius, loop):
    """maximum glissant puis moyenne : courbe douce qui ne descend jamais sous les valeurs demandées."""
    n = len(vals)

    def at(seq, i):
        return seq[i % n] if loop else seq[min(max(i, 0), n - 1)]

    top = [max(at(vals, i + k) for k in range(-radius, radius + 1)) for i in range(n)]
    return [sum(at(top, i + k) for k in range(-radius, radius + 1)) / (2 * radius + 1) for i in range(n)]


def fix(name):
    a, g, nodes = P.read_nodes(name)
    if 'Head' not in nodes or any(bn not in nodes for bn, _ in SHARE) or 'Hip' not in nodes:
        return None
    n = int(a.final_frame_index) + 1
    base = [solve(nodes, f, 0, 1)[1] for f in range(n)]
    if min(base) >= TARGET:
        return None
    bad = [f for f in range(n) if base[f] < TARGET]
    # sens du redressement : celui qui remonte le plus le masque sur l'ensemble des images fautives
    sign = max((1, -1), key=lambda s: sum(solve(nodes, f, 30, s)[1] for f in bad))
    need = []
    for f in range(n):
        if base[f] >= TARGET:
            need.append(0.0)
            continue
        tries = [(solve(nodes, f, d, sign)[1], d) for d in range(0, MAX_ANGLE + 1, STEP)]
        ok = [d for low, d in tries if low >= TARGET]
        need.append(float(ok[0] if ok else max(tries)[1]))
    loop = bool(re.search(r'wait|loop', name))
    angle = envelope(need, 3, loop)
    angle = [max(0.0, x) for x in angle]
    rest = [max(0.0, TARGET - solve(nodes, f, angle[f], sign)[1]) for f in range(n)]
    lift = envelope(rest, 3, loop)
    new = {bn: [] for bn in ('Waist', 'Bust', 'Neck', 'Head', 'Hip')}
    final = 1e9
    for f in range(n):
        out, low = solve(nodes, f, angle[f], sign)
        final = min(final, low + lift[f])
        hip = out['_hipparent'].inverted() @ Matrix.Translation((0, lift[f], 0)) @ out['_hip']
        for bn in new:
            L = hip if bn == 'Hip' else out.get(bn, local(nodes, bn, f))
            q = L.to_quaternion()
            if q.w < 0:
                q = -q
            t = L.translation
            v = nodes[bn][min(f, len(nodes[bn]) - 1)]
            new[bn].append(P.S.anim_data.Transform(list(v.scale), [q.x, q.y, q.z, q.w], [t.x, t.y, t.z]))
    for nd in g.nodes:
        if nd.name in new:
            nd.tracks[0].values = new[nd.name]
    a.save(os.path.join(OUT, name + '.nuanmb'))
    return min(base), final, max(angle), max(lift)


mine = set(open(MANIFEST).read().split()) if os.path.exists(MANIFEST) else set()
written = []
for f in sorted(os.listdir(P.NESS_MO)):
    name = f[:-7]
    if not f.endswith('.nuanmb') or not GROUND.search(name) or SKIP.search(name):
        continue
    if os.path.exists(os.path.join(OUT, f)) and name not in mine:
        continue
    r = fix(name)
    if r:
        written.append(name)
        print(f'LIFT {name:24s} masque {r[0]:6.2f} -> {r[1]:5.2f}  redressement {r[2]:4.1f} deg  hanches +{r[3]:.2f}')
for name in mine - set(written):
    p = os.path.join(OUT, name + '.nuanmb')
    if os.path.exists(p):
        os.remove(p)
open(MANIFEST, 'w').write('\n'.join(written) + '\n')
print('TOTAL', len(written))
