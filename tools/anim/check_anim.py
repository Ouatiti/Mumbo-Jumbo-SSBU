import sys, os
sys.path.insert(0, r"C:\Users\sofia\AppData\Roaming\Blender Foundation\Blender\5.1\scripts\addons\smash-ultimate-blender\dependencies\ssbh_data_py\win")
import ssbh_data_py
mine, orig = sys.argv[1], sys.argv[2]
for n in sorted(os.listdir(mine)):
    if not n.endswith('.nuanmb'): continue
    a = ssbh_data_py.anim_data.read_anim(os.path.join(mine, n))
    b = ssbh_data_py.anim_data.read_anim(os.path.join(orig, n))
    na = {x.name for g in a.groups for x in g.nodes}
    nb = {x.name for g in b.groups for x in g.nodes}
    hip = [x for g in a.groups for x in g.nodes if x.name == 'Hip'][0].tracks[0].values
    print(f'{n:22s} frames {a.final_frame_index:5.0f}/{b.final_frame_index:5.0f} nodes {len(na):3d}/{len(nb):3d} hipZ0 {hip[0].translation[1]:.2f}', 'manque:', sorted(n2 for n2 in nb - na if not n2.startswith(('H_', 'Finger', 'S_')))[:8])
