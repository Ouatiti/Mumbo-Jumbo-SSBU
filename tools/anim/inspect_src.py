"""Inspection des squelettes / anims sources (repos monde, longueurs, nb de frames)."""
import sys, os
sys.path.insert(0, r"C:\Users\sofia\AppData\Roaming\Blender Foundation\Blender\5.1\scripts\addons\smash-ultimate-blender\dependencies\ssbh_data_py\win")
import ssbh_data_py as S
from mathutils import Matrix, Vector

A = r"E:\Emulateurs\assist_ref\assist"
SK = {
    'ness': r"E:\Emulateurs\ness_model\fighter\ness\model\body\c00\model.nusktb",
    'bomberman': A + r"\bomberman\model\body\c00\model.nusktb",
    'akira': A + r"\akira\model\body\c00\model.nusktb",
    'kawasaki': A + r"\kawasaki\model\body\c00\model.nusktb",
}

def mat(m):
    # ssbh : lignes, translation dans la dernière ligne -> on transpose pour mathutils
    return Matrix([list(r) for r in m]).transposed()

for k, p in SK.items():
    sk = S.skel_data.read_skel(p)
    print('==', k)
    w = {b.name: mat(sk.calculate_world_transform(b)) for b in sk.bones}
    for n in ['Hip', 'Waist', 'Bust', 'Head', 'ShoulderL', 'ArmL', 'HandL', 'HaveL', 'LegL', 'KneeL', 'FootL', 'ToeL']:
        if n in w:
            m = w[n]
            q = m.to_quaternion()
            print(f'  {n:10s} pos={tuple(round(x,2) for x in m.translation)} rot={tuple(round(x,3) for x in q)}')
    mdir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(p)))), 'motion', 'body', 'c00')
    if os.path.isdir(mdir):
        for f in sorted(os.listdir(mdir)):
            if f.endswith('.nuanmb'):
                a = S.anim_data.read_anim(os.path.join(mdir, f))
                print(f'  ANIM {f} frames={a.final_frame_index}')
