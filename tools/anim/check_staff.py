"""Direction monde du bâton (HaveR, axe +Z au repos) par frame d'une anim (diagnostic)."""
import sys, math
argv = sys.argv[sys.argv.index('--') + 1:]
sys.path.insert(0, r"C:\Users\sofia\AppData\Roaming\Blender Foundation\Blender\5.1\scripts\addons\smash-ultimate-blender\dependencies\ssbh_data_py\win")
import ssbh_data_py as S
from mathutils import Matrix, Vector, Quaternion
sk = S.skel_data.read_skel(r"E:\Emulateurs\ness_model\fighter\ness\model\body\c00\model.nusktb")
mat = lambda m: Matrix([list(r) for r in m]).transposed()
names = [b.name for b in sk.bones]
par = {b.name: (sk.bones[b.parent_index].name if b.parent_index is not None else None) for b in sk.bones}
rest = {b.name: mat(b.transform) for b in sk.bones}
restw = {b.name: mat(sk.calculate_world_transform(b)) for b in sk.bones}
a = S.anim_data.read_anim(argv[0])
tr = {}
for g in a.groups:
    if g.group_type.name == 'Transform':
        for nd in g.nodes: tr[nd.name] = nd.tracks[0].values
def loc(n, f):
    v = tr.get(n)
    if not v: return rest[n]
    v = v[min(f, len(v) - 1)]
    q = Quaternion((v.rotation[3], *v.rotation[:3]))
    return Matrix.Translation(Vector(v.translation)) @ q.to_matrix().to_4x4()
step = int(argv[1]) if len(argv) > 1 else 10
for n in ('Trans', 'Rot', 'Hip', 'Waist', 'Bust', 'ClavicleC', 'ClavicleR', 'ShoulderR', 'ArmR', 'HandR', 'HaveR'):
    m = loc(n, 0); q = m.to_quaternion()
    print('FILEL', n, n in tr, tuple(round(x, 3) for x in q), tuple(round(x, 2) for x in m.translation))
for f in range(0, int(a.final_frame_index) + 1, step):
    W = {}
    for n in names:
        W[n] = W[par[n]] @ loc(n, f) if par[n] else loc(n, f)
    d = W['HaveR'].to_3x3() @ restw['HaveR'].to_3x3().inverted() @ Vector((0, 0, 1))
    h = W['HandR'].to_3x3() @ restw['HandR'].to_3x3().inverted() @ Vector((0, 0, 1))
    sc = [round(x, 2) for x in W['HaveR'].to_scale()]
    print('WQ', f, tuple(round(x, 3) for x in W['HaveR'].to_quaternion()), tuple(round(x, 3) for x in restw['HaveR'].to_quaternion()))
    print('F', f, 'staff', tuple(round(x, 2) for x in d), 'hand', tuple(round(x, 2) for x in h), 'scale', sc,
          'nodes_has_haver', 'HaveR' in tr)
