import sys, os, glob
sys.path.insert(0, r"C:\Users\sofia\AppData\Roaming\Blender Foundation\Blender\5.1\scripts\addons\smash-ultimate-blender\dependencies\ssbh_data_py\win")
import ssbh_data_py
d = r"E:\Emulateurs\ness_model\fighter\ness\motion\body\c00"
names = sys.argv[1].split(',')
for n in names:
    a = ssbh_data_py.anim_data.read_anim(os.path.join(d, n + '.nuanmb'))
    groups = {g.group_type.name: [n.name for n in g.nodes] for g in a.groups}
    tr = groups.get('Transform', [])
    print(n, a.final_frame_index, len(tr), 'Trans' in tr, [x for x in tr if not x.startswith(('H_', 'Finger'))][:60] if n == 'a00wait1' else '')
